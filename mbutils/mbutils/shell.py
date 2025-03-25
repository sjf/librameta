import os
import subprocess
import sys
import glob
from .log import log

#### Shell Utils ###

def shell(cmd, env=None):
  log(f"Running '{cmd}'")
  # try:
  # check=True is equivalent of set -e, fail the script if this command fails.
  if env:
    subprocess.run(cmd, shell=True, check=True, env=env)
  else:
    subprocess.run(cmd, shell=True, check=True)
  # except subprocess.CalledProcessError:
  # print(f"Command failed: {e}")
  # sys.exit(1)

def read(f):
  if not f:
    raise Exception("Missing file name.")
  with open(f) as fh:
    return fh.read().strip()

def read_value(f):
  """ Read a non-empty value from a file."""
  value = read(f)
  if not value:
    raise Exception(f"File '{f}' was empty")
  return value

def maybe_read(f, default=''):
  """ Returns the contents of file `f`, or `default` if the file does not exist."""
  try:
    return read_value(f)
  except FileNotFoundError:
    return default

def read_lines(f, to_list=True):
  if not f:
    raise Exception("Missing file name.")
  with open(f) as fh:
    result = map(lambda x:x.rstrip(), fh.readlines())
    if to_list:
      return list(result)
    return result

def write(f, s):
  with open(f, 'w') as fh:
    fh.write(s)

def touch(f):
  write(f, '')

def rm(f):
  try:
    os.remove(f)
  except FileNotFoundError:
    pass

def rm_glob(pattern, verbose=False):
  arg = '-v' if verbose else ''
  subprocess.run(f"rm {arg} {pattern} 2>/dev/null", shell=True, check=False)

def mkdir(d):
  os.makedirs(d, exist_ok=True)

def exists(f):
  return f and os.path.exists(f)

def mv(a,b):
  os.rename(a,b)

def get_size(f):
  """ Returns the file size of `f` in human-readable format."""
  if not exists(f):
    return 0
  return subprocess.getoutput(f"du -hs {f} | cut -f1")

def ls(pattern):
  return glob.glob(pattern)

def stderr(s):
  sys.stderr.write(f"{str(s)}\n")
