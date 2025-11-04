#!/usr/bin/env bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔄 Regenerating plugin YAML files..."
echo ""

# Store the root directory
ROOT_DIR=$(pwd)

# Track statistics
TOTAL=0
SUCCESS=0
SKIPPED=0
FAILED=0

# Iterate through each directory in plugins/
for plugin_dir in plugins/*/; do
    # Skip if not a directory or is __pycache__
    if [ ! -d "$plugin_dir" ] || [[ "$plugin_dir" == *"__pycache__"* ]]; then
        continue
    fi

    PLUGIN_NAME=$(basename "$plugin_dir")

    # Check if plugin.py exists
    if [ ! -f "$plugin_dir/plugin.py" ]; then
        echo -e "${YELLOW}⏭️  Skipping $PLUGIN_NAME - no plugin.py found${NC}"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    TOTAL=$((TOTAL + 1))

    echo -e "📦 Processing $PLUGIN_NAME..."

    # Change to plugin directory
    cd "$plugin_dir"

    # Install plugin requirements if they exist
    if [ -f "requirements.txt" ]; then
        echo "   📥 Installing requirements..."
        if ! pip install -q -r requirements.txt; then
            echo -e "${RED}   ⚠️  Warning: Failed to install requirements${NC}"
        fi
    fi

    # Run spaceforge generate
    if python -m spaceforge generate plugin.py; then
        echo -e "${GREEN}✅ Successfully regenerated $PLUGIN_NAME/plugin.yaml${NC}"
        SUCCESS=$((SUCCESS + 1))
    else
        echo -e "${RED}❌ Failed to regenerate $PLUGIN_NAME/plugin.yaml${NC}"
        FAILED=$((FAILED + 1))
    fi

    # Return to root directory
    cd "$ROOT_DIR"

    echo ""
done

# Print summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary:"
echo "   Total plugins processed: $TOTAL"
echo -e "   ${GREEN}Successful: $SUCCESS${NC}"
if [ $SKIPPED -gt 0 ]; then
    echo -e "   ${YELLOW}Skipped: $SKIPPED${NC}"
fi
if [ $FAILED -gt 0 ]; then
    echo -e "   ${RED}Failed: $FAILED${NC}"
    exit 1
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
