#!/usr/bin/env python3
import sys
import json
from datetime import datetime
from mbutils import *

search_params = ('search','author','title','isbn','doi','series','lang','ext','page','year','end_year','start_year','sort','order')

def search_queries(lines):
  """ Outputs the search queries, aggregated by the search field. """
  queries = []
  for l in lines:
    params = flatten_params(url_params(l, query_only=True, keep_blank_values=False))
    params = filterd(lambda k,v:k in search_params, params)
    if not params:
      continue
    queries.append(dictl(params, sep=', ', item_sep=':'))
  print(joinl(sorted(queries)))

def aggregate_search_queries(lines):
  """ Outputs the search queries, aggregated by the search field. """
  counts = defaultdict(lambda: defaultdict(lambda:[]))
  for l in lines:
    params = url_params(l, query_only=True)
    # print(l,params)
    for key,values in params.items():
      if key in search_params:
        for val in values:
          counts[key][canonnn(val)].append(val)
      # ignore unknown keys, these are bot scans.
      # else:
      #   stderr(f'unknown param {key} = {vs}, \'{l}\'')
  print_counts(counts)

def aggregate_search_results(lines):
  counts = defaultdict(lambda: defaultdict(lambda:[]))
  for l in lines:
    d = parse(l)
    if 'query' in d:
      # old log style
      num_results = f"{d['count']} results"
      for m in d['query']['bool']['must']:
        if 'multi_match' in m:
          key = 'search'
          v = m['multi_match']['query']
        if 'match_phrase' in m:
          for k_,v in m['match_phrase'].items():
            key = k_.lower()
        counts[key][canonnn(v)].append(num_results)
      for f in d['query']['bool']['filter']:
        if 'term' in f:
          v = f['term']['lang']
          counts['lang'][canonnn(v)].append(num_results)
        if 'terms' in f:
          if 'Extension' in f['terms']:
            for v in f['terms']['Extension']:
              counts['ext'][canonnn(v)].append(num_results)
          else:
            for v in f['terms']['ext']:
              counts['ext'][canonnn(v)].append(num_results)
    else:
      num_results = f"{d['count']} results"
      params = url_params(d['params'], query_only=True, keep_blank_values=False)
      for key,values in params.items():
        if key in search_params:
          for val in values:
            counts[key][canonnn(val)].append(num_results)
        # else:
        #   print(f'unknown param {key} = {vs}, \'{l}\'')
        #   pass # These are usually just bot scans.
  print_counts(counts)

def aggregate_searches_with_no_results(lines):
  no_results = defaultdict(int)
  total = 0
  out_of = 0
  for l in lines:
    out_of += 1
    d = parse(l)
    if d['count'] > 0:
      continue
    if not 'params' in d:
      # Not bothering with older log entries that dont have the url.
      continue
    query = url_params(d['params'], query_only=True, keep_blank_values=False)
    params = []
    for k,vals in sorted(query.items(), reverse=True):
      for v in sorted(vals):
        params.append(f"{k}: '{canonnn(v)}'")
    key = joinl(params, ', ')
    # print(key)
    no_results[key] += 1
    total += 1
  if out_of == 0:
    pc = 0
  else:
    pc = int(100*(total/out_of))
  print(f"{total}/{out_of} searches, {pc}%")

  result = sort_by_vals(no_results)
  print(joinl(result, to_str=lambda x:f"{x[1]}: {x[0]}"))

def aggregate_downloads(lines):
  counts = defaultdict(lambda: defaultdict(lambda:[]))
  count = 0
  by_id_count = Counter()
  by_id_title = {}
  by_id_searches = defaultdict(list)
  by_title_count = defaultdict(int)
  position_counts = defaultdict(int)
  for l in lines:
    json_ = ast.literal_eval(l)
    if contains_keys(json_, ['name','data']): # old format
      data = json_['data']
    else:
      data = json_

    if not contains_keys(data, ['authors','title','id']):
      # print(f"Skipping bad json {l}")
      continue
    count += 1
    id_ = data['id']
    title = data['title']
    position = int(data['position']) if 'position' in data else -1
    search = {}
    if 'urlpath' in data:
      search = flatten_params(url_params(data['urlpath'], keep_blank_values=False))
    elif 'query' in data: # old format
      search = filterd(lambda k,v:v, data['query']) # remove empty params.
    if 'page' in search:
      position += int(search['page']) * config['PAGE_SIZE']
    # print(repr(data['authors']))
    # authors has lots of whitespace bc it is from the html content text.
    authors = canonnn(data['authors'],lower=False, rm_punctuation=False)
    by_id_count[id_] += 1
    by_id_searches[id_].append(frozenset(search.items()))
    by_id_title[id_] = f"'{title} by {authors}'"
    by_title_count[title] +=1
    position_counts[position] += 1
  print(f"Total downloads: {count:,}")
  print("Downloads by title")
  for title,count in sort_by_vals(by_title_count):
    print(f"{count}: {title}")
  print("---------------------------------------------------------------------------")
  print("Downloads by position")
  for position,count in sort_by_vals(position_counts):
    print(f"{count}: {position}")
  print("---------------------------------------------------------------------------")
  print("Downloads by book MD5 (there can be many copies of the same title with different MD5s)")
  for k,count in sort_by_vals(by_id_count):
    # count = by_id_count[k]
    searches = count_occurrences(by_id_searches[k])
    print(f"{count}: {dictl(searches, sep=', ', to_str_key=lambda k:dict(k))} {by_id_title[k]}")

def flatten_params(d):
  result = {}
  for k,v in d.items():
    if len(v) == 1:
      result[k] = v[0]
    else:
      result[k] = joinl(sorted(v),',')
  return result

def print_counts(counts):
  for param in search_params:
    print(f"{param}\t{len(counts[param]):,}")
  for param in search_params:
    for query_value,raw_query_values in sort_by_vals(counts[param], key=lambda x:(len(x[1]),x[0])):
      count = len(raw_query_values)
      values = count_occurrences(raw_query_values)
      print(f"{param}:{count} '{query_value}' [{dictl(values, sep=', ', empty='')}]")

def parse(s):
  try:
    return json.loads(s)
  except:
    pass
  try:
    return ast.literal_eval(s)
  except e:
    stderr(f"Couldn't parse: '{s}'")
    raise e

def count_occurrences(vals):
  result = defaultdict(int)
  for v in vals:
    result[v] += 1
  return result

def sort_by_vals(d, key=lambda x:(x[1],x[0])):
  # Default sort is by (value,key)
  return sorted(d.items(), key=key, reverse=True)

commands = {
  'all_searches': search_queries,
  'searches': aggregate_search_queries,
  'results': aggregate_search_results,
  'zero_results': aggregate_searches_with_no_results,
  'downloads': aggregate_downloads,
  }

def usage_fail():
  print("Usage: logs.py [search|downloads|results] [input-file]")
  sys.exit(1)

if __name__ == '__main__':
  if len(sys.argv) < 3:
    usage_fail()
  command = sys.argv[1]
  if command not in commands:
    usage_fail()
  file = sys.argv[2]
  lines = read_lines(file, to_list=False)

  print(f"Generated at {datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')}")
  commands[command](lines)


