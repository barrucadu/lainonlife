#!/usr/bin/env bash

MUSIC="/srv/radio/music"
OUT="/srv/http/file-list"

if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  echo "USAGE: $0 [music-dir] [out-dir]"
  echo
  echo "Positional arguments:"
  echo "  music-dir  Path of the channel music files [default: $MUSIC]"
  echo "  out-dir    Path to write the file lists to [default: $OUT]"
  exit 0
fi

if [[ ! -z "$1" ]] && [[ ! -z "$2" ]]; then
  MUSIC=$1
  OUT=$2
fi

if [[ ! -d "$MUSIC" ]]; then
  echo "music-dir must be a directory"
  exit 1
fi

if [[ ! -d "$OUT" ]]; then
  echo "out-dir must be a directory"
  exit 1
fi

cd $MUSIC
for channel in *; do
  tree    -l -I transitions "$channel" > "$OUT/$channel.txt"
  tree -d -l -I transitions "$channel" > "$OUT/$channel-albums.txt"
  tree    -l -I transitions -H "" -T "$channel" --nolinks "$channel" > "$OUT/$channel.html"
  tree -d -l -I transitions -H "" -T "$channel" --nolinks "$channel" > "$OUT/$channel-albums.html"
done
