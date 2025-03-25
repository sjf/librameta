#!/bin/bash
set -eu

if [[ ${1:-} == '-v' ]]; then
  set -x
  shift
fi

DEST=admin/generated/
LOG_FILES=logs/nginx/nginx-access.log*
TEMP_DIR=$(mktemp -d /tmp/goaccess.XXXX)
mkdir -p $TEMP_DIR

if [ -f secrets/self.txt ]; then
  zcat -f $LOG_FILES | egrep -v $(cat secrets/self.txt) > ${TEMP_DIR}/access.log
else
  zcat -f $LOG_FILES > ${TEMP_DIR}/access.log
fi

grep -v python-requests/lmlmlm ${TEMP_DIR}/access.log > ${TEMP_DIR}/access.log.1 || true
mv ${TEMP_DIR}/access.log.1 ${TEMP_DIR}/access.log

if [ -n "${GEOIP_DB:-}" ]; then
  GEOIP_ARG="--geoip-database=$GEOIP_DB"
fi
GOACCESS="goaccess --no-progress -p scripts/goaccess.conf ${GEOIP_ARG:-} --db-path=${TEMP_DIR}"

# remove the non-error message in a subshell (to preserve the exit code)
# and redirects output back to stderr. Because this tool sucks.
$GOACCESS --persist -o ${DEST}/report_all.html ${TEMP_DIR}/access.log 2> >(grep -v 'Cleaning up resources...' >&2)

# $GOACCESS --restore -o ${DEST}/report.html \
#   --ignore-panel=NOT_FOUND \
#   --ignore-panel=REQUESTS_STATIC \
#   --ignore-panel=VISIT_TIMES \
#   --ignore-panel=OS \
#   --ignore-panel=REQUESTS \
#   --ignore-panel=HOSTS \
#   --ignore-panel=KEYPHRASES \
#   --ignore-panel=ASN \
#   --ignore-panel=REFERRERS \
#   --ignore-panel=REFERRING_SITES \
#   --ignore-panel=BROWSERS \
#   2> >(grep -v 'Cleaning up resources...' >&2)
# $GOACCESS --restore -o ${DEST}/report_clients.html \
#   --ignore-panel=REQUESTS_STATIC \
#   --ignore-panel=NOT_FOUND \
#   --ignore-panel=VISIT_TIMES \
#   --ignore-panel=VIRTUAL_HOSTS \
#   --ignore-panel=STATUS_CODES \
#   --ignore-panel=REMOTE_USER \
#   --ignore-panel=CACHE_STATUS \
#   --ignore-panel=MIME_TYPE \
#   --ignore-panel=ASN \
#   --ignore-panel=TLS_TYPE \
#   2> >(grep -v 'Cleaning up resources...' >&2)

rm -rf $TEMP_DIR
  # --ignore-panel=VISITORS \
  # --ignore-panel=REQUESTS \
  # --ignore-panel=REQUESTS_STATIC \
  # --ignore-panel=NOT_FOUND \
  # --ignore-panel=HOSTS \
  # --ignore-panel=OS \
  # --ignore-panel=BROWSERS \
  # --ignore-panel=VISIT_TIMES \
  # --ignore-panel=VIRTUAL_HOSTS \
  # --ignore-panel=REFERRERS \
  # --ignore-panel=REFERRING_SITES \
  # --ignore-panel=KEYPHRASES \
  # --ignore-panel=STATUS_CODES \
  # --ignore-panel=REMOTE_USER \
  # --ignore-panel=CACHE_STATUS \
  # --ignore-panel=GEO_LOCATION \
  # --ignore-panel=MIME_TYPE \
  # --ignore-panel=TLS_TYPE \
  # --ignore-panel=ASN \
