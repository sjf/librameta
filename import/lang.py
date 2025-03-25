import pycountry
import langcodes
import sys
import regex
from functools import lru_cache
from mbutils import non_empty
from datetime import datetime

__all__ = ['get_langcode', 'get_year']

# Top world languages in order of popularity (plus a couple like greek that often need a regex to be matched).
_TOP_LANGS = ['eng', 'rus', 'zho', 'spa', 'hin', 'ben', 'por', 'jpn', 'pan', 'mar',
              'tel', 'tur', 'kor', 'fra', 'deu', 'vie', 'ara', 'ell', 'nld']

_by_name = {}
_by_native = {}
_by_code2 = {}
_by_code3 = {}
_top_lang_regexes = {}
current_year = datetime.now().year

# Function to list all languages with their ISO codes and names
def _build_language_lookup_tables(output=None):
  for language in pycountry.languages:
    if language.alpha_3 == 'und': # code for undertermined language, we are using `None` for that.
      continue
    if language.alpha_3 == 'enc':
      # English (Canadian), but it is not set up correctly in the module and the name is 'En'
      # which causes problems with 'en' for English.
      continue
    code3 = language.alpha_3
    code2 = None
    if hasattr(language, 'alpha_2'):  # Check if the language has a 2-letter code
      code2 = language.alpha_2

    name = regex.sub('\\(.*\\)','',language.name).lower() # remove any part of the name in parantheses
    if code2 == 'el':
      name = 'greek' # greek has wierd official name that is not used in libmeta.

    lc = langcodes.get(code3)
    native = lc.language_name(lc.language).lower()

    reg = None
    if code3 in _TOP_LANGS:
      reg = f"^(.*[^a-z]|)({name}|{code3}|{code2})([^a-z].*|)$"
      _top_lang_regexes[code3] = regex.compile(reg)

    lang = {'language': language, 'code3': code3, 'code2': code2, 'name': name, 'native': native, 'regex': reg}
    _by_code3[code3] = lang

    _by_name[name] = lang
    _by_native[native] = lang
    if code2:
      _by_code2[code2] = lang

  if not output:
    return

  # Output the lookup table and entries which have issues.
  for code3,lang in _by_code3.items():
    print(f"{code3} {lang}")
  print()
  # Unfortunately there are some languages where the code3 is the name for a /different/ language.
  # We give priority to the name, not the code3, so these are not recognised correctly.

  # There are also some languages where the name matches the code3 for a different language.
  # These are recognized correctly, because the name has priority.

  # There are some native names that have multiple code3s. These will be recognized as
  # whichever of them comes last alphabetically.
  for language in pycountry.languages:
    code3 = language.alpha_3
    if code3 not in _by_code3:
      continue

    if code3 in _by_name and _by_name[code3]['code3'] != code3:
      print(f"{language.name}({code3}) code3 matches name for {_by_name[code3]}")
    if code3 in _by_native and _by_native[code3]['code3'] != code3:
      print(f"{language.name}({code3}) code3 matches native name for {_by_native[code3]}")

    name = _by_code3[code3]['name']
    if name in _by_name and _by_name[name]['code3'] != code3:
      print(f"{name}({code3}) name matches name for {_by_name[name]}")
    if name in _by_native and _by_native[name]['code3'] != code3:
      print(f"{name}({code3}) name matches native name for {_by_native[name]['code3']}")

    native = _by_code3[code3]['native']
    if native in _by_name and _by_name[native]['code3'] != code3:
      print(f"{native}({code3}) native name matches name for {_by_name[native]}")
    if native in _by_native and _by_native[native]['code3'] != code3:
      print(f"{native}({code3}) native name matches native for {_by_native[native]}")

@lru_cache(maxsize=None) # Don't limit the cache size because there's not that many (<5k) unique values for language.
def get_langcode(s, output='code3'):
  if not s:
    return None
  s = s.strip().lower()
  # s is a language name in english
  if s in _by_name:
    return _by_name[s][output]
  # s is a alpha-2 language code
  if s in _by_code2:
    return _by_code2[s][output]
  # native language name
  if s in _by_native:
    return _by_native[s][output]
  # alpha-3 language code.
  if s in _by_code3:
    return _by_code3[s][output]
  # look for regexes matches of the top most
  # popular languages, for cases like 'English,Russian'.
  # Prioritize the most popular language b/c there
  # can only be one language recognized.
  for code3 in _TOP_LANGS:
    if regex.match(_top_lang_regexes[code3], s):
      return _by_code3[code3][output]
  return None

# Match 4 consequective unicode digits, surround by unicode word boundary.
YEAR_REGEX = regex.compile(r'\b(\p{Nd}{4})\b')
# Another regex that will match a 4 digit number without depending on unicode word boundaries.
YEAR_REGEX_2 = regex.compile(r'^(.*[^0-9]|)(\p{Nd}{4})([^0-9].*|)$')

@lru_cache(maxsize=None) # There are ~11k values for year.
def get_year(s):
  years = regex.findall(YEAR_REGEX, s)
  result = None
  if years:
    result = get_lowest_year_as_int(years)
  if not result:
    years2 = regex.findall(YEAR_REGEX_2, s)
    if years2:
      result = get_lowest_year_as_int(map(lambda m:m[1], years2))
  return result

def get_lowest_year_as_int(years):
  years = map(unicode_to_ascii_year, years)
  years = non_empty(years)
  if not years:
    return None
  return min(years)

@lru_cache(maxsize=None)
def unicode_to_ascii_year(text):
  try:
    n = int(text)
  except ValueError:
    return None
  # Year is before 1000CE, this is probably wrong.
  if n < 1000:
    return None
  # Year is in the future, also wrong.
  if n > current_year:
    return None
  return n

if __name__ == '__main__':
  _build_language_lookup_tables(output=True)
else:
  _build_language_lookup_tables()
