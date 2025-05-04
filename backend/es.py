import re
import elasticsearch
from elasticsearch import Elasticsearch
from util import nonzero, log
from mbutils import read, split, cmp, dictl, read_value, uniq, index_or_default, non_empty, joinl, printd
import langcodes
from functools import cmp_to_key
from collections import defaultdict
import json
import os
import shlex

from book import Book, sanitize_isbn
from result import Result

COVER_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"
FALLBACK_COVER = "/static/cover.png"
LIMIT = 50
INDEX = 'libmeta_alias'

class ElasticSearch:
  def __init__(self):
    host = os.environ.get('ELASTIC_HOST')
    api_key = read_value(os.environ.get('ELASTIC_API_KEY_FILE'))
    log(f"Connecting to Elasticsearch {host}")
    self.es = Elasticsearch(host, api_key = api_key)
    self.page_size = int(os.environ.get('PAGE_SIZE'))

  def search(self, query):
    and_terms = []
    unquoted = None
    if query.search and not query.was_expanded:
      or_terms = [] # Match any of full title, isbn or doi.
      unquoted, quoted = get_quoted_substrings(query.search)
      if unquoted:
        unquoted_t = inexact_phrase('full_title', self.tokenize(unquoted), 400, 300, 50, 0)
        if not quoted:
          or_terms.append(unquoted_t)
      if quoted:
        quoted_ts = [exact_phrase('full_title', q, 500) for q in quoted]
        if unquoted:
          # Include the unquoted phrase in the `and` clause
          quoted_ts.append(unquoted_t)
        # All quoted strings must be present.
        or_terms.append(es_and(quoted_ts))
      or_terms.append(contains_words("IdentifierWODash", sanitize_isbn(query.search)))
      or_terms.append(exact_string("Doi", query.search))
      and_terms.append(es_or(or_terms))
    elif query.search and query.was_expanded:
      # Treat the query as if it was all unquoted.
      and_terms.append(contains_words("full_title", query.search, 75, fuzzy=True))

    if query.title:
      # Assume the user has the exact title, as if it was quoted.
      and_terms.append(exact_phrase("Title", query.title))
    if query.author:
      # All the words in the author query appear in the author field.
      # The first/last name can be in order, so order is disregarded for sorting.
      # Words like editor, et al, etc are removed by the author analyser.
      and_terms.append(contains_words("Author.author_analyser", query.author))
    if query.series:
      # Assume the user has the exact series, as if it was quoted.
      and_terms.append(exact_phrase("Series", query.series))
    if query.isbn:
      and_terms.append(contains_words("IdentifierWODash", sanitize_isbn(query.isbn)))
    if query.doi:
      and_terms.append(exact_string("Doi", query.doi))

    filters = get_filters(query)
    sort = get_sort(query)

    os.environ.get('DEBUG','') and print(query) # ssss
    search_expanded = False
    es_query = es_and(and_terms, filters)
    hits = self._search(es_query, sort, query.page_num)

    if not hits and not query.was_expanded and query.search and unquoted:
      # Repeat search with expanded query if the search was not quoted.
      query.was_expanded = True
      return self.search(query)

    result = Result(query, hits)
    os.environ.get('DEBUG','') and (print(result)) # ssss
    return result

  def _search(self, es_query, sort, page_num):
    body = {
      "query": es_query,
      "sort": sort,
      "from": page_num * self.page_size,
      "size": self.page_size + 1
    }
    os.environ.get('DEBUG','') and (print(INDEX), print(json.dumps(body,indent=2))) # ssss
    search_response = self.es.search(index=INDEX, body=body)
    # Just return the list of results.
    return search_response['hits']['hits']

  def tokenize(self, s):
    if not s:
      return []
    # Split `s` using the search_analyser.
    body = {'analyzer': 'search_analyser', 'text': s}
    response = self.es.indices.analyze(index=INDEX, body=body)
    return [token['token'] for token in response['tokens']]

  def search_by_md5(self, md5, main_index=True):
    # This only works if elasticsearch has indexed md5, which is not the default.
    # There are two tables in the source data, they can have overlapping md5s.
    body = {"query": exact_string("MD5", md5.upper()), "size": 2}
    search_response = self.es.search(index=INDEX, body=body)
    os.environ.get('DEBUG','') and print(body, search_response)
    for hit in search_response['hits']['hits']:
      book = Book(hit)
      if main_index and book.is_nonfiction:
        return book
      elif not main_index and book.is_fiction:
        return book
    return None

def get_filters(query):
  result = []
  if query.lang:
    result.append(exact_string("lang3", query.lang))
  if query.exts:
    result.append(any_exact_string("Extension", query.exts))
  if query.year:
    result.append(exact_string("year_", query.year))
  if query.start_year or query.end_year:
    year_range = {}
    if query.start_year:
      year_range["gte"] = query.start_year
    if query.end_year:
      year_range["lte"] = query.end_year
    result.append({"range": {"year_": year_range}})
  return result

def get_sort(query):
  result = []
  # User defined sort.
  if query.sort:
    # Docs with missing values are placed at the end.
    if query.sort == 'year':
      result.append({'year_': {'order': query.order}})
    elif query.sort == 'size':
      result.append({'Filesize': {'order': query.order}})
    else:
      raise Exception(f"Unhandled sort field {query.sort}")

  if query.browser_lang:
    # Sort by language matches browser language.
    result.append({
      "_script": {
        "type": "number",
        "script": {
          "source": f"""
            if (doc['lang3'].size() == 0) {{
              return 1;
            }}
            if (doc['lang3'].value == '{query.browser_lang}') {{
              return 0;
            }}
            return 2;
          """
        },
        "order": "asc"
      }
    })
  # Sort by query match.
  result.append("_score")
  # Sort by extension preference.
  result.append({"extension_score": {"order": "asc"}})
  # Sort by filesize, descending.
  if query.sort != 'size': # Don't sort on size twice.
    result.append({"Filesize": {"order": "desc"}})
  return result

