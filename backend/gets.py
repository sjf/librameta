#!/usr/bin/env python3
import requests
import sys
import time
from bs4 import BeautifulSoup
from es import ElasticSearch
from collections import defaultdict
from mbutils import *
"""
Script to check that direct download urls are generated correctly.
"""

TIMEOUT = config['PYTEST_TIMEOUT']

GET_ERROR = 'Could-not-get-remote-dl-page'
DL_ERROR = 'Could-not-get-remote-file'

def get(md5):
  try:
    url = f"https://example.com/{index}/{md5}"
    response = requests.get(url, timeout=TIMEOUT)
    soup = BeautifulSoup(response.text, 'html.parser')
    a = soup.find('a', string='GET')
    if response.status_code != 200:
      debug(f"{url} {response}")
      for k,v in response.headers.items():
        log(f"{k}: {v}")
      return GET_ERROR + ' HTTP error' + str(response)
    # print(url)
    # print(response.text)
    link = url_decode(a['href'])
    return link
  except Exception as e:
    log("",e)
    return GET_ERROR + ' ' + str(e)
  # response = requests.head(link)
  # print(response)

def check_link_dl(book):
  try:
    response = requests.head(book.main_link, timeout=TIMEOUT, allow_redirects=False)
    is_ok = False
    if 'Content-Disposition' in response.headers:
      content_disposition = response.headers['Content-Disposition']
      content_disposition = re.sub(r'[\x00-\x1F\x7F]', '_', content_disposition) # remove control chars

      safe_title = re.sub(r'[<>:"/\\|?*;]', '_', book.title)
      if safe_title in content_disposition:
        is_ok = True
      if re.search(f'filename=.*\\.{book.extension}"$', content_disposition):
        is_ok = True
    if not is_ok:
      log(f"{url} {response}")
      for k,v in response.headers.items():
        log(f"{k}: {v}")
    else:
      log(f"Content-Disposition: {response.headers['Content-Disposition']}")
    return is_ok
  except Exception as e:
    log("",e)
    return DL_ERROR

es = ElasticSearch()
lines = read_csv(sys.argv[1])
index = True if sys.argv[2] == 'main' else 'fiction'
skip = int(sys.argv[3]) if len(sys.argv) > 3 else 0
counts = defaultdict(int)
diffs = []
count = 0
i = 0

for i in range(len(lines)):
  if i <= skip:
    continue

  line = lines[i]

  count += 1
  if count % 20 == 0:
    log(dictl(counts, sep=', '))
  debug(f"{i}: {line}")

  md5 = line[0]
  book = es.search_by_md5(md5, main_index=(index == 'main'))
  if not book:
    log(f" ** Could not find {line}")
    counts['not_found'] += 1
    continue

  if book.main_link.startswith('https://example.com/'):
    counts['no_direct_link'] += 1
    continue

  actual_link = get(md5)
  if actual_link.startswith(GET_ERROR):
    # just skip
    time.sleep(3)
    continue

  if book.main_link == actual_link:
    counts['links_the_same'] += 1
  else:
    is_ok = check_link_dl(book)
    if is_ok == True:
      counts['not_the_same_but_link_works'] += 1
    elif is_ok == DL_ERROR:
      pass # do nothing, assuming transitory error like timeout.
    else:
      counts['not_same_and_broken'] += 1
    # entry = [actual_link, book.link, dl_diff]
    log(f"Line: {i} Link still works: {is_ok}")
    log(f"Actual:  {actual_link}")
    log(f"Created: {book.main_link}")
    if not is_ok:
      log(f"Actual (clickable): {url_encode(actual_link)}")
      log(f"Created(clickable): {url_encode(book.main_link)}")
    log(f"Book: {book._source}")
    log("--------------------------")

    # sys.exit(1)
  time.sleep(0.2)

log(dictl(counts))
