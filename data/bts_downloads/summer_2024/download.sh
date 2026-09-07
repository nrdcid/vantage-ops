#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 || -z $1 ]]; then
    echo "Usage: $0 ARCHIVE.zip" >&2
    exit 1
fi

archive=$1
wget --no-verbose -O "$archive" -- "https://transtats.bts.gov/PREZIP/$archive"
unzip -q -o "$archive"
rm -- "$archive"
