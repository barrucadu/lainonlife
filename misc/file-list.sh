#!/usr/bin/env bash

cd /srv/radio/music
for channel in *; do
  tree -l                               "$channel" > "/srv/http/file-list/$channel.txt"
  tree -l -H "" -T "$channel" --nolinks "$channel" > "/srv/http/file-list/$channel.html"
done
