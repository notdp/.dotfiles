#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: fetch.sh <url> [output-file]" >&2
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

raw_url="$1"
output_file="${2:-}"

if [[ "$raw_url" != http://* && "$raw_url" != https://* ]]; then
  echo "Only http(s) URLs are supported: $raw_url" >&2
  exit 2
fi

normalized_url="${raw_url#http://}"
normalized_url="${normalized_url#https://}"
reader_url="https://r.jina.ai/http://${normalized_url}"

if [[ -n "$output_file" ]]; then
  curl -fsSL "$reader_url" -o "$output_file"
  echo "$output_file"
else
  curl -fsSL "$reader_url"
fi
