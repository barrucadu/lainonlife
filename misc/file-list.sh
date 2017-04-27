#!/usr/bin/env bash

cd /srv/radio/music
for channel in *; do
  tree -l -I transitions                               "$channel" > "/srv/http/file-list/$channel.txt"
  tree -l -I transitions -H "" -T "$channel" --nolinks "$channel" > "/srv/http/file-list/$channel.html"
  tree -d -l -I transitions                               "$channel" > "/srv/http/file-list/$channel-albums.txt"
  tree -d -l -I transitions -H "" -T "$channel" --nolinks "$channel" > "/srv/http/file-list/$channel-albums.html"
done
