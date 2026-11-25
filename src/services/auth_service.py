"""Parola ozetleme ve rol kontrolu (opsiyonel giris ozelligi)."""
import hashlib
import hmac
import os

ITERATIONS = 100_000
ADMIN_ONLY = {"delete_student", "delete_course", "manage_users"}


def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt,
                                 ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    salt_hex, digest_hex = stored.split("$")
    candidate = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(candidate, stored)


class AuthService:
    def __init__(self, conn):
        self.conn = conn

    def create_user(self, username, password, role="teacher"):
        if not username or len(password) < 6:
            raise ValueError("Kullanıcı adı boş olamaz, parola en az 6 karakter olmalıdır.")
        with self.conn:
            self.conn.execute(
                "INSERT INTO users (username, password_hash, role)"
                " VALUES (?, ?, ?)", (username, hash_password(password), role))

    def login(self, username, password):
        """Basarili ise (username, role) dondurur, degilse None."""
        row = self.conn.execute(
            "SELECT username, password_hash, role FROM users WHERE username=?",
            (username,)).fetchone()
        if row and verify_password(password, row["password_hash"]):
            return {"username": row["username"], "role": row["role"]}
        return None

    @staticmethod
    def has_permission(user, action):
        if action in ADMIN_ONLY:
            return user is not None and user["role"] == "admin"
        return user is not None
