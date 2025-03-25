_DEFAULTS = {
  # Nginx
  'HT_USERNAME': 'mb',
  'HT_PASSWORD_FILE': 'secrets/mb-password.txt',
  'FILES_HT_USERNAME': 'mb',
  'FILES_HT_PASSWORD_FILE': 'secrets/files-password.txt',

  # Backend
  'SECRET_KEY_FILE': 'secrets/flask-secret-key.txt',
  'COVER_URL': 'https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg',

  # Elasticsearch
  'ELASTIC_HOST': 'http://127.0.0.1:9200',
  'ELASTIC_ADMIN_API_KEY_FILE': 'secrets/elastic-admin-api-key.txt',
  'ELASTIC_API_KEY_FILE': 'secrets/elastic-api-key.txt', # API key for read-only role.
  'ES_ALIAS': 'libmeta_alias',
  'INDEX1': 'libmeta1',
  'INDEX2': 'libmeta2',
  'PAGE_SIZE': 20,
  'MAX_PAGE_NUM': 50,

  # Pytests
  'SENDGRID_API_KEY_FILE': 'secrets/sendgrid-api-key.txt',
  'SENDGRID_FROM_FILE': 'secrets/sendgrid-from.txt',
  'SENDGRID_TO_FILE': 'secrets/sendgrid-to.txt',
  'VERIFY_SSL': True,
  'TEST_DOWNLOAD': True,
  'PYTEST_TIMEOUT': 2,
  'PYTEST_MAIL': False,

  # Import
  'IMPORT_MAIL': False,
  'DUMP_DIR': 'dumps',
  'IMPORT_CLEAN' : True,

  # MySQL
  'DBS': 'libmeta_compact fiction',
  'DB_HOST': '127.0.0.1',
  'MYSQL_DB': 'libmeta',
  'DB_ROOT_PASSWORD_FILE': 'secrets/db-password.txt',
  'DB_USER': 'mysql',
  'DB_PASSWORD_FILE': 'secrets/db-user-password.txt',

  'FEEDBACK_DEST': '/var/log/feedback.html'
}
