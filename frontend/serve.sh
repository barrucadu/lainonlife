#!/usr/bin/env bash

trap 'kill $(jobs -p)' EXIT
./watch.sh &
python -m http.server --directory ./_site
