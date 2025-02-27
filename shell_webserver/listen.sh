#!/usr/bin/env bash

trap "kill -- -$$" SIGINT
trap "kill -- -$$" SIGTERM
trap "kill -- -$$" SIGQUIT

cd "$(dirname $0)"

while true
do
  netcat --listen --local-port 8080 --source localhost -e 'bash ./http.sh' 
done

