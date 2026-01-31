"""
Small migration helper: add `category` column to ReceiptItem for SQLite if it's missing.
Run from project root: python -m financial.scripts.add_category_column_if_missing
"""
from sqlmodel import create_engine
import sqlite3
import os

DB_PATH = "/tmp/financial.db"
DB_URL = f"sqlite:///{DB_PATH}"


def ensure_column():
    if not os.path.exists(DB_PATH):
        print("DB not found, nothing to migrate")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # inspect table info
    cur.execute("PRAGMA table_info('receiptitem')")
    cols = [r[1] for r in cur.fetchall()]
    if 'category' in cols:
        print('category column already present')
    else:
        print('Adding category column to receiptitem')
        cur.execute("ALTER TABLE receiptitem ADD COLUMN category TEXT")
        conn.commit()
        print('Done')
    conn.close()


if __name__ == '__main__':
    ensure_column()
