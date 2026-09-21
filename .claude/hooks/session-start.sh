#!/bin/bash
set -euo pipefail

# Only run in Claude Code on the web; local sessions manage their own Hugo install.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if ! command -v hugo >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq hugo
fi
