import os
import pytest
from mbutils import iso_timestamp, mail

failed = []
# # Collect failed tests in the report hook
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
  outcome = yield
  result = outcome.get_result()

  if result.when == 'call' and result.failed:
    failed.append({
        'name': item.name,
        'nodeid': result.nodeid,
        'location': item.location,
        'error': result.longreprtext
    })

def pytest_sessionfinish(session, exitstatus):
  if not failed:
    return
  if os.environ['PYTEST_MAIL'] != 'True':
    return
  body = f"The following tests have failed:<p>"
  for t in failed:
    body += f"<strong>{t['nodeid']}</strong><br>"
  body += f"<h2>Details</h2><strong>Time:</strong><pre>{iso_timestamp()}</pre>"
  for t in failed:
    body += f"<strong>{t['nodeid']}</strong><p><pre>{t['error']}</pre><p>"
  mail("Pytest Failure Report", body)

def pytest_configure(config):
  if 'BACKEND' in os.environ:
    print("\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print(f"Testing BACKEND:{os.environ['BACKEND']}")
    print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
