#!/usr/bin/env bash

trap 'kill $(jobs -p)' EXIT
./watch.sh &

# running with python to ensure pipenv's python will be used 
python3 ./devserver.py
