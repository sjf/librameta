import os
import sys
import elasticsearch, elastic_transport
from elasticsearch import Elasticsearch, helpers
from mbutils import *

__all__ = ['ElasticSearchAdmin']

RETRIES = 3
RETRY_DELAY_SECS = 10 # Wait this amount of time before retrying an Elasticsearch insert.

class ElasticSearchAdmin:
  def __init__(self):
    api_key = read_value(os.getenv('ELASTIC_ADMIN_API_KEY_FILE'))
    log(f"Connecting to Elasticsearch host '{os.getenv('ELASTIC_HOST')}'")
    self.es = Elasticsearch(os.getenv('ELASTIC_HOST'), api_key = api_key)

  def upsert(self, docs):
    retries = RETRIES + 1
    success = 0
    failed = []

    while retries > 0:
      try:
        success, errors = helpers.bulk(self.es, docs)
        if errors:
          log_es_errors(errors, failed)
        break # Don't retry
      except elasticsearch.AuthenticationException as e:
        raise e
      except (elasticsearch.helpers.BulkIndexError, elastic_transport.ConnectionTimeout) as ex:
        log_error(f"Indexing failed with exception:{ex}")
        if isinstance(ex, elasticsearch.helpers.BulkIndexError):
          log_es_errors(ex.errors, failed)
        retries -= 1
        if retries > 0:
          log(f'Retrying... (attempt {RETRIES + 2 - retries}) after {RETRY_DELAY_SECS} seconds', )
          time.sleep(RETRY_DELAY_SECS)

    if retries == 0:
      raise Exception(f" ** Elastic search bulk upsert failed after {RETRIES} retries.")
    return success, failed

  def get(self, id_):
    try:
      return self.es.get(index=os.environ['CURRENT_INDEX'], id=id_)
    except elasticsearch.NotFoundError:
      return None

  def getm(self, ids):
    return self.es.mget(index=os.environ['CURRENT_INDEX'], body={'ids':ids})['docs']

  def get_alias_indexes(self, alias):
    try:
      alias_info = self.es.indices.get_alias(name=alias)
      return list(alias_info.keys())
    except elasticsearch.NotFoundError as e:
      print(e)
      return []

  def swap_alias_indexes(self, alias, current_index, new_index):
    actions = {
      'actions': [
        {'remove': {'alias': alias, 'index': current_index}},
        {'add': {'alias': alias, 'index': new_index}}
      ]
    }
    log(f"ES update_aliases: {actions}")
    return self.es.indices.update_aliases(body=actions)

  def delete_index(self, name):
    return self.es.indices.delete(index=name)

  def refresh_index(self, index):
    log(f"Refreshing index {index}")
    return self.es.indices.refresh(index=index)

def log_es_errors(errors, failed):
  log_error(f"** ES error: {len(errors)} docs failed to upsert.")
  failed.extend(errors)
  max_ = 5
  for err in errors[:max_]:
    e = err['index']
    log_error(f"Upsert failed: status:{e['status']} reason:{repr(e['error']['reason'])} data:{e['data']}")
  if len(errors) > max_:
    log_error(".... Skipping rest of the errors, See the failed.txt file for the full list of errors.")
