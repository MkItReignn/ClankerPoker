#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
git pull --ff-only
poetry install --only main
sudo systemctl restart clankerpoker
sudo systemctl --no-pager status clankerpoker | head -5
