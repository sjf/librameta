#!/usr/bin/env python
from mbutils import *
import sys
from pathlib import Path
from collections import defaultdict
from statistics import *

def process(f):
  ls = read_lines(f)
  d = parse(ls)
  return d

def parse(ls):
  result = defaultdict(list)
  for l in ls:
    date,position = l.split(',')
    result[date].append(int(position))
  return result

def aggreg(d):
  result = {}
  for k,ps in d.items():
    result[k] = mean(ps)
  return result

def out(result):
  for k,n in result.items():
    print(f"{k},{n}")

if __name__ == '__main__':
  file = sys.argv[1]
  d = process(file)
  d = aggreg(d)
  out(d)
