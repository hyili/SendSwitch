#!/bin/sh

if [ "$1" != "" ] && [ "$2" != "" ]
then
	curl -X POST -H "Content-Type: application/json" -d "{\"routing_key\": \"$2\"}" $1
else
	echo "set_key.sh [target_url] [key]"
fi
