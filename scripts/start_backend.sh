#!/bin/sh
set -eu

PYTHON_CMD=${PYTHON_CMD:-python}
UVICORN_CMD=${UVICORN_CMD:-uvicorn}

rm -f backend/var/rework_autopsy.db

cd backend
${PYTHON_CMD} db/seed.py
${PYTHON_CMD} scripts/ml-classifier/train_classifier.py
${PYTHON_CMD} scripts/ml-classifier/train_final_model.py

exec ${UVICORN_CMD} main:app --host 0.0.0.0 --port 8000
