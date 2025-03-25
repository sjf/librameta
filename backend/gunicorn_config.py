# This is inside the docker container, so it is ok to bind on 0.0.0.0.
bind = '0.0.0.0:8000'
accesslog = '/var/log/gunicorn/gunicorn-access.log'
errorlog  = '/var/log/gunicorn/gunicorn-error.log'
pidfile = '/var/run/gunicorn.pid'
# Client IP address is always the IP of the nginx proxy, change to use the forwarded IP real-ip header.
# %L is response time.
access_log_format = '%({x-real-ip}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s %(L)s"'
loglevel = 'info'
# By preloading an application you can save some RAM resources as well as speed up server boot times.
# Although, if you defer application loading to each worker process, you can reload your application code easily by restarting workers.
preload = True

import logging
import mbutils

def on_starting(server):
  # Log errors to console as well as error log file.
  gunicorn_error_logger = logging.getLogger("gunicorn.error")
  console_handler = logging.StreamHandler()
  console_handler.setFormatter(mbutils.formatter)
  gunicorn_error_logger.addHandler(console_handler)

  gunicorn_error_logger.info(f'Starting Gunicorn...')

def when_ready(server):
  logging.getLogger("gunicorn.error").info(f'Gunicorn ready, listening on {",".join(server.cfg.bind)}...')
def on_reload(server):
  logging.getLogger("gunicorn.error").info(f'Reloading Gunicorn...')
def on_exit(server):
  logging.getLogger("gunicorn.error").info(f'Gunicorn shutting down...')
