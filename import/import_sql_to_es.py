#!/usr/bin/env python3
from sqlalchemy import create_engine
import pandas as pd
import time, humanfriendly, os, elasticsearch, sys
from mbutils import get_db_uri, log, debug, load_config
from es_admin import *
from model import *
from files import *

RETRIES = 3
config = load_config({
  'BATCH_SIZE': 20_000,
  'OFFSET': 0,
})

def main(db, config=config):
  log(f"-- Importing {db} from SQL to ES, offset: {config['OFFSET']} --")
  start = time.time()

  engine = create_engine(get_db_uri())
  es = ElasticSearchAdmin()

  batch_size = config['BATCH_SIZE']
  offset = config['OFFSET']
  if db in ('libmeta', 'libmeta_compact'):
    table = 'updated'
  elif db == 'fiction':
    table = 'fiction'
  else:
    sys.stderr.write(f"Unknown db '{db}'\n")
    sys.exit(1)

  queryfmt = """SELECT * FROM {table} WHERE (visible is NULL OR visible = '') LIMIT {batch_size} OFFSET {offset}"""

  total = 0
  bad = []
  while True:
    query = queryfmt.format(table = table, batch_size = batch_size, offset = offset)

    debug(query)
    try:
      df = pd.read_sql(query, engine)
      if df.empty:
        break
    except UnicodeDecodeError as e:
      if batch_size == 1:
        log(f"Bad offset {offset} {e}")
        bad.append(offset)
        offset += 1
        batch_size = config['BATCH_SIZE'] # original value
        continue
      else:
        # repeat with binary search to get offset of problem row.
        log(f"UnicodeDecodeError at {offset} - {offset + batch_size}")
        batch_size = int(batch_size / 2)
        continue
    if batch_size != config['BATCH_SIZE']:
      batch_size = batch_size * 2

    success, errors = es.upsert(df_to_es_docs(db, df))
    total += success
    bad.extend(errors)
    offset += batch_size

    debug(f"Imported {db} {total:,} rows so far...")

  # Export finished.
  end = time.time()
  log(f"Elapsed time: {humanfriendly.format_timespan(end - start)}")
  log(f"Bad entries skipped: {len(bad)}, see {bad_file(db)}")
  write(bad_file(db), joinl(bad))
  if success:
    log(f"Data import of {db} completed successfully!")
  else:
    raise Exception(f"No records imported into {db}.")


def df_to_es_docs(db, df):
  for _, row in df.iterrows():
    doc = to_es_doc(db, row.to_dict())
    if not doc:
      # Don't try to import invalid rows.
      continue
    else:
      yield doc

if __name__ == '__main__':
  if len(sys.argv) < 2:
    sys.stderr.write("Usage: es_import.py <db-name>\n")
    sys.exit(1)
  main(sys.argv[1])

