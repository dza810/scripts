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

# Content-Length: ${#body}

status="200 OK"
cat <<EOF
HTTP/1.1 $status
Content-Type: text/plain
Transfer-Encoding: chunked

EOF

while read l
do
  line=$(echo -n "$l" | tr -d '\r\n')
  echo "${#line} ${line}" >output
  [[ -z "$line" ]] && continue
  echo -ne "${#line}\r\n${line}\r\n"
done <<<"$body"

echo -ne "0\r\n\r\n"

