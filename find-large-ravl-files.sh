#!/bin/bash

# Find files in .ravl folder over 500 lines (excluding venv and logs folders)
# Usage: ./find-large-ravl-files.sh [line_threshold]

THRESHOLD=${1:-500}

echo "Finding files in .ravl with more than $THRESHOLD lines..."
echo "Excluding: venv/ and logs/ folders"
echo ""

find .ravl -type f -not -path ".ravl/venv/*" -not -path ".ravl/logs/*" -exec wc -l {} + | awk -v threshold="$THRESHOLD" '$1 > threshold {print $1, $2}' | sort -rn
