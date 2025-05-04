import os
import subprocess
import sys
import time, datetime
import humanfriendly
import logging
import configparser
import traceback
import re
import ast
import csv
import urllib.parse
import pprint
from collections.abc import Iterable
from collections import Counter, defaultdict
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from ._defaults import _DEFAULTS
from .log import *
from .shell import read, stderr

def uniq(l):
  """ Remove duplicates while preserving order. """
  return list(dict.fromkeys(l))

def cmp(a,b):
  # ascending
  res = (a > b) - (a < b)
  # descending
  return -res

def split(s, sep=','):
  parts = s.split(sep)
  parts = map(lambda x:x.strip(), parts)
  parts = non_empty(parts)
  return parts

def joinl(l, sep="\n", to_str=str, empty='[]'):
  if not l:
    return empty
  return sep.join(map(to_str,l))

def dictl(d, sort_key=None, sep='\n', empty='{}', to_str_key=lambda x:x, item_sep='='):
  items = sorted(d.items(), key=sort_key)
  return joinl([f"{to_str_key(k)}{item_sep}{repr(v)}" for k,v in items], sep=sep, empty=empty)

def mapl(f,seq):
  return list(map(f,seq))

def printl(o, sort_key=None):
  if isinstance(o, dict):
    s = dictl(o, sort_key=sort_key)
  elif isinstance(o, Iterable):
    s = joinl(o)
  else:
    s = o
  print(s)

def printd(d):
  return pprint.pprint(d)

def filterd(f, d):
  result = {}
  for k,v in d.items():
    if f(k,v):
      result[k] = v
  return result

def trunc(s, max_=60):
  if len(s) > max_:
    return s[:max_-3] + '...'
  return s

def containsl(list1, list2):
  return set(list2).issubset(list1)

def contains_keys(d, keys):
  return containsl(d.keys(), keys)

def non_empty(l):
  return list(filter(lambda x:x, l))

def index_or_default(n, l, default):
  if len(l) <= n:
    return default
  return l[n]

def file_line_reader(file_path):
  """ Generator to read file line by line, returns the line number and stripped line."""
  # DEBUG and log(f"Opening {file_path}")
  with open(file_path) as fh:
    line_num = 0
    while line := fh.readline():
      yield line.rstrip(), line_num
      line_num += 1

def url_params(url, keep_blank_values=True, query_only=False):
  """ Returns the URL params as dict where the value is list all the param values. """
  if query_only:
    query = url
  else:
    query = urllib.parse.splitquery(url)[1] # split query from url
  params = urllib.parse.parse_qs(query, keep_blank_values=keep_blank_values)
  return dict(params)

def url_wo_host(url):
  """ Returns the URL without the hostname and protocol. """
  parsed_url = urllib.parse.urlparse(url)
  new_url = ('', '', parsed_url.path, parsed_url.params, parsed_url.query, parsed_url.fragment)
  return urllib.parse.urlunparse(new_url)

def replace_url_param(url, name, value):
  params = url_params(url)
  params[name] = [value]
  query = urllib.parse.urlencode(params, doseq=True)

  parsed_url = urllib.parse.urlparse(url)
  parsed_url = parsed_url._replace(query=query)
  new_url = urllib.parse.urlunparse(parsed_url)
  return new_url

def url_decode(s):
  return urllib.parse.unquote(s)

def url_encode(s):
  return urllib.parse.quote(s)

def get_db_uri():
  DB_URI = "mysql://{user}:{password}@{host}/{db}"
  db_host = os.environ.get('DB_HOST')
  db = os.environ.get('MYSQL_DB')
  user = os.environ.get('DB_USER')
  password = read(os.environ.get('DB_PASSWORD_FILE'))
  return DB_URI.format(user=user, password=password, db=db, host=db_host)

def url_to_filename(url):
  url = url.replace('://','_')
  # Replace forbidden characters with underscores
  return re.sub(r'[<>:"/\\|?*]', '_', url)

def mail(subject, body):
  to = os.environ.get('TO_ADDRESS')
  from_ = os.environ.get('FROM_ADDRESS')
  message = Mail(
      from_email=from_,
      to_emails=to,
      subject=subject,
      html_content=body)
  log(f"Sending mail '{subject}' to {to} from {from_}")
  sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
  response = sg.send(message)
  if response.status_code != 202:
    log(f"Failed to send mail: response {response.status_code}\n{response.headers}")

def read_csv(f, delimiter=',', quotechar='"'):
  result = []
  with open(f) as fh:
    reader = csv.reader(fh, delimiter=delimiter, quotechar=quotechar)
    for line in reader:
      result.append(line)
  return result

def canon(s):
  return s.strip().lower().strip('"').strip("'")

def canonnn(s, lower=True, rm_whitespace=False, rm_punctuation=True):
  s = s.strip() # remove leading and trailing whitespace
  if lower:
    s = s.lower() # lower case

  if rm_whitespace:
    s = re.sub(r'\s', '', s) # remove all whitespace
  else:
    s = re.sub(r'\s+', ' ', s, flags=re.MULTILINE) # collapse whitespace, including newlines

  if rm_punctuation:
    s = re.sub(r'[^\w\s]', '', s) # remove chars that are not letters, digits or whitespace.
  return s



