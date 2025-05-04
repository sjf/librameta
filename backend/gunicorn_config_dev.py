import logging
import mbutils

def on_starting(server):
  # Log access and errors to the console.
  console_handler = logging.StreamHandler()
  console_handler.setFormatter(mbutils.formatter)
  gunicorn_error_logger = logging.getLogger("gunicorn.error")
  gunicorn_error_logger.addHandler(console_handler)

  logging.getLogger("gunicorn.access").addHandler(logging.StreamHandler())

  gunicorn_error_logger.info(f'Starting Gunicorn...')

def when_ready(server):
  logging.getLogger("gunicorn.error").info(f'Gunicorn ready, listening on {",".join(server.cfg.bind)}...')
def on_reload(server):
  logging.getLogger("gunicorn.error").info('Reloading Gunicorn...')
def on_exit(server):
  logging.getLogger("gunicorn.error").info('Gunicorn shutting down...')
