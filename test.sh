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

echo "Running pylint checks..."
PYTHONPATH=. python -m pylint --errors-only spaceforge/ plugins/

if [[ "$CI" == "true" ]]; then
    echo "Running code formatting checks..."
    python -m black --check spaceforge/ plugins/

    echo "Running isort checks..."
    python -m isort --check-only spaceforge/ plugins/

    echo "Running autoflake..."
    python -m autoflake --check ./**/*.py

    echo "Ensuring schema is up to date..."
    cd spaceforge
    python cls.py > schema.json
    git diff --exit-code schema.json || (echo "Schema has changed, please update it." && exit 1)
    cd -
else
    echo "Running code formatting..."
    python -m black spaceforge/ plugins/

    echo "Running isort..."
    python -m isort spaceforge/ plugins/

    echo "Running autoflake..."
    python -m autoflake --in-place ./**/*.py

    echo "Updating schema"
    cd spaceforge
    python cls.py > schema.json
    cd -
fi
