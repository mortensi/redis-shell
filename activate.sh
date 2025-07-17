#!/bin/bash
# Auto-activate virtual environment and run redis-shell
source .venv/bin/activate
exec "$@"
