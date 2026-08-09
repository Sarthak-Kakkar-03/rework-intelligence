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

CMD ["./scripts/start_backend.sh"]
