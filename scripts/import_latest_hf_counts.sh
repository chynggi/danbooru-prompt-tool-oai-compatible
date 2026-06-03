#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p data

url="${1:-https://huggingface.co/datasets/newtextdoc1111/danbooru-tag-csv/resolve/main/danbooru_tags.csv}"
csv_path="data/danbooru_tags.csv"

curl -L "$url" -o "$csv_path"
python -m danbooru_prompt_tool import-csv --db data/danbooru_tags.sqlite --csv "$csv_path"
