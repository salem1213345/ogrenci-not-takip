"""SQLite baglanti ve sema yonetimi."""
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB = "ogrenci_not.db"


def get_connection(path=DEFAULT_DB):
    """Yabanci anahtarlari acik bir baglanti dondurur ve semayi kurar."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn
