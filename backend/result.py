import re
import json
import os
from flask import request

from mbutils import config, replace_url_param
from book import Book

COVER_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"

class Result():
  def __init__(self, query, hits):
    # The page nums are strings bc None type is rendered by jinja as 'None'
    self.next_page = ''
    self.prev_page = ''
    self.at_max = False
    self_url = request.url
    if query.was_expanded:
      self_url = replace_url_param(self_url, 'x', 1)
    if hits:
      # Only show prev/next buttons if there are results.
      # Page num is provided by the user so it can be any number.
      self.at_max = query.page_num >= config['MAX_PAGE_NUM']
      if len(hits) > config['PAGE_SIZE'] and not self.at_max:
        # There are more results, remove the extra one.
        hits = hits[:config['PAGE_SIZE']]
        self.next_page = replace_url_param(self_url, 'page', query.page_num + 1)
      # Only show the back link if there are results.
      if query.page_num > 0:
        self.prev_page = replace_url_param(self_url, 'page', query.page_num - 1)

    self.books = [Book(h) for h in hits]
    self.was_expanded = query.was_expanded

  def __repr__(self):
    return f"<Result: num_results:{len(self.books)}, next_page:{self.next_page}, \
 prev_page:{self.prev_page}, at_max:{self.at_max} was_expanded:{self.was_expanded}>"
