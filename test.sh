#!/usr/bin/env bash

set -e

echo "Running pytests..."
python -m pytest spaceforge/ -v

echo "Running type checks..."
python -m mypy spaceforge/

if [[ "$CI" == "true" ]]; then
    echo "Running code formatting checks..."
    python -m black --check spaceforge/

    echo "Running isort checks..."
    python -m isort --check-only spaceforge/
else
    echo "Running code formatting..."
    python -m black spaceforge/

    echo "Running isort..."
    python -m isort spaceforge/
fi
