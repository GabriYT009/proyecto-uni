#!/usr/bin/env python3
"""Import an SQL dump into sqlite db.sqlite3

Usage:
  python import_sql.py path/to/solucionarteBD.sql

If no path is provided, it will look for ../cliente/solucionarteBD.sql (relative to django_app/scripts).
"""
import sqlite3
from pathlib import Path
import sys

THIS_DIR = Path(__file__).resolve().parent
DEFAULT_SQL = THIS_DIR.parent.parent / 'cliente' / 'solucionarteBD.sql'
DB_PATH = THIS_DIR.parent / 'db.sqlite3'

def load_sql(sql_path: Path, db_path: Path):
    if not sql_path.exists():
        print(f"SQL file not found: {sql_path}")
        return 1
    # remove existing db if exists
    if db_path.exists():
        print(f"Removing existing DB at {db_path}")
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    sql_text = sql_path.read_text(encoding='utf-8')
    try:
        cur.executescript(sql_text)
        conn.commit()
        print(f"Imported SQL into {db_path}")
        return 0
    except Exception as e:
        print("Error importing SQL:", e)
        return 2
    finally:
        conn.close()

def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    sql_path = Path(arg) if arg else DEFAULT_SQL
    return load_sql(sql_path, DB_PATH)

if __name__ == '__main__':
    raise SystemExit(main())
