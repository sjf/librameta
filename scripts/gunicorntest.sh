#!/bin/bash
set -eu
export BACKEND=http://localhost:8001
export IS_GUNICORN=yes
export TEST_DOWNLOAD=False
find . -name ._\* | xargs rm || true
pytest "$@"