def split_quotes(s):
  lex = shlex.shlex(s)
  lex.quotes = '"'
  lex.whitespace_split = True
  lex.commenters = ''
  return list(lex)

def get_quoted_substrings(s):
  # Split s into unquoted search terms and quoted terms.
  # Returns the unquoted terms and a list of quoted terms.
  # The quoted terms will _not retain the enclosing quotes.
  try:
    parts = split_quotes(s)
  except ValueError:
    # Unclosed quote
    try:
      parts = split_quotes(s + '"')
    except:
      return [s],[] # Couldn't parse query.

  quoted, unquoted = [], []
  for p in parts:
    if not p:
      continue # no empty strings
    if p[0] == '"' and p[-1] == '"':
      if len(p) > 2: # no empty quoted strings.
        quoted.append(p[1:-1]) # remove quotes.
    else:
      unquoted.append(p)
  unquoted = joinl(unquoted, ' ', empty='')
  return unquoted, quoted

# Sort by whether ISBN is present. (field is not indexed)
# {
#   "_script": {
#     "type": "number",
#     "script": {
#       "source": f"""
#         if (doc['IdentifierWODash'].value != '') {{
#           return 0;
#         }} else {{
#           return 1;
#         }}
#       """,
#       # "order": "desc"
#     }
#   }
# },

# Document contains the _exact_ search query.
# The terms maybe moved by `slop` positions, they will be scored lower however.
# Slop can fix the author first/last name ordering problem, but it is not ideal
# because they will be scored lower for being re-ordered.
# match_phrase does not support fuzziness.
def exact_phrase(field, s, boost=1, slop=0):
  return {
     "match_phrase": {
        field: {
          "query": s,
          "slop": slop,
          "boost": boost
        }
      }
    }

# Document contains all the terms in `parts`.
# Terms can be slop=5 words away and still be loosely scored as in order.
# Results in order will score higher.
# Spell correction (fuzz) is applied.
def inexact_phrase(field, parts, boost_in_order_nofuzz, boost_out_of_order_nofuzz,
  boost_in_order, boost_out_of_order):
  # Match each term without spelling correction (fuzz).
  nofuzzy_clauses = [
    {
      "span_multi": {
        "match": {
          "fuzzy": {
            field: {
              "value": part,
              "fuzziness": 0
            }
          }
        }
      }
    } for part in parts]
  # Match each term with spelling correction (fuzz).
  fuzzy_clauses = [
    {
      "span_multi": {
        "match": {
          "fuzzy": {
            field: {
              "value": part,
              "fuzziness": "AUTO"
            }
          }
        }
      }
    } for part in parts]
  return es_or(
    [
      # Match the terms _in order_ with slop=5s. No fuzz.
      # Slop can help fix author first/last name order.
      {
        "span_near": {
            "clauses": nofuzzy_clauses,
            "slop": 5,
            "in_order": True,
            "boost": boost_in_order_nofuzz
        }
      },
      # Match the terms in _any order_ (but still close to each other) with slop=5.
      {
        "span_near": {
            "clauses": nofuzzy_clauses,
            "slop": 5,
            "in_order": False,
            "boost": boost_out_of_order_nofuzz
        }
      },
      # Same as above two, but with fuzziness.
      # Fuzzy matches need to be heavily penalized (boosted less)
      # otherwise fuzzy matches that are infrequent words will score
      # higher than exact matches.
      {
        "span_near": {
            "clauses": fuzzy_clauses,
            "slop": 5,
            "in_order": True,
            "boost": boost_in_order
        }
      },
      {
        "span_near": {
            "clauses": fuzzy_clauses,
            "slop": 5,
            "in_order": False,
            "boost": boost_out_of_order
        }
      },
    ])

# Field contains all the words in `s`.
# Up to `percentage_match` words maybe missing.
# The order of words is completely irrelevant.
# Spell checking (fuzz) maybe on or off. Bad spelling does not
# affect scoring.
# Documents with more occurrences of the term(s) will score higher, with no
# regard to matching the order of the query- which is not desireable.
def contains_words(field, s, percentage_match=100, fuzzy=False):
  fuzziness = 'AUTO' if fuzzy else 0
  return {
    "match": {
      field: {
        "query": s,
        "operator": "or",
        "minimum_should_match": f"{percentage_match}%",
        "fuzziness": fuzziness,
      }
    }
  }

# Field contains the _exact string_ `s`.
# Search query is not analyzed, punctuation is not removed etc.
def exact_string(field, s):
  return {"term": {field: s}}

# Field contains any of the _exact strings_ `s`.
# Search query is not analyzed, punctuation is not removed etc.
def any_exact_string(field, l):
  return {"terms": {field: l}}

def es_and(clauses, filters=None):
  result = {"bool":{"must": clauses}} # must means 'and'
  if filters:
    result["bool"]["filter"] = filters
  return result

def es_or(clauses):
  return {"bool":{"should": clauses}} # should means 'or'

# Document contains all the terms in any order, with fuzziness.

# {
#   "match": {
#     "full_title": {
#       "query": query.search,
#       "operator": "and",
#       "fuzziness": "AUTO",
#       "boost": 10
#     }
#   }
# },
