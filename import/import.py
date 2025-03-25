#!/usr/bin/env python3

import os
import subprocess
import sys
import time, datetime
import getopt
import requests
from enum import Enum

from mbutils import *
from files import *
from es_admin import *
import import_dump_to_es as dump_to_es
import import_sql_to_es as sql_to_es

DL_RETRIES = 4
CURL = "curl -sS"

config = load_config()

def main(dbs, do_download, mode, do_swap, force_import):
  failed = False
  start_time = start(f"\n------ Starting import of:{joinl(dbs,',')} Mode:{mode}, Elasticsearch:{config['ELASTIC_HOST']}\n" +
    f"------ Swap indexes:{do_swap} Clean up:{config['IMPORT_CLEAN']} Force import: {force_import} ------")

  failed = import_dbs(dbs, do_download, mode, do_swap, force_import)
  end_(f"------ Finished importing {dbs} ------", start_time)
  report_status(failed)

  if failed:
    sys.exit(1)

def report_status(failed):
  status = "failed" if failed else "succeeded"
  report = [f'<html><body><h1>Import {status} at {iso_timestamp()}</h1><pre>']
  log_messages = get_logged_messages()
  report.extend(log_messages)
  report.append('</pre>')
  write('admin/generated/import_status.html', joinl(report))
  if failed:
    mail(f"{sys.argv[0]} Failed", joinl(log_messages))

def maybe_create_indexes():
  # Create missing indexes, don't update existing indexes because
  # they have to be closed to this and searches will fail.
  shell('./scripts/es_setup_indexes.sh -n')

@catch_and_log_exceptions
def import_dbs(dbs, do_download, mode, do_swap, force_import):
  maybe_create_indexes()
  setup_index()

  failed = False
  for db in dbs:
    result = import_db(db, do_download, mode, force_import)
    failed |= result
    clean(db, result)
  if not failed and mode != Mode.ES_COMPARE and mode != Mode.MYSQL_IMPORT:
    # Manually refresh the index to try to get e2e tests to pass.
    es.refresh_index(os.environ['NEW_INDEX'])
    if do_swap:
      swap_index()
  return failed

@catch_and_log_exceptions
def import_db(db, do_download, mode, force_import):
  start_time = start(f"---- Starting import of:{db} to index:{os.environ['NEW_INDEX']} ----")
  etag = download(db, do_download)
  unpack(db, etag)

  if mode != Mode.MYSQL_IMPORT and mode != Mode.MYSQL_IMPORT_AND_ES_IMPORT:
    split_sql_inserts(db, etag)
  else:
    strip_sql(db, etag)

  if mode == Mode.MYSQL_IMPORT:
    import_sql(db, etag)
  elif mode == Mode.MYSQL_IMPORT_AND_ES_IMPORT:
    import_sql(db, etag)
    import_sql_to_es(db, etag, force_import)
  elif mode == Mode.DUMP_FILE_IMPORT:
    compare = False
    import_dump_to_es(db, etag, compare, force_import)
  elif mode == Mode.ES_COMPARE_AND_IMPORT:
    compare = True
    import_dump_to_es(db, etag, compare, force_import)
  elif mode == Mode.ES_COMPARE:
    parse_dump_and_compare(db, etag)
  else:
    log(f"Unknown mode:{mode}")
    sys.exit(1)
  end_(f"---- Finished importing '{db}' ----", start_time)

