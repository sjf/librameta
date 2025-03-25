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
from collections import Counter, defaultdict
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from ._defaults import _DEFAULTS
from .log import *

DATE_FORMAT = "%d/%b/%Y:%H:%M:%S %z"

def iso_timestamp():
  return datetime.datetime.now().astimezone().strftime(DATE_FORMAT)

def duration(start, end):
  return humanfriendly.format_timespan(end - start)

list_handler = None
logger = logging.getLogger('mbutils')
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s',  datefmt=DATE_FORMAT)
is_initialized = False

def _setup_logging():
  logger.setLevel(logging.DEBUG)

  # console handler
  console_handler = logging.StreamHandler()

  if 'MB_LOG_DIR' in os.environ:
    log_dir = os.environ.get('MB_LOG_DIR')
  else:
    log_dir = f'logs/'
  # file handler
  file_handler = logging.FileHandler(f'{log_dir}/mb.log')

  setup_and_install_handler(console_handler)
  setup_and_install_handler(file_handler)

  #Change the console level to debug, default is INFO
  console_handler.setLevel(logging.DEBUG)
  is_initialized = True

def setup_and_install_handler(handler):
  handler.setFormatter(formatter)
  handler.setLevel(logging.INFO)
  logger.addHandler(handler)

def setup_list_handler():
  """Set up the handler that stores log messages in memory so they can be
  retrieved with `get_logged_messages`."""
  global list_handler
  list_handler = ListHandler()
  setup_and_install_handler(list_handler)

def get_logged_messages():
  if not list_handler:
    raise Exception("List handler was not installed.")
  return list_handler.messages

class ListHandler(logging.Handler):
  """ A logging handler that stores log messages in memory. """
  def __init__(self):
    super().__init__()
    self.messages = []
  def emit(self, record):
    self.messages.append(self.format(record))

def log(message, ex=None):
  if ex:
    logger.info(format_ex(ex))
  logger.info(message)

def log_error(message, ex=None):
  if ex:
    logger.error(format_ex(ex))
  logger.error(message)

def debug(message, ex=None):
  if ex:
    logger.debug(format_ex(ex))
  logger.debug(message)

def catch_and_log_exceptions(func):
  def wrapper(*args, **kwargs):
    """ Returns True if func failed. Otherwise return the result of the function (which should be True if failed.)"""
    try:
      res = func(*args, **kwargs)
      if res in (True, False):
        return res
      return False # did not fail.
    except Exception as ex:
      log("catch_and_log_exceptions", ex)
      return True # failed.
  return wrapper

def format_ex(ex):
  exc_type, exc_value, exc_traceback = sys.exc_info()
  return ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))

def print_res(func):
  def wrapper(*args, **kwargs):
    res = func(*args, **kwargs)
    print(res)
    return res
  return wrapper

if not is_initialized:
  _setup_logging()

