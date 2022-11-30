#!/bin/sh

set -e

usage_msg="Usage: $0 [-f|--autoformat]"

case "$1" in
-h|--help|help)
  echo "$usage_msg"
  exit
  ;;
-f|--autoformat)
  ;;
*)
  # lint
  black_flags="--check"
  isort_flags="--check"
  ;;
esac

echo "Formatting..."
set -x
poetry run mypy .
poetry run isort . $isort_flags
poetry run black . $black_flags
poetry run flake8
