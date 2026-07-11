#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."

python -m ashare_replay.cli ops-check
