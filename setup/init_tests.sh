#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Copy test_schemas.py into the workspace tests directory.
# The test source is readable — difficulty in this task is API knowledge,
# not logic discovery.
# ---------------------------------------------------------------------------
mkdir -p /workspace/tests
cp /repo/test_schemas.py /workspace/tests/test_schemas.py

echo "Tests ready."
echo "Run tests with: pytest /workspace/tests/test_schemas.py -v"
