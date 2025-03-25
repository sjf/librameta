import os
import sys
import time
from mbutils import *
from lang import *

__all__ = ['row_to_doc', 'to_es_doc']

# Non-fic database column names
non_fiction_db_cols = ['ID', 'Title', 'VolumeInfo', 'Series', 'Periodical', 'Author', 'Year', 'Edition', 'Publisher', 'City', 'Pages', 'PagesInFile',
  'Language', 'Topic', 'Library', 'Issue', 'Identifier', 'ISSN', 'ASIN', 'UDC', 'LBC', 'DDC', 'LCC', 'Doi', 'Googlebookid', 'OpenLibraryID',
  'Commentary', 'DPI', 'Color', 'Cleaned', 'Orientation', 'Paginated', 'Scanned', 'Bookmarked', 'Searchable', 'Filesize', 'Extension', 'MD5',
  'Generic', 'Visible', 'Locator', 'Local', 'TimeAdded', 'TimeLastModified', 'Coverurl', 'Tags', 'IdentifierWODash']
# These DB columns can be copied directly to the ES doc.
non_fiction_es_cols = ['IdentifierWODash', 'Doi', 'Title', 'Author', 'Series', 'Edition', 'VolumeInfo', 'Periodical', 'Issue', 'Year', 'Publisher',
  'Language', 'Extension', 'Pages', 'PagesInFile', 'Coverurl']

# Fiction database column names
fiction_db_cols = ['ID', 'MD5', 'Title', 'Author', 'Series', 'Edition', 'Language', 'Year', 'Publisher', 'Pages', 'Identifier', 'GooglebookID',
  'ASIN', 'Coverurl', 'Extension', 'Filesize', 'Library', 'Issue', 'Locator', 'Commentary', 'Generic', 'Visible', 'TimeAdded', 'TimeLastModified']
# These DB columns can be copied directly to the ES doc.
fiction_es_cols = ['Title', 'Author', 'Series', 'Edition', 'Issue', 'Year', 'Publisher', 'Language', 'Pages', 'Extension', 'Coverurl']

# Extensions in order of preference.
extensions = [
  'epub',
  'mobi',
  'azw3', 'azw',
  'fb2', # eastern european ebook format
  'pdf', 'djvu',
  'docx', 'doc',
  'rar', # I dont know how to score this.
  'rtf',
  'chm',
  'html',
  'lit', # Obsolete MS ebook format.
  'txt',
  # Everything else is scored the worst.
]
extension_scores = defaultdict(lambda:len(extensions), {ext:idx for idx,ext in enumerate(extensions)})

def row_to_doc(db, row):
  # Convert a DB row, a list of values, to an elasticsearch doc.

  if db in ['libmeta', 'libmeta_compact']:
    db_columns = non_fiction_db_cols
  elif db == 'fiction':
    db_columns = fiction_db_cols
  else:
    log(f"Unknown db '{db}'")
    sys.exit(1)

  if len(row) != len(db_columns):
    log(f"Row too short: {len(row)}\n{row}")
    sys.exit(1)
  dict_ = dict(zip(db_columns, row))
  try:
    return to_es_doc(db, dict_), None
  except Exception as e:
    log_error(f'Failed to convert to ES doc: {dict_}')
    raise e;

def to_es_doc(db, row):
  if row['Visible'] in ['no','ban','del']:
    # Don't import hidden rows.
    return None

  if db in ['libmeta','libmeta_compact']:
    prefix = 'nf'
    es_columns = non_fiction_es_cols
  elif db == 'fiction':
    prefix = 'f'
    es_columns = fiction_es_cols
  else:
    log(f"Unknown db '{db}'")
    sys.exit(1)

  source = {}
  for k in es_columns:
    source[k] = row[k]

  source['ID'] = prefix + str(row['ID']) # The ID numbers will overlap between the databases.
  source['MD5'] = row['MD5'].upper() # MD5 in the db is case-insensitive.
  source['lang3'] = get_langcode(row['Language']) # alpha-3 language code.
  source['Filesize'] = to_es_int(row['Filesize']) # Convert big-int to int64.
  source['year_'] = get_year(row['Year']) # Numeric value of year.
  source['full_title'] = f"{source['Title']} {source['Author']} {source['Series']}"
  source['extension_score'] = extension_scores[row['Extension']] # The ranking of the filetypes is static, so precompute it.
  if 'descr' in row:
    source['Description'] = row['descr']
  if 'Descr' in row:
    source['Description'] = row['Descr']
  if db == 'fiction':
    source['IdentifierWODash'] = row['Identifier']
  return { "_index": os.environ['NEW_INDEX'],
           "_id": source['ID'],
           "_source": source }

def to_es_int(n):
  n = int(n)
  # Just truncate ints that are too big to fit in int32.
  # This only happens for one out of 7million records.
  max_int = (2**31)-1
  min_int = -(2**31)
  if n > max_int:
    return max_int
  if n < min_int:
    return min_int
  return n

