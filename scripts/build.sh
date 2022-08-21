#!/bin/bash

SOURCE="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
SOURCE_DIR="$(readlink -f ${SCRIPT_DIR}/..)"

source $HOME/miniforge3/etc/profile.d/conda.sh
status=$(conda activate $SOURCE_DIR/env/$1)

if [ "$status" != "" ]; then
    echo "Fail to activate env: $SOURCE_DIR/env/$1: $status"
    exit 0
fi

cd $SOURCE_DIR
rm -rf build/*
rm -rf dist/*
python setup.py sdist bdist_wheel
