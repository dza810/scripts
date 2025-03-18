#!/usr/bin/env bash

trap "kill -- -$$" SIGINT  

for i in {1..2}
do
	(
	while true
	do
		python -c "import time; time.sleep(10); print('$i')"
	done
) &
done

wait

