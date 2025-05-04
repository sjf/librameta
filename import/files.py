from mbutils import *

# Files and directories used during import.

def ddir(db):
  d = f"{os.getenv('DUMP_DIR')}/{db}"
  if not exists(d):
    mkdir(d)
  return d

def bad_file(db):
  return output_file("bad", db)

def progress_file(db):
  return output_file("imported_to", db)

def missing_file(db):
  return output_file("missing", db)

def output_file(prefix, db):
  host = url_to_filename(os.environ['ELASTIC_HOST'])
  index = os.environ['NEW_INDEX']
  return f"{ddir(db)}/{prefix}_{host}_{index}.txt"
