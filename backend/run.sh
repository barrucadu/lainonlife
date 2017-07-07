#!/usr/bin/env bash

cd $(dirname $0)

ENV_DIR="__venv__"

if [[ ! -d "$ENV_DIR" ]]; then
  virtualenv "$ENV_DIR"
fi

source "$ENV_DIR/bin/activate"

pip install -r requirements.txt

python3 backend.py $*
