"""SQLite bağlantısı, şema yönetimi ve küçük yardımcı metotlar."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_no  TEXT    NOT NULL UNIQUE,
    first_name  TEXT    NOT NULL,
    last_name   TEXT    NOT NULL,
    department  TEXT    NOT NULL DEFAULT '',
    email       TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS courses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    credit      INTEGER NOT NULL DEFAULT 3 CHECK (credit BETWEEN 1 AND 10),
    instructor  TEXT    NOT NULL DEFAULT '',
    semester    TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS grades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id   INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    exam_type   TEXT    NOT NULL,
    score       REAL    NOT NULL CHECK (score BETWEEN 0 AND 100),
    weight      REAL    NOT NULL DEFAULT 1 CHECK (weight > 0),
    exam_date   TEXT    NOT NULL DEFAULT (date('now')),
    UNIQUE (student_id, course_id, exam_type)
);

CREATE INDEX IF NOT EXISTS idx_grades_student ON grades(student_id);
CREATE INDEX IF NOT EXISTS idx_grades_course ON grades(course_id);
"""

# Sürüm 2: kullanıcı hesapları, ders kayıtları (enrollment) ve mesajlaşma.
# Mevcut tablolara yalnızca NULL olabilen sütunlar eklenir; hiçbir satır silinmez.
MIGRATION_V2 = (
    "ALTER TABLE students ADD COLUMN class_year INTEGER",
    """CREATE TABLE users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT    NOT NULL,
        role          TEXT    NOT NULL CHECK (role IN ('teacher', 'student')),
        full_name     TEXT    NOT NULL,
        student_id    INTEGER UNIQUE REFERENCES students(id) ON DELETE CASCADE,
        created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        last_login    TEXT,
        CHECK ((role = 'student') = (student_id IS NOT NULL))
    )""",
    "ALTER TABLE courses ADD COLUMN teacher_id INTEGER REFERENCES users(id) ON DELETE SET NULL",
    """CREATE TABLE enrollments (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        course_id   INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        UNIQUE (student_id, course_id)
    )""",
    # Notu olan her öğrenci o derse kayıtlı sayılır: mevcut veriden kayıtlar üretilir.
    """INSERT OR IGNORE INTO enrollments (student_id, course_id)
       SELECT DISTINCT student_id, course_id FROM grades""",
    """CREATE TABLE messages (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject      TEXT    NOT NULL,
        body         TEXT    NOT NULL,
        target_type  TEXT    NOT NULL
                     CHECK (target_type IN ('teacher', 'student', 'class', 'course')),
        target_label TEXT    NOT NULL DEFAULT '',
        parent_id    INTEGER REFERENCES messages(id) ON DELETE SET NULL,
        created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    )""",
    """CREATE TABLE message_recipients (
        message_id  INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        read_at     TEXT,
        PRIMARY KEY (message_id, user_id)
    )""",
    """CREATE TABLE meta (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""",
    "CREATE INDEX idx_enrollments_course ON enrollments(course_id)",
    "CREATE INDEX idx_recipients_user ON message_recipients(user_id, read_at)",
    "CREATE INDEX idx_messages_sender ON messages(sender_id)",
)

MIGRATIONS = {2: MIGRATION_V2}
SCHEMA_VERSION = max(MIGRATIONS)


class Database:
    """Tek bir SQLite dosyasını yöneten ince katman."""

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        is_file = self.path != ":memory:"
        existed = is_file and Path(self.path).is_file() and Path(self.path).stat().st_size > 0
        if is_file:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self.backup_path: Path | None = None
        self._migrate(backup_first=existed)

    # ------------------------------------------------------------ migration
    @property
    def schema_version(self) -> int:
        return int(self._conn.execute("PRAGMA user_version").fetchone()[0])

    def _migrate(self, backup_first: bool) -> None:
        """Eksik sürüm adımlarını sırayla ve her biri tek işlem içinde uygular."""
        current = self.schema_version
        if current >= SCHEMA_VERSION:
            return
        if backup_first:
            # Var olan bir dosya güncellenmeden önce otomatik yedeği alınır.
            target = Path(self.path)
            self.backup_path = target.with_name(f"{target.stem}.v{current or 1}-yedek.db")
            if not self.backup_path.exists():
                backup = sqlite3.connect(str(self.backup_path))
                with backup:
                    self._conn.backup(backup)
                backup.close()
        for version in sorted(v for v in MIGRATIONS if v > current):
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                for statement in MIGRATIONS[version]:
                    self._conn.execute(statement)
                self._conn.execute(f"PRAGMA user_version = {int(version)}")
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    # ----------------------------------------------------------------- meta
    def get_meta(self, key: str, default: str | None = None) -> str | None:
        row = self.query_one("SELECT value FROM meta WHERE key = ?", (key,))
        return row["value"] if row else default

    def set_meta(self, key: str, value: str) -> None:
        self.run(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    @contextmanager
    def cursor(self):
        """İşlemi (transaction) yöneten imleç bağlamı."""
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    def execute(self, sql: str, params: tuple = ()) -> int:
        """INSERT çalıştırır, yeni kaydın id değerini döndürür."""
        with self.cursor() as cur:
            cur.execute(sql, params)
            return int(cur.lastrowid or 0)

    def run(self, sql: str, params: tuple = ()) -> int:
        """UPDATE/DELETE çalıştırır, etkilenen satır sayısını döndürür."""
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
