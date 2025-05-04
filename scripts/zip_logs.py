#!/usr/bin/env python
from mbutils import *
import sys
from pathlib import Path

def process(f):
  ls = read_lines(f)
  d = parse(ls)
  return d

def parse(ls):
  result = {}
  for l in ls:
    date,count = l.split(',')
    result[date] = count
  return result

def zip(ds):
  result = {}
  keys = set()
  for d in ds:
    keys |= d.keys()
  for k in keys:
    value = []
    for d in ds:
      v = d[k] if k in d else 0
      value.append(v)
    result[k] = value
  return result

def out(headers,d):
  print(joinl(['date'] + headers,','))
  for k,v in d.items():
    print(f"{k},{joinl(v,',')}")

def header(f):
  filename_without_ext = Path(f).stem
  return filename_without_ext

if __name__ == '__main__':
  files = sys.argv[1:]
  ds = list(map(process, files))
  r = zip(ds)
  headers = list(map(header,files))
  out(headers, r)
