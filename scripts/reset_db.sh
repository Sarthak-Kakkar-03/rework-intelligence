#!/usr/bin/env bash
set -e

rm -f backend/var/rework_autopsy.db
python backend/db/seed.py
echo "Database reset complete."
