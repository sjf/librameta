#!/bin/bash
# set -x

params=(page author title series isbn doi ext lang year start_year end_year)
request_types=(index search download 404) # Log file names used.

TEMP_DIR=$(mktemp -d /tmp/logs_by_hour.XXXX)
mkdir -p $TEMP_DIR

egrep 'GET /(search|search-adv|) '  "$1" > ${TEMP_DIR}/index.log
egrep 'GET /(search|search-adv|)\?' "$1" > ${TEMP_DIR}/search.log
egrep '"(LOG|LOG_JSON) DOWNLOAD {'  "$1" > ${TEMP_DIR}/download.log
egrep 'HTTP/..." 404 '              "$1" > ${TEMP_DIR}/404.log
egrep 'LOG_JSON RESULTS.* "count": 0,' "$1" > ${TEMP_DIR}/noresults.log

for f in "${params[@]}"; do
  egrep "GET /[^ ]*[&?]${f}=" ${TEMP_DIR}/search.log > ${TEMP_DIR}/${f}.log
done

files=()
for f in "${request_types[@]}" "${params[@]}" "noresults"; do
  {
    cat ${TEMP_DIR}/${f}.log |
    cut -d' ' -f 4 | # Get date, 4th field in log
    sed 's|^\[||' | sed 's|\]$||' | #remove square brackets around date
    sed 's|-[0-9][0-9]00$||' |  # remove timezone e.g. "-0700".
    grep '/202[0-9]' | # exclude lines that didnt parse properly
    # sed 's|:\([0-9][0-9]\):[0-9][0-9]:[0-9][0-9]$| \1:00:00|' | # use this to aggreate by hour: replace mins:secs with zeros, insert space between date and time.
    sed 's|:\([0-9][0-9]\):[0-9][0-9]:[0-9][0-9]$| 00:00:00|' | # use this to aggregate by day.
    sort | uniq -c | # count
    awk '{ print $2 " " $3 "," $1 }' | # convert to csv
    cat > ${TEMP_DIR}/${f}.csv
    files+=("${TEMP_DIR}/${f}.csv")
  }
done

# These logs arent just counted, they need to be averaged.
{
  egrep 'LOG_JSON DOWNLOAD' "$1" |
  egrep 'position":' |
  sed 's|^[^[]*\[||' | # remove before timestamp, up to first [
  sed 's|\].*"position": "|,|' | # remove between timestamp and position
  sed 's|".*||' | # remove after position
  # now the file is timestamps and positions
  # todo: the follow part can be for each file when there are more logs to consume.
  sed 's|-[0-9][0-9]00||' |  # remove timezone e.g. "-0700".
  grep '/202[0-9]' | # exclude lines that didnt parse properly
  # sed 's|:\([0-9][0-9]\):[0-9][0-9]:[0-9][0-9]$| \1:00:00|' | # use this to aggreate by hour: replace mins:secs with zeros, insert space between date and time.
  sed 's|:\([0-9][0-9]\):[0-9][0-9]:[0-9][0-9]| 00:00:00|' | # use this to aggregate by day.
  cat > ${TEMP_DIR}/download_positions.log
}
./scripts/average_timeseries.py ${TEMP_DIR}/download_positions.log > ${TEMP_DIR}/download_positions.csv
files+=("${TEMP_DIR}/download_positions.csv")

# Aggregate all the logs.
{
  ./scripts/zip_logs.py "${files[@]}" | # zip all the logs into one file
  sort -t/ -k3,3n -k2M -k1n # sort by date eg '14/Sep/2024'
}

rm -rf $TEMP_DIR
