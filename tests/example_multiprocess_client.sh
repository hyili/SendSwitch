#!/bin/sh

for i in $(seq 1 10);
do
	./example_client.py $@ &
done
