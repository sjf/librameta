import sys
import logging
import os
from copy import deepcopy
import json
import langcodes
from flask import flash

import urllib
from util import *
from mbutils import read, split, joinl, dictl, filterd, config, iso_language_names_by_code

EXTS = ['epub', 'mobi', 'pdf', 'djvu']
SORT_FIELDS = ['year','size']
ORDER_VALUES = ['asc','desc']

class Query:
  param_names = ['search', 'title', 'author', 'series', 'isbn', 'doi','lang','exts',
  'page_num','year','start_year','end_year','sort','order']
  advanced_param_names = ['title', 'author', 'series', 'isbn', 'doi','lang','exts',
  'year','start_year','end_year']

  def __init__(self, path, args={}, accept_languages=None):
    self.path = path

    self.has_search_query = False
    # All the string type search params, don't need conversion or validation.
    for key in ['search', 'title', 'author', 'series', 'isbn', 'doi']:
      self.__dict__[key] = None
      if is_set(args, key):
        self.has_search_query = True
        self.__dict__[key] = _sanitize(args[key])

    self.lang,self.display_lang = _get_language_from_request(args)
    self.exts = _get_exts_from_request(args)
    self.page_num = _get_page_num_from_request(args)
    self.browser_lang = _get_browser_lang3(accept_languages)
    self.year = _get_year(args)
    self.start_year, self.end_year = _get_year_range(args)
    self.sort, self.order = _get_sort(args)
    self.was_expanded = _get_expanded(args)

  @property
  def is_advanced(self):
    if not self.has_search_query:
      return self.path in ['/adv', '/search-adv']
    return bool(set(self.params().keys()) & set(self.advanced_param_names))

  def toggle_sort(self, sort=None, order=None):
    if sort not in SORT_FIELDS or order not in ORDER_VALUES:
      raise Exception("Invalid sort parameter.")
    copy = deepcopy(self)
    if self.sort_eq(sort, order):
      # Toggle this sort off
      copy.sort, copy.order = None, None
    else:
      copy.sort, copy.order = sort, order
    return copy

  def sort_eq(self, sort, order):
    return self.sort == sort and self.order == order

  def encode(self):
    return urllib.parse.urlencode(self.params(), doseq=True)

  def params(self):
    params = {}
    for name in self.param_names:
      if self.__dict__[name]:
        params[name] = self.__dict__[name]
    return params

  def __str__(self):
    dict_ = filterd(lambda k,v:not k.startswith('__'), self.__dict__)
    return f'<Query {dict_} is_advanced:{self.is_advanced}>'

def is_set(args, key):
  if not key in args:
    return False
  # Only whitespace is not considered a value.
  value = args[key].strip()
  return bool(value)

def _sanitize(s):
  s = s.strip("'") # Dont strip double quotes.
  s = s.strip()
  return s

def _get_language_from_request(args):
  if not is_set(args, 'lang'):
    # # No lang param, use preferred browser lang
    # return get_preferred_lang_code(request)
    return None, None # disabling this for now.
  code = args['lang'].lower()
  if not(len(code) == 3 and langcodes.tag_is_valid(code)):
    flash(f"Invalid language '{code}'")
    return None,None
  display_name = code
  # iso_language_names_by_code is the same dataset used by the client-side.
  if code in iso_language_names_by_code:
    display_name = iso_language_names_by_code[code]
  return code,display_name

def _get_exts_from_request(args):
  if not is_set(args, 'ext'):
    return None
  parts = args.getlist('ext')
  exts = [ p for p in parts if p in EXTS ]
  invalid = [ p for p in parts if p not in EXTS ]
  if invalid:
    flash(f"Unsupported file type: {', '.join(invalid)}")
    return None
  if exts:
    return exts

def _get_year_range(args):
  start_year = None
  end_year = None
  if is_set(args, 'start_year'):
    try:
      start_year = int(args['start_year'])
    except ValueError:
      flash("Year must be a number")
      return None, None

  if is_set(args, 'end_year'):
    try:
      end_year = int(args['end_year'])
    except ValueError:
      flash("Year must be a number")
      return None, None

  if start_year and end_year and start_year > end_year:
      flash("Start year must be earlier than end year.")
      return None, None
  return start_year,end_year

def _get_year(args):
  if not is_set(args, 'year'):
    return None
  try:
    return int(args['year'])
  except ValueError:
    flash("Year must be a number")
    return None

def _get_page_num_from_request(args):
  if not is_set(args, 'page'):
    return 0
  try:
    val = int(args['page'])
  except ValueError:
    return 0
  if val > config['MAX_PAGE_NUM']:
    flash("Something went wrong")
    return 0
  return val

def _get_sort(args):
  if not is_set(args, 'sort'):
    return None, None

  sort = args['sort']
  if sort == 'relevance':
    # 'relevance' is treated the same as the default/no value for sort.
    return None, None
  if not sort in SORT_FIELDS:
    flash('Invalid sort parameter.')
    return None, None

  order = 'desc' # default order is descending
  if is_set(args, 'order'):
    order = args['order']
    if order not in ORDER_VALUES:
      flash('Invalid sort parameter.')
      return None, None

  return sort,order

def _get_browser_lang3(accept_languages):
  """ Return the alpha3 lang code requested by the client. """
  if not accept_languages or not accept_languages[0]:
    return None
  # Full language code, e.g. en-US.
  language_code = accept_languages[0][0]
  try:
    language = langcodes.Language.get(language_code)
  except Exception as e:
    # Some clients send "*" as the language.
    return None
  # langcodes will let you create an object for an invalid code.
  # So check validity.
  if language.is_valid():
    return language.to_alpha3()
  return None

def _get_expanded(args):
  if not is_set(args, 'x'):
    return False
  return args['x'] == '1'
