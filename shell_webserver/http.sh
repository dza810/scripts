#!/usr/bin/env bash

set -eu

declare -A headers

read method url version

while read l
do
  line=$(echo -n "$l" | tr -d '\r\n')
  [[ -z "$line" ]] && break
  IFS=": " read -r k v <<<"$line"
  headers["${k,,}"]="$v"
done

for k in "${!headers[@]}"
do
  echo "$k: ${headers[$k]}" >output
done

status="404 Not Found"
body=""
if [[ -f "./${url}" ]]
then
  status="200 OK"
  body=$(cat ".${url}")
fi

cat <<EOF
HTTP/1.1 $status
Content-Length: ${#body}
Content-Type: text/html

${body}
EOF

