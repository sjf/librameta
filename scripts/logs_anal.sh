#!/bin/bash
set -ue

if [[ ${1:-} == '-v' ]]; then
  set -x
fi

DEST=admin/generated
TEMP_DIR=$(mktemp -d /tmp/logs_anal.XXXX)
mkdir -p $DEST
mkdir -p $TEMP_DIR

cp logs/feedback.html $DEST || true

{
cat logs/gunicorn/gunicorn-access.log* |
 sed -E 's|(([0-9]{1,3}.){3}[0-9]{1,3}), (([0-9]{1,3}.){3}[0-9]{1,3})|\3|' | # Some lines have >1 forwarded ip, just pick the second one.
 sed 's| -\([0-9][0-9]\)00\]|-\100\]|' | # Fix timestamps that have space before the timezone.
 cat > ${TEMP_DIR}/l
}

if [[ -z "${KEEP_TESTS:-}" ]]; then
  #Remove test searches.
  grep -v python-requests/lmlmlm ${TEMP_DIR}/l > ${TEMP_DIR}/l_
  mv ${TEMP_DIR}/l_ ${TEMP_DIR}/l
  # Remove self queries.
  if [[ -f secrets/self.txt ]]; then
    cat ${TEMP_DIR}/l | egrep -v $(cat secrets/self.txt) > ${TEMP_DIR}/l_
    mv ${TEMP_DIR}/l_ ${TEMP_DIR}/l
  fi
fi

cat ${TEMP_DIR}/l | egrep 'GET /(search|search-adv|)\?'| grep " 200 " | cut -d' ' -f6 | sed 's|^/.*[?]||' > ${TEMP_DIR}/s
scripts/logs.py searches ${TEMP_DIR}/s > ${DEST}/searches.txt

# old log format
cat ${TEMP_DIR}/l | grep 'LOG RESULTS' | cut -d' ' -f7- | sed "s|} Count:\([0-9]*\)\"|, 'count':\1}|" > ${TEMP_DIR}/r
# new log format
cat ${TEMP_DIR}/l | grep 'LOG_JSON RESULTS' | cut -d' ' -f7- |sed 's|"$||' >> ${TEMP_DIR}/r
scripts/logs.py results ${TEMP_DIR}/r > ${DEST}/results.txt
scripts/logs.py zero_results ${TEMP_DIR}/r > ${DEST}/searches_with_no_results.txt

cat ${TEMP_DIR}/l | grep 'DOWNLOAD' | cut -d' ' -f7- | sed 's|"$||' > ${TEMP_DIR}/d
scripts/logs.py downloads ${TEMP_DIR}/d > ${DEST}/downloads.txt

scripts/goaccess.sh ${1:-}

scripts/by_hour.sh ${TEMP_DIR}/l > ${DEST}/time_series.csv

rm -rf ${TEMP_DIR}
