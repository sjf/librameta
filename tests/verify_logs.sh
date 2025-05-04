#!/bin/bash
set -eux
: The last command run is the one that failed.
DEST=admin/generated

grep 'lmlmlm@example.com' ${DEST}/feedback.html
grep 'lmlmlm-message' ${DEST}/feedback.html

grep 'climbing bible' ${DEST}/searches.txt
grep 'climbing bible' ${DEST}/results.txt
grep 'Bitter Secrets' ${DEST}/downloads.txt
grep 'thistitledoesnotexist' ${DEST}/searches_with_no_results.txt
grep 'LOG_JSON RESULTS.*A14888D5DA7465A06BA13A19340314C1' logs/gunicorn/gunicorn-access.log

[ -f ${DEST}/report_all.html ]

: Logs passed verification
