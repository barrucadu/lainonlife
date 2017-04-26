#!/usr/bin/env bash

for channel in everything; do
  tree -l                               "/srv/radio/music/$channel" > "/srv/http/file-list/$channel.txt"
  tree -l -H "" -T "$channel" --nolinks "/srv/radio/music/$channel" > "/srv/http/file-list/$channel.html"
done
