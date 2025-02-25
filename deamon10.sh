#!/usr/bin/env bash

trap SIGINT "kill -$$"

for i in {1..10}
do
	(
	while true
	do
		( sleep 3 && echo "Im $i" ) &
	done
) &
done

wait

