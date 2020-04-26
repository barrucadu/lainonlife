#!/usr/bin/env bash

trap 'kill $(jobs -p)' EXIT
echo "watching files~"
watchmedo shell-command --recursive --command "pipenv run build" --ignore-patterns "./_site/*"

