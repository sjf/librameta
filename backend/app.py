import sys
import logging
import os
import json
from flask import Flask, render_template, request, flash, session, redirect
import elasticsearch
from es import ElasticSearch
from http import HTTPStatus

from util import *
import mbutils
from mbutils import read, split, joinl, dictl
from mbutils.config import config
from routes import bp

def configure_flask_app():
  if app.debug or os.getenv('FLASK_ENV') == 'development':
    app.config['TESTING'] = True
    app.config['DEBUG'] = True
    app.config['SECRET_KEY'] ='dev'
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    os.environ['DEBUG'] = 'True'
    @app.after_request
    def add_referrer_policy_header(response):
      # This header is added by nginx in prod.
      response.headers['Referrer-Policy'] = 'same-origin'
      return response
  else:
    app.config['SECRET_KEY'] = read(config['SECRET_KEY_FILE'])
  return app

def is_using_gunicorn():
  return "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")

def setup_logging():
  gunicorn_error_logger = logging.getLogger("gunicorn.error")
  gunicorn_access_logger = logging.getLogger("gunicorn.access")

  if not is_using_gunicorn():
    # Set up gunicorn logs if not being run by gunicorn.
    # Log access and errors to the console.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(mbutils.formatter)
    gunicorn_error_logger.setLevel(logging.DEBUG)
    gunicorn_error_logger.addHandler(console_handler)

    gunicorn_access_logger.setLevel(logging.DEBUG)
    gunicorn_access_logger.addHandler(logging.StreamHandler())
  # Filter health access logs.
  logging.getLogger("werkzeug").addFilter(LogFilter())
  gunicorn_access_logger.addFilter(LogFilter())

  # Log all the flask messages to the gunicorn error file.
  # flask does not really produce access-type log messages.
  # logging performed by the app uses the gunicon access and error loggers.
  app.logger.handlers = gunicorn_error_logger.handlers
  app.logger.setLevel(gunicorn_error_logger.level)

class LogFilter(logging.Filter):
  def filter(self, record):
    # dont log requests to health endpoint because it makes too much noise.
    return record.getMessage().find('"GET /health HTTP') == -1

def log_startup():
  def rule_to_str(rule):
    return f"Rule: {rule}, Endpoint: {rule.endpoint}, Methods: {rule.methods}"
  rules = sorted(app.url_map.iter_rules(), key=lambda r:r.rule)
  endpoints = joinl(rules, to_str=rule_to_str)
  log_error(f"Config:\n{dictl(config)}", logging.INFO)
  log_error(f"Endpoints:\n{endpoints}", logging.INFO)

if __name__ != "__main__":
  # When run by gunicorn or flask:
  app = Flask(__name__)
  app.register_blueprint(bp)
  configure_flask_app()
  setup_logging()
  log_startup()

  # @app.before_request
  # def require_auth():
  #   print(request.path)
  #   if request.path == '/login' or request.path.startswith('/static/'):
  #     # No auth needed
  #     return
  #   if not session.get('authenticated'):
  #     return redirect('/login')

  # @app.errorhandler(404)
  # def not_found(unused):
  #   return redirect('/login')
