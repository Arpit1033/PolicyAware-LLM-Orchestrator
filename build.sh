#!/usr/bin/env bash
# Render Build Script
# This script is executed by Render during every deploy.

set -o errexit  # Exit on error

pip install -r requirements-lock.txt

cd src
python manage.py collectstatic --noinput
python manage.py migrate
