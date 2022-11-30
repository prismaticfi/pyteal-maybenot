#!/bin/sh

set -e

# formatting flags
black_flags=""
isort_flags=""
poetry_flags="--remove-all-unused-imports --verbose --recursive --in-place --exclude=__init__.py"

set -x
poetry run isort . $isort_flags
poetry run black . $black_flags
poetry run autoflake $poetry_flags .

# run twice - one tool may lead to new changes required from another
poetry run isort . $isort_flags
poetry run black . $black_flags
poetry run autoflake $poetry_flags .
