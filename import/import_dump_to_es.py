#!/usr/bin/env python3
import time, humanfriendly, os, elasticsearch, sys
import getopt
import ast
import tokenize
from concurrent.futures import ProcessPoolExecutor
import functools
from token import tok_name, OP, STRING, NUMBER, NEWLINE, ENDMARKER, NAME
from es_admin import *
from model import *
from files import *
from mbutils import *

config = load_config({
  'BATCH_SIZE': 10_000,
  'LIMIT': 0 # maximum number of items to process.
})
es = None

def main(db, compare=True, es_import=False, config=config):
  log(f"-- ES processing of {db}, new index:{os.environ['NEW_INDEX']}, current index:{os.environ['CURRENT_INDEX']}," +
    f" compare:{compare}, es_import:{es_import} limit:{config['LIMIT']} --")

  start = time.time()
  global es; es = ElasticSearchAdmin()

  files = ls(f"{ddir(db)}/{db}_inserts.sql.part-*")
  limit = config['LIMIT'] / len(files) # Split the limit between all executors.
  log(f"Importing {len(files)} files:\n{joinl(sorted(files))}")

  with ProcessPoolExecutor() as executor:
    partial = functools.partial(import_file, db=db,
      limit=limit, compare=compare, es_import=es_import, batch_size=config['BATCH_SIZE'])
    results = executor.map(partial, files)

  total, missing, bad = aggregate(results)
  write(missing_file(db), joinl(missing))
  write(bad_file(db), joinl(bad))

  end = time.time()
  log(f"Total: {total:,} entries")
  log(f"Missing: {len(missing):,}, see {missing_file(db)}")
  log(f"Bad: {len(bad):,}, see {bad_file(db)}")
  log(f"Finished loading ES data from {db} in: {humanfriendly.format_timespan(end - start)}")

def import_file(file, db=None, limit=None, compare=None, es_import=None, lock=None, batch_size=None):
  bad = []
  missing = []
  total = 0

  batch = []
  for line_num,row in parse_values(LineReader(file)):
    doc, err = row_to_doc(db, row)
    if doc:
      batch.append((line_num, doc))
    elif err:
      bad.append(str((line_num, err, row)))

    if len(batch) >= batch_size:
      total += handle_batch(db, batch, compare, es_import, missing, bad)
      batch = []
      missing_str = f" Missing:{len(missing):,}" if compare else ""
      debug(f"File: {file} Processed:{total:,} (Line:{line_num:,}) {missing_str}")
    if limit and total >= limit:
      break
  if batch:
    total += handle_batch(db, batch, compare, es_import, missing, bad)

  log(f"Completed: {file} Imported:{total:,} (Line:{line_num:,}) Missing:{len(missing)} Failed entries:{len(bad)}")
  return {'total': total, 'missing': missing, 'bad':bad}

def aggregate(results):
  total = 0
  missing = []
  bad = []
  for result in results:
    total += result['total']
    missing.extend(result['missing'])
    bad.extend(result['bad'])
  return total, missing, bad

def parse_values(line_reader):
  in_paran = False
  paran_contents = []
  for t in tokenize.generate_tokens(line_reader.readline):
    n = line_reader.line_num
    if t.type == OP and t.string == '(':
      if in_paran:
        unexpected(t, n, "Nested paran not supported")
      in_paran = True
    elif t.type == OP and t.string == ')':
      if not in_paran:
        unexpected(t, n, "Unexpected close paran")
      in_paran = False
      yield n, paran_contents # Return the values and the line number, the line number in the
      # token is not accurate if lines are skipped.
      paran_contents = []
    elif t.type == STRING:
      if not in_paran:
        unexpected(t, n, "Unexpected string value")
      parsed_value = ast.literal_eval(t.string)  # tokenizer returns string with quotes and escape chars.
      paran_contents.append(parsed_value)
    elif t.type == NUMBER:
      if not in_paran:
        unexpected(t, n, "Unexpected number")
      paran_contents.append(int(t.string)) # the dataset only has int values, no floats
    elif t.type == NAME and t.string == 'NULL':
      if not in_paran:
        unexpected(t, n, "Unexpected NULL")
      paran_contents.append('')
    elif t.type == OP and t.string == ',':
      continue
    elif t.type == OP and t.string == ';':
      if in_paran:
        unexpected(t, n, "Unclosed paran")
    elif t.type == NEWLINE:
      continue
    elif t.type == ENDMARKER:
      if in_paran:
        unexpected(t, n, "Unclosed paran")
      return
    else:
      unexpected(t, n)

def unexpected(t, line_num, s='', parans=[]):
  context = ''
  if parans:
    context = joinl(parans, ', ')
  raise Exception(f"Unexpected token:{tok_name[t.type]} {s} line:{line_num} position:{t.start[1]} '{t.string}' context:'{context}'")

class LineReader:
  """ For use with tokenize.generate_tokens. """
  def __init__(self, file):
    self.fh = open(file)
    self.line_num = 0 # the first line is 1, 0 means no lines have been read.
  def readline(self):
    while line := self.fh.readline():
      self.line_num += 1
      return line
    return '' # This means the end of the file (empty lines will contain \n)

def handle_batch(db, batch, compare, es_import, missing, bad):
  if compare:
    misses,diffs = diffm(batch)
    for line_num, resp, doc in misses:
      missing.append(f'line:{line_num} {resp} DOC: {doc}')
    for line_num, diff, doc in diffs:
      log(f"Diff at line {line_num}. diff:{diff}")
      bad.append(f'line:{line_num} {diff} DOC:{doc}')
  if es_import:
    success, errors = es.upsert(map(lambda x:x[1], batch)) # remove line numbers from batch
    for err in errors:
      bad.append(f'Index failed: {err}')
  return len(batch)

def diffm(docs_and_line_nums):
  """ Get multiple docs from ES and compare to docs in `docs_and_line_nums`. """
  ids = list(map(lambda x:x[1]['_id'], docs_and_line_nums))
  by_id = dict(zip(ids, docs_and_line_nums))
  es_docs = es.getm(ids)
  missing = []
  diffs = []
  for resp in es_docs:
    id_ = resp['_id']
    line_num, doc = by_id[id_]

    if 'error' in resp:
      diffs.append((line_num, resp, doc)) # Just store the whole response
    elif not resp['found']:
      missing.append((line_num, resp, doc))
    else:
      differences = diff(resp['_source'], doc['_source'])
      if differences:
        diffs.append((line_num, differences, doc))

  return missing, diffs

def diff(es_doc, doc):
  result = {}
  for k,v1 in es_doc.items():
    if k not in doc:
      result[k] = (v1, None)
      continue
    v2 = doc[k]
    if v1 != v2:
      result[k] = (v1, v2)
  return result

if __name__ == '__main__':
  try:
      opts, args = getopt.getopt(sys.argv[1:], "cn", [])
  except getopt.GetoptError as err:
      print(str(err))
      sys.exit(2)

  compare = False
  es_import = True
  for opt, arg in opts:
    if opt == '-c': # Compare db file to current data in ES.
      compare = True
    if opt == '-n': # No import.
      es_import = False

  if len(args) != 1:
    print("Usages import: [-cn] <db-name>")
    sys.exit(1)

  db = args[0]
  main(db, compare=compare, es_import=es_import)

