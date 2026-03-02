#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Place the legacy Pydantic v1 schemas.py in the workspace.
# The agent must migrate this file in-place to Pydantic v2.
# ---------------------------------------------------------------------------
cp /repo/schemas.py /workspace/schemas.py

echo "Workspace ready."
echo ""
echo "File to migrate: /workspace/schemas.py"
echo "Run tests with:  pytest /workspace/tests/test_schemas.py -v"
