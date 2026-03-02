#!/bin/bash
set -e

if [ -x "/root/.opencode/bin/opencode" ]; then
    /root/.opencode/bin/opencode web --hostname 0.0.0.0 --port 8080
else
    echo "OpenCode is not installed or not found at /root/.opencode/bin/opencode"
    exit 1
fi