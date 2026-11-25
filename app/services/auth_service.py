"""Kullanıcı hesapları, parola özetleme ve giriş doğrulama.

Parolalar düz metin olarak saklanmaz: PBKDF2-HMAC-SHA256 (tuzlu, 200 000 tur)
ile özetlenir ve sabit zamanlı karşılaştırma ile doğrulanır.
"""

import hashlib
import hmac
import os
import sqlite3

from app.database import Database
from app.errors import AuthError, NotFoundError, ValidationError
from app.models import User
from app.validators import require_text, validate_password, validate_username

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 200_000
LOGIN_FAILED = "Kullanıcı adı veya şifre hatalı."


def hash_password(password: str, salt: bytes | None = None,
                  iterations: int = ITERATIONS) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate.hex(), digest_hex)


# Bilinmeyen kullanıcı adında da aynı süre harcanır (kullanıcı adı tahmini zorlaşır).
_DUMMY_HASH = hash_password("kullanici-yok-9", salt=b"\x00" * 16)


class AuthService:
    def __init__(self, db: Database):
        self.db = db

    # ---------------------------------------------------------------- sorgu
    def get(self, user_id) -> User:
        row = self.db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if row is None:
            raise NotFoundError("Kullanıcı bulunamadı.")
        return User.from_row(row)

    def has_teacher(self) -> bool:
        return self.db.query_one("SELECT 1 AS x FROM users WHERE role = 'teacher' LIMIT 1") \
            is not None

    def teachers(self) -> list[User]:
        rows = self.db.query("SELECT * FROM users WHERE role = 'teacher' ORDER BY full_name")
        return [User.from_row(row) for row in rows]

    def student_account(self, student_id) -> User | None:
        row = self.db.query_one("SELECT * FROM users WHERE student_id = ?", (student_id,))
        return User.from_row(row) if row else None

    # -------------------------------------------------------------- hesaplar
    @staticmethod
    def _secret(password, enforce_policy: bool) -> str:
        """Gerçek hesaplarda parola kuralı uygulanır; yalnızca demo verisi
        (enforce_policy=False) 1234 gibi basit parolalar kullanabilir."""
        if enforce_policy:
            return validate_password(password)
        if not password:
            raise ValidationError("Şifre zorunludur.", field="Şifre")
        return str(password)

    def create_teacher(self, username, full_name, password, password_again=None,
                       enforce_policy: bool = True) -> User:
        name = validate_username(username)
        display = require_text(full_name, "Ad Soyad", max_length=80)
        secret = self._secret(password, enforce_policy)
        if password_again is not None and password_again != password:
            raise ValidationError("Şifreler birbiriyle aynı değil.", field="Şifre (tekrar)")
        first_teacher = not self.has_teacher()
        try:
            new_id = self.db.execute(
                "INSERT INTO users (username, password_hash, role, full_name) "
                "VALUES (?, ?, 'teacher', ?)",
                (name, hash_password(secret), display),
            )
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Bu kullanıcı adı zaten kullanılıyor.",
                                  field="Kullanıcı adı") from exc
        if first_teacher:
            # İlk öğretmen hesabı, sorumlusu atanmamış mevcut dersleri üstlenir.
            self.db.run("UPDATE courses SET teacher_id = ? WHERE teacher_id IS NULL", (new_id,))
        return self.get(new_id)

    def set_student_password(self, student_id, password, password_again=None,
                             username=None, enforce_policy: bool = True) -> User:
        """Öğrencinin portal hesabını oluşturur veya şifresini sıfırlar.

        Yeni hesapta kullanıcı adı verilmezse öğrenci numarası kullanılır;
        var olan hesabın kullanıcı adı değişmez.
        """
        secret = self._secret(password, enforce_policy)
        login_name = validate_username(username) if username else None
        if password_again is not None and password_again != password:
            raise ValidationError("Şifreler birbiriyle aynı değil.", field="Şifre (tekrar)")
        student = self.db.query_one("SELECT * FROM students WHERE id = ?", (student_id,))
        if student is None:
            raise NotFoundError("Öğrenci bulunamadı.")
        existing = self.student_account(student_id)
        if existing:
            self.db.run("UPDATE users SET password_hash = ? WHERE id = ?",
                        (hash_password(secret), existing.id))
            return self.get(existing.id)
        try:
            new_id = self.db.execute(
                "INSERT INTO users (username, password_hash, role, full_name, student_id) "
                "VALUES (?, ?, 'student', ?, ?)",
                (login_name or student["student_no"], hash_password(secret),
                 f"{student['first_name']} {student['last_name']}", student_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValidationError(
                "Bu kullanıcı adı başka bir hesapta kullanılıyor.",
                field="Kullanıcı adı",
            ) from exc
        return self.get(new_id)

    def change_password(self, user_id, current, new, new_again=None) -> None:
        row = self.db.query_one("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        if row is None:
            raise NotFoundError("Kullanıcı bulunamadı.")
        if not verify_password(current or "", row["password_hash"]):
            raise ValidationError("Mevcut şifre hatalı.", field="Mevcut şifre")
        secret = validate_password(new, "Yeni şifre")
        if new_again is not None and new_again != new:
            raise ValidationError("Yeni şifreler birbiriyle aynı değil.",
                                  field="Yeni şifre (tekrar)")
        self.db.run("UPDATE users SET password_hash = ? WHERE id = ?",
                    (hash_password(secret), user_id))

    # ----------------------------------------------------------------- giriş
    def authenticate(self, username, password) -> User:
        name = (username or "").strip()
        row = self.db.query_one("SELECT * FROM users WHERE username = ?", (name,)) if name \
            else None
        stored = row["password_hash"] if row else _DUMMY_HASH
        if not verify_password(password or "", stored) or row is None:
            raise AuthError(LOGIN_FAILED)
        self.db.run("UPDATE users SET last_login = datetime('now', 'localtime') WHERE id = ?",
                    (row["id"],))
        return User.from_row(row)
