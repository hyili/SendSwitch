#!/bin/sh

# This script is used to get routing key from apiserver.py

if [ "$1" != "" ]
then
	curl -X GET $1
else
	echo "get_key.sh [target_url]"
fi
