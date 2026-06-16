from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


# backend/db/seed.py
# parents[0] = db/
# parents[1] = backend/
# parents[2] = project root
REPO_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = REPO_ROOT / "backend" / "var" / "rework_autopsy.db"
MIGRATION_PATH = REPO_ROOT / "backend" / "db" / "migrations" / "001_init.sql"
SEED_DIR = REPO_ROOT / "data" / "seed"


TABLE_LOAD_ORDER = [
    ("teams", "teams.json"),
    ("repos", "repos.json"),
    ("issues", "issues.json"),
    ("pull_requests", "pull_requests.json"),
    ("rework_events", "rework_events.json"),
    ("context_artifacts", "context_artifacts.json"),
    ("context_recommendations", "context_recommendations.json"),
]


def load_json_array(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        print(f"Skipping missing seed file: {path}")
        return []

    raw = path.read_text(encoding="utf-8").strip()

    if not raw:
        print(f"Seed file is empty, treating as []: {path}")
        return []

    data = json.loads(raw)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}, got {type(data).__name__}")

    return data


def insert_rows(
    conn: sqlite3.Connection,
    table_name: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        print(f"{table_name}: inserted 0 rows")
        return

    columns = list(rows[0].keys())

    for row in rows:
        if list(row.keys()) != columns:
            raise ValueError(
                f"Inconsistent columns in {table_name}. "
                f"Expected {columns}, got {list(row.keys())}"
            )

    column_sql = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)

    sql = f"""
        INSERT INTO {table_name} ({column_sql})
        VALUES ({placeholders})
    """

    values = [[row[column] for column in columns] for row in rows]

    conn.executemany(sql, values)
    print(f"{table_name}: inserted {len(rows)} rows")


def reset_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        DB_PATH.unlink()

    if not MIGRATION_PATH.exists():
        raise FileNotFoundError(f"Missing migration file: {MIGRATION_PATH}")

    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(migration_sql)

        for table_name, file_name in TABLE_LOAD_ORDER:
            rows = load_json_array(SEED_DIR / file_name)
            insert_rows(conn, table_name, rows)

        conn.commit()

    except Exception:
        if conn is not None:
            conn.rollback()
        raise

    finally:
        if conn is not None:
            conn.close()

    print(f"\nDatabase created at: {DB_PATH}")


if __name__ == "__main__":
    reset_database()