def download(db, do_download):
  if not do_download:
    log(f"Not redownloading {db}")
    return 'NOTAG'

  url = f"{config['DUMP_URL']}{db}.rar"
  dest_file = f"{ddir(db)}/{db}.rar"
  etag_file = f"{ddir(db)}/{db}.etag"
  temp_etag_file = etag_file + ".inprogress"

  attempt = 0
  done = False
  resume = False
  changed = False

  while attempt < DL_RETRIES and not done:
    if attempt > 0:
      log(f"Retrying {url}... (attempt {attempt})")

    changed, resume = False, False
    etag = None

    # Always prioritize incomplete dl's so they can resume.
    if exists(temp_etag_file):
      # Previous download didn't complete.
      etag = read(temp_etag_file).strip('"') # curl saves quotes to file.
    elif exists(etag_file):
      etag = read(etag_file)

    remote_etag = get_etag(url)
    log(f"Current etag:{etag} remote_etag:{remote_etag}")

    if not etag:
      log(f"First download of {url}")
      changed = True
      etag = remote_etag
    elif remote_etag == etag:
      log(f"Remote file has not changed: {url} etag:{etag}")
      if exists(f"{ddir(db)}/{db}.{etag}.rar.incomplete"):
        log(f"Resuming incomplete download.")
        resume = True
      elif exists(dest_file):
        log(f"Not redownloading {dest_file}, remote file is unchanged.")
        return etag
      else:
        log(f"Downloaded file {dest_file} is missing, re-downloading.")
        # Force redownload, this should be an optional, bc the same dump may not
        # need to be re-imported.
        changed = True
    else:
      log(f"New file at: {url} etag:{etag} remote_etag:{remote_etag}")
      changed = True
      etag = remote_etag
      log(f"Cleaning up temp files for previous import")
      # remove state for previous versions.
      rm_glob(status_file(db, '*', '*'))
      # remove in-progress downloads.
      rm_glob(f"{ddir(db)}/*.rar.incomplete", verbose=True)

    if not changed and not resume:
      done = True
      break
    start = time.time()
    cont = ""
    dl_inprogress = f"{ddir(db)}/{db}.{etag}.rar.incomplete"
    if resume:
        size = get_size(dl_inprogress)
        log(f"Resuming download of {url} ({size})...")
        cont = "-C-"
    else:
        log(f"Downloading {url}...")

    try:
      shell(f"curl -sS --etag-save {temp_etag_file} {cont} -o {dl_inprogress} {url}")
      done = True
      update_etag(temp_etag_file, etag_file)
      mv(dl_inprogress, dest_file)
      end = time.time()
      log(f"Downloaded {url} to {dest_file} in {duration(start, end)}")
      return etag
    except subprocess.CalledProcessError as e:
      print(e)
      attempt += 1

  if not done:
    log(f"ERROR: ** Download of {url} did not complete. **")
    sys.exit(1)

def unpack(db, etag):
  file = f"{ddir(db)}/{db}.rar"
  if is_completed(UNPACK, db, etag):
    log(f"Not unpacking '{file}'")
    return

  s = start(f"Unpacking '{file}'...")
  if not exists(file):
    raise Exception(f"Rar file '{file}' does not exist. Do you need to redownload the dump?")
  shell(f"unrar x -o+ -idq {file} {ddir(db)}/")
  if config['IMPORT_CLEAN']:
    rm_glob(file, verbose=True)
  end(UNPACK, db, etag, f"Unpacked '{file}'", s)
  # don't remove the download bc it takes so long to dl.

def strip_sql(db, etag):
  sql = f"{ddir(db)}/{db}.sql"
  if is_completed(STRIP, db, etag):
    log(f"Not re-stripping '{sql}'")
    return
  s = start(f"Stripping '{sql}' for SQL import ({get_size(sql)})...")

  edit_sql = f"{ddir(db)}/{db}_edit.sql"
  shell(f"sed -f import/edit.sed {sql} > {edit_sql}")

  if config['IMPORT_CLEAN']:
    rm_glob(sql, verbose=True)
  end(STRIP, db, etag, f"Stripped '{sql}'", s)

def split_sql_inserts(db, etag):
  sql = f"{ddir(db)}/{db}.sql"
  if is_completed(SPLIT, db, etag):
    log(f"Not re-splitting inserts from '{sql}'")
    return

  s = start(f"Extracting inserts from sql and splitting '{sql}' ({get_size(sql)})...")

  inserts_sql = f"{ddir(db)}/{db}_inserts.sql"
  split_pattern = f"{inserts_sql}.part-"

  shell(f"sed -f import/edit_{db}.sed {sql} > {inserts_sql}")
  shell(f"split -l 300 --numeric-suffixes {inserts_sql} {split_pattern}")
  files = ls(split_pattern + "*")

  if config['IMPORT_CLEAN']:
    rm_glob(sql, verbose=True)
    rm_glob(inserts_sql, verbose=True)
  end(SPLIT, db, etag, f"Split '{inserts_sql}' into {len(files)} files", s)

