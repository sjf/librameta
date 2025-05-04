import json
import os
import langcodes
import logging
from flask import has_request_context, request
from datetime import datetime
from collections import defaultdict
from mbutils import iso_timestamp, joinl

def client_ip():
  if has_request_context():
    return request.headers.get('X-Real-IP', request.remote_addr)
  else:
    return '-'

def log(mesg):
  """ Logs an info message to the gunicorn access log."""
  log_mesg = f"{client_ip()} - - [{iso_timestamp()}] \"{mesg}\"" # these quotes dont work great json.

  logger = logging.getLogger("gunicorn.access")
  logger.info(log_mesg)

def log_json(tag, obj):
  """ Logs a json info message to the gunicorn access log."""
  log(f"LOG_JSON {tag} {json.dumps(obj)}")

def log_error(mesg, level=logging.ERROR, exc_info = None):
  """ Logs to the gunicorn error log with an optional stack trace."""
  log_mesg = f'{client_ip()} {mesg}'
  logger = logging.getLogger("gunicorn.error")
  logger.log(level, log_mesg, exc_info = exc_info)

def nonzero(s):
  """ Returns true if `s` is a non-zero number or a string that is not '0'."""
  return s and s != '0'

def maybe_param(key):
  """ Return param `key` or None is missing or empty. """
  if present(key):
    return request.values.get(key)
  return None

def params_dict(allowed_keys):
  result = defaultdict(str)
  for key in allowed_keys:
    if present(key):
      result[key] = request.values.get(key)
  return result



