#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

bash "$script_dir/file_list.sh" > url.list
xargs -r -d '\n' -n 1 -P 3 bash "$script_dir/download.sh" < url.list