def import_sql(db, etag):
  edit_sql = f"{ddir(db)}/{db}_edit.sql"
  if is_completed(DUMP_TO_SQL, db, etag):
    log(f"Not re-importing '{edit_sql}'")
    return
  s = start(f"Running SQL '{edit_sql}' ({get_size(edit_sql)})...")

  shell(f"mysql -h {config['DB_HOST']} -u root --password=$(cat {config['DB_ROOT_PASSWORD_FILE']}) {config['MYSQL_DB']} < {edit_sql}")

  end(DUMP_TO_SQL, db, etag, f"Ran SQL '{edit_sql}'", s)

def import_sql_to_es(db, etag, force_import):
  if not force_import and is_completed(SQL_TO_ES, db, etag):
    log(f"Not re-importing to elasticsearch {db} from SQL database.")
    return
  s = start(f"Starting elasticsearch import for {db} from SQL database...")

  sql_to_es.main(db)

  end(SQL_TO_ES, db, etag, f"Imported {db} to elasticsearch from SQL database", s)

def import_dump_to_es(db, etag, compare, force_import):
  if not force_import and is_completed(DUMP_TO_ES, db, etag):
    log(f"Not re-importing to elasticsearch '{db}' from file.")
    return
  s = start(f"Starting elasticsearch import for {db} from sql files...")

  dump_to_es.main(db, compare=compare, es_import=True)

  end(DUMP_TO_ES, db, etag, f"Imported {db} to elasticsearch from file.", s)

def parse_dump_and_compare(db, etag):
  inserts_sql = f"{ddir(db)}/{db}_inserts.sql"
  s = start(f"Starting elasticsearch CHECK for {db} from file ({get_size(inserts_sql)})...")

  dump_to_es.main(db, compare=True, es_import=False)

  end(DUMP_TO_ES, db, etag, f"Finishing checking {db}.", s)

def get_etag(url):
  etag = requests.head(url).headers.get('etag')
  if not etag:
    raise Exception(f"No etag for url {url}")
  return etag.strip('"')

UNPACK =      'unpacked'
STRIP =       'isedited'
SPLIT =       'isplit--'
DUMP_TO_SQL = 'dump2sql'
SQL_TO_ES =   'sql2es--'
DUMP_TO_ES =  'dump2es-'
stages = [UNPACK, STRIP, SPLIT, DUMP_TO_SQL, SQL_TO_ES, DUMP_TO_ES]

def completed(stage, db, etag):
  if stage not in stages:
    raise Exception("Unknown stage ${stage}")
  # invalidate other etags completed, they all go to the same destination files
  rm_glob(status_file(db, stage, '*'))
  touch(status_file(db, stage, etag))

def is_completed(stage, db, etag):
  if stage not in stages:
    raise Exception("Unknown stage ${stage}")
  done = exists(status_file(db, stage, etag))
  if not done:
    # Stages following the uncompleted stage become uncompleted,
    # because their dependencies have changed.
    for s in stages[stages.index(stage):]:
      rm(status_file(db, s, etag))
  return done

def status_file(db, stage, etag):
  host = url_to_filename(os.environ['ELASTIC_HOST'])
  return f"{ddir(db)}/completed_{host}-{stage}-{etag}"

def start(s):
  s and log(s)
  return time.time()

def end(stage, db, etag, s, start):
  completed(stage, db, etag)
  t = duration(start, time.time())
  log(f"{s} in {t}")

def end_(s, start):
  t = duration(start, time.time())
  log(f"{s} in {t}")

def update_etag(temp, dest):
  etag = read(temp).strip('"')
  write(dest, etag)
  rm(temp)

def drop_table(db):
  # log(f"Dropping table '{db}'")
  # shell(f"echo \"DROP TABLE {config['DB']}\" | mysql -h {config['DB_HOST']} -u root --password=$(cat {config['DB_ROOT_PASSWORD_FILE']}) {config['DB']} || true")
  pass

def clean(db, failed):
  if config['IMPORT_CLEAN']:
    rm_glob(f"{ddir(db)}/completed_*", verbose=True)
    rm_glob(f"{ddir(db)}/*.rar", verbose=True)
    rm_glob(f"{ddir(db)}/*.sql", verbose=True)
    rm_glob(f"{ddir(db)}/*.sql.part-*", verbose=True)
    # Dont remove the etag, it is used to tell if this version has already been imported.
    # rm_glob(f"{ddir(db)}/etag_*", verbose=True)
    if not failed:
      # Only remove this if the import succeeded, so failed import can be resumed.
      rm_glob(f"{ddir(db)}/imported_to_*", verbose=True)

