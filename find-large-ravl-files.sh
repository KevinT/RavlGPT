#!/bin/bash

# Find files in .ravl folder over 500 lines (excluding venv and logs folders)
# Usage: ./find-large-ravl-files.sh [line_threshold]

THRESHOLD=${1:-500}

echo "Finding files in .ravl with more than $THRESHOLD lines..."
echo "Excluding: venv/, logs/, and build/ folders"
echo ""

find .ravl -type f -not -path "*/venv/*" -not -path "*/logs/*" -not -path "*/build/*" -exec wc -l {} + | awk -v threshold="$THRESHOLD" '$1 > threshold {print $1, $2}' | sort -rn
