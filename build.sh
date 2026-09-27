#!/usr/bin/env bash
# Render build script for SRMS
set -o errexit

pip install --no-cache-dir -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
