#!/usr/bin/env python3
import pytest
import importlib
import responses
from unittest.mock import patch, MagicMock
from mbutils import *
import_py = importlib.import_module("import")

DB = 'foo'
URL = f"{config['DUMP_URL']}{DB}.rar"
REMOTE_ETAG = 'remote-etag'
REMOTE_RAR = 'remote-rar-contents'
PARTIAL_CONTENT = 'remote-rar-partial-content'

DIR = f"{config['DUMP_DIR']}/{DB}"
DEST_FILE = f'{DIR}/{DB}.rar'
TEMP_DEST_FILE = f'{DIR}/{DB}.{REMOTE_ETAG}.rar.incomplete'
ETAG_FILE = f'{DIR}/{DB}.etag'
TEMP_ETAG_FILE = f'{DIR}/{DB}.etag.inprogress'

def curl_succeeds(cmd, *args, **kwargs):
  if get_cmd(cmd) == 'curl':
    write(TEMP_ETAG_FILE, REMOTE_ETAG)
    write(TEMP_DEST_FILE, REMOTE_RAR)
  return subprocess.CompletedProcess(args, returncode=0)

def curl_fails(cmd, *args, **kwargs):
  if get_cmd(cmd) == 'curl':
    write(TEMP_ETAG_FILE, REMOTE_ETAG)
    write(TEMP_DEST_FILE, PARTIAL_CONTENT)
    raise subprocess.CalledProcessError(returncode=1, cmd=cmd)
  return subprocess.CompletedProcess(args, returncode=0)

def assert_curled(mock_run, n, resume=None):
  count = 0
  for args_list in mock_run.call_args_list:
    # Check the first arg. Shell commands appear as a single string.
    cmd = get_cmd(args_list[0][0])
    has_resume_flag = ' -C- ' in args_list[0][0]
    print(f"____________cmd: '{cmd}'")
    if cmd == 'curl':
      if resume is None:
        count += 1
      elif resume and has_resume_flag:
        count += 1
      elif not resume and not has_resume_flag:
        count += 1
  assert count == n

def get_cmd(shell_command):
  return shell_command.split(' ')[0]

@responses.activate
@patch("subprocess.run", side_effect=curl_succeeds)
def test_download_first_dl_suceeds(mock_run, fs):
  responses.add(responses.HEAD, URL, headers={"etag": REMOTE_ETAG}, status=200)
  # with patch("subprocess.run", side_effect=curl_succeeds) as mock_run:

  res = import_py.download(DB, True)

  assert res == REMOTE_ETAG
  assert_curled(mock_run, 1, resume=False)
  assert read(DEST_FILE) == REMOTE_RAR
  assert read(ETAG_FILE) == REMOTE_ETAG
  assert not exists(TEMP_ETAG_FILE)
  assert not exists(TEMP_DEST_FILE)

@responses.activate
@patch("subprocess.run")
def test_download_remote_file_not_changed(mock_run, fs):
  responses.add(responses.HEAD, URL, headers={"etag": REMOTE_ETAG}, status=200)
  mkdir(DIR)
  write(ETAG_FILE, REMOTE_ETAG)
  write(DEST_FILE, REMOTE_RAR)

  res = import_py.download(DB, True)

  assert res == REMOTE_ETAG
  assert_curled(mock_run, 0)
  assert read(DEST_FILE) == REMOTE_RAR
  assert read(ETAG_FILE) == REMOTE_ETAG
  assert not exists(TEMP_ETAG_FILE)
  assert not exists(TEMP_DEST_FILE)

@responses.activate
@patch("subprocess.run", side_effect=curl_succeeds)
def test_download_remote_file_changed(mock_run, fs):
  responses.add(responses.HEAD, URL, headers={"etag": REMOTE_ETAG}, status=200)
  mkdir(DIR)
  write(ETAG_FILE, 'old-etag')
  write(DEST_FILE, 'old-rar')

  res = import_py.download(DB, True)

  assert res == REMOTE_ETAG
  assert_curled(mock_run, 1, resume=False)
  assert read(DEST_FILE) == REMOTE_RAR
  assert read(ETAG_FILE) == REMOTE_ETAG
  assert not exists(TEMP_ETAG_FILE)
  assert not exists(TEMP_DEST_FILE)

@responses.activate
@patch("subprocess.run", side_effect=curl_succeeds)
def test_download_remote_file_changed_rms_in_progress_download(mock_run, fs):
  responses.add(responses.HEAD, URL, headers={"etag": REMOTE_ETAG}, status=200)
  mkdir(DIR)
  write(ETAG_FILE, 'old-etag')
  write(TEMP_DEST_FILE, 'old-partial-content')

  res = import_py.download(DB, True)

  assert res == REMOTE_ETAG
  assert_curled(mock_run, 1, resume=False)
  assert read(DEST_FILE) == REMOTE_RAR
  assert read(ETAG_FILE) == REMOTE_ETAG
  assert not exists(TEMP_ETAG_FILE)
  assert not exists(TEMP_DEST_FILE)

@responses.activate
@patch("subprocess.run", side_effect=curl_fails)
@patch("subprocess.getoutput", return_value='1000') # for `du`
def test_download_curl_retries_on_failure(mock_getoutput, mock_run, fs):
  responses.add(responses.HEAD, URL, headers={"etag": REMOTE_ETAG}, status=200)

  with pytest.raises(SystemExit) as exc_info:
    import_py.download(DB, True)

  assert exc_info.value.code == 1 # exit code.
  assert_curled(mock_run, 1, resume=False)
  assert_curled(mock_run, import_py.DL_RETRIES - 1, resume=True)
  assert read(TEMP_DEST_FILE) == PARTIAL_CONTENT
  assert read(TEMP_ETAG_FILE) == REMOTE_ETAG
  assert not exists(ETAG_FILE)
  assert not exists(DEST_FILE)

@responses.activate
@patch("subprocess.run", side_effect=curl_succeeds)
@patch("subprocess.getoutput", return_value='1000') # for `du`
def test_download_curl_resumes_in_progress_download(mock_getoutput, mock_run, fs):
  responses.add(responses.HEAD, URL, headers={"etag": REMOTE_ETAG}, status=200)
  mkdir(DIR)
  write(ETAG_FILE, 'old-etag') # From a previous import
  write(DEST_FILE, 'old-rar')
  write(TEMP_ETAG_FILE, REMOTE_ETAG) # In progress download.
  write(TEMP_DEST_FILE, PARTIAL_CONTENT)

  res = import_py.download(DB, True)

  assert res == REMOTE_ETAG
  assert_curled(mock_run, 1, resume=True)
  assert read(DEST_FILE) == REMOTE_RAR
  assert read(ETAG_FILE) == REMOTE_ETAG
  assert not exists(TEMP_ETAG_FILE)
  assert not exists(TEMP_DEST_FILE)

@responses.activate
@patch("subprocess.run", side_effect=curl_succeeds)
def test_download_remote_file_not_changed_download_missing(mock_run, fs):
  responses.add(responses.HEAD, URL, headers={"etag": REMOTE_ETAG}, status=200)
  mkdir(DIR)
  write(ETAG_FILE, REMOTE_ETAG)

  res = import_py.download(DB, True)

  assert res == REMOTE_ETAG
  assert_curled(mock_run, 1, resume=False)
  assert read(DEST_FILE) == REMOTE_RAR
  assert read(ETAG_FILE) == REMOTE_ETAG
  assert not exists(TEMP_ETAG_FILE)
  assert not exists(TEMP_DEST_FILE)
