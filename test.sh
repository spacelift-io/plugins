#!/usr/bin/env bash

set -e

echo "Setting up dev dependencies..."
pip install -e ".[dev]"

echo "Running pytests..."
python -m pytest spaceforge/ -v

echo "Running type checks..."
python -m mypy spaceforge/

if [[ "$CI" == "true" ]]; then
    echo "Running code formatting checks..."
    python -m black --check spaceforge/

    echo "Running isort checks..."
    python -m isort --check-only spaceforge/

    echo "Running autoflake..."
    python -m autoflake --check ./**/*.py

    echo "Ensuring shema is up to date..."
    cd spaceforge
    python cls.py > schema.json
    git diff --exit-code schema.json || (echo "Schema has changed, please update it." && exit 1)
    cd -
else
    echo "Running code formatting..."
    python -m black spaceforge/

    echo "Running isort..."
    python -m isort spaceforge/

    echo "Running autoflake..."
    python -m autoflake --in-place ./**/*.py

    echo "Updating schema"
    cd spaceforge
    python cls.py > schema.json
    cd -
fi
