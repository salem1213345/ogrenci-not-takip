"""Uygulama genelinde kullanılan sabitler ve varsayılan yollar."""

from pathlib import Path

APP_NAME = "Öğrenci Not Takip Sistemi"
APP_VERSION = "2.0.0"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "cikti"
DEFAULT_DB_PATH = DATA_DIR / "notlar.db"
DEMO_DB_PATH = DATA_DIR / "demo.db"

EXAM_TYPES = ("Vize", "Final", "Ödev", "Proje")
DEFAULT_WEIGHTS = {"Vize": 40.0, "Final": 60.0, "Ödev": 20.0, "Proje": 30.0}
SEMESTERS = (
    "2025-Güz",
    "2025-Bahar",
    "2026-Güz",
    "2026-Bahar",
    "2027-Güz",
    "2027-Bahar",
)

CSV_ENCODING = "utf-8-sig"
CSV_DELIMITER = ";"
