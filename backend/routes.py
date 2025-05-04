import sys
import logging
import os
import json
from flask import Flask, render_template, request, flash, redirect, session
from markupsafe import escape
from flask import Blueprint, current_app
import elasticsearch
from es import ElasticSearch
from http import HTTPStatus
import urllib.parse as ul

from mbutils import *
from util import *
from query import Query

bp = Blueprint('main', __name__)
es = ElasticSearch()

@bp.route('/')
@bp.route('/index.html')
def index():
  query = Query(request.path, request.args, request.accept_languages)
  if query.has_search_query:
    # Redirect old links using just /?... to /search.
    return redirect(f'/search?{request.query_string.decode("utf-8")}', code=301)
  return render_template('index.html', query=Query(request.path), page='index')

@bp.route('/adv')
def adv():
  return render_template('index.html', query=Query(request.path), page='index')

@bp.route('/search')
@bp.route('/search-adv') # The different path is only used to render the search box, both endpoints handle all params.
def search():
  query = Query(request.path, request.args, request.accept_languages)
  result, code = None, 200
  if query.has_search_query:
    result = _search(query)
    if not result:
      code = 500 # The search failed.
  if result:
    return handle_result(query, result)
  # There was no search query, or the query failed, just render the same as index page.
  return render_template('index.html', query=query, page='index'), code

def _search(query):
  try:
    return es.search(query)
  except Exception as e:
    flash("Something went wrong")
    info = ''
    if isinstance(e, elasticsearch.BadRequestError):
      info = e.info
    log_error(f"Error handling search request: {info}", exc_info = e)
    if current_app.debug:
      raise e
    # In production swallow the exception and let the parent handle the error.
    return None

def handle_result(query, result):
  log_json('RESULTS', {
    'params': request.query_string.decode('utf-8'),
    'count': len(result.books),
    'expanded': query.was_expanded,
    'ids': list(map(lambda x:x.md5, result.books))
    })
  return render_template('results.html', result=result, query=query, page='results')

LOG_KEYS = {'DOWNLOAD': ['urlpath', 'query', 'position', 'id', 'title', 'authors', 'button']}
@bp.route('/log', methods=['POST'])
def log_handler():
  data = request.data.decode('utf-8')
  try:
    decoded = json.loads(data)
    if not contains_keys(decoded, ['name','data']):
      raise Exception(f"Invalid keys: {decoded.keys()}")
    name = decoded['name'].upper()
    if name not in LOG_KEYS:
      raise Exception(f"Invalid name: {name}")
    data = decoded['data']
    data = filterd(lambda k,v:k in LOG_KEYS[name], data)
    if not data:
      raise Exception(f"No validated keys in {decoded}")
    log_json(name, data)
  except Exception as e:
    log_error(f"Can't decode JSON: {e}")
    decoded = data
  return ''

@bp.route('/login', methods=['GET', 'POST'])
def login():
  mesg = ""
  if request.method == 'POST':
    if request.form.get('password') == config['PASSWORD']:
      session['authenticated'] = True
      return redirect('/')
    else:
      mesg = "<pre>Login failed</pre>"
  return f"""
    <form method="post">
      <input type="password" name="password">
      <input type="submit" value="Login">
    </form>
    {mesg}
  """
@bp.route('/logout')
def logout():
  session.pop('authenticated', None)
  return redirect('/login')

@bp.route('/thankyou', methods=['POST'])
def thankyou():
  email = escape(request.form.get('email', ''))
  message = escape(request.form.get('message', ''))
  with open(config['FEEDBACK_DEST'], 'a') as f:
    f.write(f'<p><strong>{iso_timestamp()}</strong></p>\n')
    if email:
      f.write(f'<p>Email: {email}</p>\n')
    f.write(f'<p><pre>{message}</pre></p><hr>\n')

  return render_template('/thankyou.html')

@bp.route('/about')
def about():
  return render_template('about.html')

@bp.route('/feedback')
def feedback():
  return render_template('feedback.html')

@bp.route('/health')
def health():
  return 'OK'

@bp.after_app_request
def add_header(response):
  response.headers['X-LMLMLM'] = f'{maybe_read("build_time.txt", "n/a")} {maybe_read("git.txt", "n/a") }'
  return response
