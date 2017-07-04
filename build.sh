#!/usr/bin/env nix-shell
#! nix-shell -i bash -p stack ghc

cd frontend
stack build
stack exec frontend build

if [[ "$1" == "deploy" ]]; then
  rsync -rv _site/ /srv/http/
fi
