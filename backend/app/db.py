from pathlib import Path
import sqlite3


REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "backend" / "var" / "rework_autopsy.db"


def get_connection() -> sqlite3.Connection:
    """
    Create a SQLite connection to the autopsy database.
    
    Returns:
    	A sqlite3.Connection object for the autopsy database.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
