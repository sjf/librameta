#!/usr/bin/env python
from query import *
from query import _get_browser_lang3

def test_is_advanced_neg():
  queries = [
    # basic searches
    Query('/search'),
    Query('/', {'search':'foo'}),
    Query('/', {'search':'foo', 'page': '1'}),
    Query('/', {'search':'foo', 'page': '0'}),
    Query('/', {'search':'foo','sort':'size'}),
    Query('/', {'search':'foo','sort':'size','order':'desc'}),
    Query('/', {'search':'foo','sort':'size','order':'desc'}),
    # url is advanced, but query is basic
    Query('/search-adv', {'search':'foo','sort':'size','order':'desc'}),
    # No search params
    Query('/', {'year':'1990','sort':'size','order':'desc'})
  ]
  for query in queries:
    assert not query.is_advanced, query

def test_is_advanced_pos():
  queries = [
    # advanced url path
    Query('/adv',{}),
    Query('/search-adv',{}),
    # advanced queries
    Query('/', {'title':'foo'}),
    Query('/', {'title':'foo', 'page': '1'}),
    Query('/', {'author':'foo','sort':'size'}),
    Query('/', {'series':'foo','sort':'size','order':'desc'}),
    Query('/', {'author':'foo','sort':'size','order':'desc'}),
    # basic path, but advanced queries
    Query('/search', {'title':'foo'}),
    Query('/search', {'title':'foo'}),
  ]
  for query in queries:
    assert query.is_advanced, query

def test_get_browser_lang3():
  assert _get_browser_lang3([('en-US', 1.0), ('en', 0.9), ('fr', 0.8), ('de', 0.7)]) == 'eng'
  assert _get_browser_lang3([('invalid', 1.0), ('en', 0.9), ('fr', 0.8), ('de', 0.7)]) == None
  assert _get_browser_lang3([]) == None
  assert _get_browser_lang3([('*', 1.0)]) == None
