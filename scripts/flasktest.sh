#!/bin/bash
set -eu
export BACKEND=https://$(hostname):9999
export VERIFY_SSL=False 
export IS_FLASK=yes 
# export TEST_DOWNLOAD=False
find . -name ._\* | xargs rm || true
pytest "$@"
