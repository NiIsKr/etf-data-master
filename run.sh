#!/bin/bash
set -e

cd "$(dirname "$0")"

# Activate venv
source venv/bin/activate

# Run monitor with defaults + any additional flags
python -m src.monitor \
  --isins LU3098954871,LU3075459852 \
  "$@"
