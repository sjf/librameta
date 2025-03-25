#!/usr/bin/env python3
import sys
import os
import pprint
from es_admin import *
from mbutils import *

config = load_config()
esa = ElasticSearchAdmin()
es = esa.es # To use the ES api directly.

alias = config['ES_ALIAS']
index1 = config['INDEX1']
index2 = config['INDEX2']
if len(sys.argv) == 1:
  arg = 'list'
else:
  arg = sys.argv[1]

stats = {}
for s in es.cat.indices(format="json"):
  index = s['index']
  if index[0] == '.':
    # internal
    continue
  vals = {}
  for k,v in s.items():
    if k in ['uuid','index', 'pri', 'rep']:
      # not interesting
      continue
    if k in ['docs.count', 'docs.deleted']:
      # big numbers
      v = f"{int(v):,}"
    vals[k] = v
  stats[index] = vals

def print_aliases():
  indexes = esa.get_alias_indexes(alias)
  indexes = sorted(indexes)
  print(f"Indexes in alias '{alias}': [{joinl(indexes,', ',empty='')}]")
  print()

def count(index):
  if not index in stats:
    print(f"Index '{index}' does not exist.")
    sys.exit(1)
  return stats[index]['docs.count']

if arg == 'list':
  print_aliases()
  aliases = es.indices.get_alias(body="*")
  for name,s in sorted(stats.items()):
    print(f"{name} ({count(name)} docs)")
    als = sorted(aliases[name]['aliases'].keys())
    print(f"  aliases: {joinl(als, ', ', empty='None')}")
    for k,v in sorted(s.items()):
      if k in ['docs.count']:
        continue
      print(f"  {k}: {v}")

elif arg == 'swap':
  print_aliases()
  indexes = esa.get_alias_indexes(alias)
  current = []
  if index1 in indexes:
    current.append(index1)
  if index2 in indexes:
    current.append(index2)
  if len(current) == 2:
    print(f'Too many indexes in alias: {current}')
    sys.exit(1)
  if len(current) == 0:
    print(f'Alias has no indexes.')
    sys.exit(1)
  current = current[0]
  new = None
  if index1 == current:
    new = index2
  if index2 == current:
    new = index1
  c1 = count(index1)
  c2 = count(index2)
  print(f"{index1}: {c1}")
  print(f"{index2}: {c2}")
  print(f"New index: {new}")
  input(f"Swapping {alias} to {new}, enter to continue\n")
  resp = esa.swap_alias_indexes(alias, current, new)
  print(f"Response: {resp}")
  print()
  print_aliases()

elif arg == 'clear':
  index = sys.argv[2]
  c = count(index)
  input(f"Removing {c} docs from '{index}', enter to continue\n")
  resp = es.delete_by_query(index=index, body={"query": {"match_all": {}}})
  print(f"Response: {resp}")

elif arg == 'rm':
  index = sys.argv[2]
  c = count(index)
  input(f"Removing {index} ({c} docs) from '{alias}', enter to continue\n")
  actions = {
    'actions': [
      {'remove': {'alias': alias, 'index': index}},
    ]
  }
  log(f"update_aliases: {actions}")
  resp = es.indices.update_aliases(body=actions)
  print(f"Response: {resp}")

elif arg == 'add':
  index = sys.argv[2]
  c = count(index)
  input(f"Adding {index} ({c} docs) to '{alias}', enter to continue\n")
  actions = {
    'actions': [
      {'add': {'alias': alias, 'index': index}}
    ]
  }
  log(f"update_aliases: {actions}")
  resp = es.indices.update_aliases(body=actions)
  print(f"Response: {resp}")

elif arg == 'delete':
  index = sys.argv[2]
  c = count(index)
  input(f"Deleting {index} ({c} docs), enter to continue\n")
  resp = es.indices.delete(index=index)
  print(f"Response: {resp}")

elif arg == "mapping":
  index = sys.argv[2]
  pprint.pprint(es.indices.get_mapping(index=index)[index]['mappings'])

else:
  print(f"Unknown {arg}, try: list, swap, add, rm, clear, delete")












