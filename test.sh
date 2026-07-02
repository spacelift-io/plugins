#!/usr/bin/env bash

set -e

echo "Setting up dev dependencies..."
pip install -e ".[dev]"

echo "Installing plugin dependencies..."
for req_file in plugins/*/requirements.txt; do
    if [ -f "$req_file" ]; then
        echo "  Installing $(dirname "$req_file")..."
        pip install -q -r "$req_file"
    fi
done

echo "Validating plugins..."
python validate_plugins.py

echo "Running pytests..."
python -m pytest spaceforge/ -v

echo "Running type checks..."
python -m mypy spaceforge/

if [[ "$CI" == "true" ]]; then
    echo "Running ruff lint checks..."
    ruff check spaceforge/ plugins/

    echo "Running ruff format checks..."
    ruff format --check spaceforge/ plugins/

    echo "Ensuring schema is up to date..."
    cd spaceforge
    python cls.py > schema.json
    git diff --exit-code schema.json || (echo "Schema has changed, please update it." && exit 1)
    cd -
else
    echo "Running ruff lint (with fixes)..."
    ruff check --fix spaceforge/ plugins/

    echo "Running ruff format..."
    ruff format spaceforge/ plugins/

    echo "Updating schema"
    cd spaceforge
    python cls.py > schema.json
    cd -
fi