def setup_index():
  if 'NEW_INDEX' in os.environ:
    # New index set by env var.
    os.environ['CURRENT_INDEX'] = other_index(os.environ['NEW_INDEX'])
    return
  # Index not set, get current index from elastic search.
  current_indexes = es.get_alias_indexes(config['ES_ALIAS'])
  new_index = config['INDEX1']
  if new_index in current_indexes:
    new_index = config['INDEX2']
  os.environ['NEW_INDEX'] = new_index
  os.environ['CURRENT_INDEX'] = other_index(new_index)

def swap_index():
  alias = config['ES_ALIAS']
  new_index = os.environ['NEW_INDEX']
  current_indexes = es.get_alias_indexes(alias)
  log(f"-- Swapping {alias}, from {current_indexes} to {new_index} --")

  if new_index in current_indexes:
    raise Exception(f"Index '{new_index}'' is already a current index for '{alias}'")

  es.swap_alias_indexes(alias, os.environ['CURRENT_INDEX'], new_index)
  if config['IMPORT_CLEAN']:
    prev_index = os.environ['CURRENT_INDEX']
    log(f"-- Deleting old index {prev_index} --")
    es.delete_index(prev_index)

def other_index(idx):
  if idx == config['INDEX1']:
    return config['INDEX2']
  return config['INDEX1']

def mail(subject, body):
  if os.environ.get('IMPORT_MAIL') != 'True':
    return
  to = os.environ.get('TO_ADDRESS')
  from_ = os.environ.get('FROM_ADDRESS')
  message = Mail(
      from_email=from_,
      to_emails=to,
      subject=subject,
      html_content=f"<h3>Logs</h3><pre>{body}</pre>")
  log(f"Sending mail '{subject}' to {to} from {from_}")
  sg = SendGridAPIClient(read_value(os.environ.get('SENDGRID_API_KEY_FILE')))
  response = sg.send(message)
  if response.status_code != 202:
    log(f"Failed to send mail: response {response.status_code}\n{response.headers}")

class Mode(Enum):
  MYSQL_IMPORT = 1 # Import to MySQL only.
  MYSQL_IMPORT_AND_ES_IMPORT = 2 # Import to MySQL first and then to ES (default is straight to ES).
  DUMP_FILE_IMPORT = 3 # Import to ES (default).
  ES_COMPARE = 4 # Compare dump file to ES data.
  ES_COMPARE_AND_IMPORT = 5 # Compare dump file to current data in ES and import.

  def from_str(s):
    try:
      return Mode[s]
    except KeyError:
      print(f"Invalid mode '{s}', try {joinl(Mode.values(),', ')}")
      sys.exit(1)
  def values():
    return list(Mode.__members__.keys())

if __name__ == "__main__":
  do_download = True
  do_swap = True
  force_import = False
  mode = Mode.DUMP_FILE_IMPORT

  try:
      opts, args = getopt.getopt(sys.argv[1:], "dcnfm:", [])
  except getopt.GetoptError as err:
      print(f"""Usages import:
-d (no download)
-c (no clean)
-n (no index swap)
-f (force re-import to elasticsearch)
-m ({joinl(Mode.values(),'|')})""")

      print(str(err))
      sys.exit(2)

  for opt, arg in opts:
    if opt == '-d': # Dont re-download
      do_download = False
    if opt == '-n': # Dont swap indexes after import
      do_swap = False
    if opt == '-f': # Re-import even if stage has already completed.
      force_import = True
    elif opt == '-c': # Don't clean up files
      config['IMPORT_CLEAN'] = False
    elif opt == '-m':
      mode = Mode.from_str(arg)

  dbs = []
  if args:
    dbs = args
  else:
    dbs = split(config['DBS'], sep=' ')
  if not dbs:
    print("No dbs to import.")
    sys.exit(2)

  setup_list_handler()
  es = ElasticSearchAdmin()
  main(dbs, do_download, mode, do_swap, force_import)
