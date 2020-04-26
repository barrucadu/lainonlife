#!/usr/bin/env bash

if [ -z "$1" ]; then
    ./build.py ../config.json.example
else
    ./build.py "$1"
fi
