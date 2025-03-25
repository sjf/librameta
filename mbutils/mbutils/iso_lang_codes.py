#!/usr/bin/env python
import sys
import csv
import os
import re
import unidecode
from collections import defaultdict
import importlib.resources

__all__ = ['iso_languages', 'iso_language_names_by_code']

def no_ascii(s):
  s = s.strip()
  s = s.strip(')')
  s = s.strip('(')
  return all(ord(c) > 127 for c in s)

def add(result, name, code, fold=True):
  name = name.strip()
  assert name, (name, code)
  assert len(code) == 3
  # if name not in result:
  #   result[name] = (name, code)
  search_names = [name.lower()]
  # if name.lower() not in result:
  #   # print(name)
  if fold and not no_ascii(name):
    ascii_folded = unidecode.unidecode(name).lower()
    if ascii_folded != name.lower():
      search_names.append(ascii_folded)
    # if ascii_folded.lower() not in result:
    #   # Dont include it already matches, e.g. the english name.
    #   # print(f"{name} -> {ascii_folded}")
    #   # result[ascii_folded] = (name, code)
    #   result[ascii_folded.lower()] = [name, code]
  result.append([search_names, name, code])

def open_csv(is_main):
  file_name = 'ISO 639 language codes.csv'
  if is_main:
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    fh = open(file_path)
    return csv.reader(fh)
  else:
    fh = importlib.resources.open_text('mbutils', file_name)
    return csv.reader(fh)

def process(is_main):
  reader = open_csv(is_main)
  for row in reader:
    try:
      english,code,type,status,natives = row
      # print([code, english, natives])
    except ValueError:
      print(row)
      sys.exit(1)
    if code == 'ell':
      english = 'Greek'
      natives = 'Ελληνικά (Elliniká)'
    english_names = english.split(',')
    for name in english_names:
      add(iso_languages, name, code, True) # fold english name, only affects 1-2 anyway.
    iso_language_names_by_code[code] = english_names[0];

    for part in natives.split(';')[::-1]:
      # Iterate in reverse order, so first items will have priority bc some have multiple names with the same transliteration.
      for native in part.split('('):
        if '(' in part and not ')' in native:
          # This name has a transliteration, but this is the original name.
          # Do not try to fold it because the transliteration is closer to the ascii version.
          fold = False
        else:
          fold = True

        native = native.strip()
        native = native.strip(')')
        if not native:
          continue
        # not adding native names right now because with ascii folding there ends up with too
        # many duplicates.
        # add(result, native, code, fold)

iso_languages = []
iso_language_names_by_code = {} # map from lang code to display name. Currently first english name.

process(__name__ == '__main__')

if __name__ == '__main__':
  print(f'languages = {iso_languages};')
  print(f'language_names_by_code = {iso_language_names_by_code};')
