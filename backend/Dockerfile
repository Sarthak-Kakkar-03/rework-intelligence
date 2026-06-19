FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/pyproject.toml ./backend/
RUN pip install --no-cache-dir ./backend

COPY backend ./backend
COPY data ./data
COPY scripts ./scripts

EXPOSE 8000

CMD ["sh", "-c", "./scripts/reset_db.sh && cd backend && uvicorn main:app --host 0.0.0.0 --port 8000"]
