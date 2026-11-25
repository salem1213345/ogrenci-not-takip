"""Ortak doğrulama yardımcıları."""

import math
import re
from datetime import date, datetime

from app.errors import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
CODE_RE = re.compile(r"^[A-Za-zÇĞİÖŞÜçğıöşü0-9._-]{2,16}$")


def clean(value) -> str:
    """None güvenli metin temizliği."""
    if value is None:
        return ""
    return str(value).strip()


def require_text(value, field: str, max_length: int = 100, min_length: int = 1) -> str:
    text = clean(value)
    if len(text) < min_length:
        raise ValidationError(f"{field} zorunludur.", field=field)
    if len(text) > max_length:
        raise ValidationError(f"{field} en fazla {max_length} karakter olabilir.", field=field)
    return text


def optional_text(value, field: str, max_length: int = 100) -> str:
    text = clean(value)
    if len(text) > max_length:
        raise ValidationError(f"{field} en fazla {max_length} karakter olabilir.", field=field)
    return text


def validate_email(value) -> str:
    email = clean(value)
    if email and not EMAIL_RE.match(email):
        raise ValidationError(
            "Geçerli bir e-posta adresi girin (örn. ad@okul.edu.tr).", field="E-posta"
        )
    if len(email) > 120:
        raise ValidationError("E-posta en fazla 120 karakter olabilir.", field="E-posta")
    return email


def parse_decimal(value, field: str, minimum: float, maximum: float) -> float:
    """Türkçe ondalık virgülünü de kabul eden sayı ayrıştırıcı."""
    text = clean(value).replace(",", ".")
    if not text:
        raise ValidationError(f"{field} zorunludur.", field=field)
    try:
        number = float(text)
    except ValueError as exc:
        raise ValidationError(f"{field} sayısal bir değer olmalıdır.", field=field) from exc
    # float() "nan"/"inf" metinlerini de kabul eder; NaN tüm karşılaştırmalarda
    # False döndüğü için aralık kontrolünü atlar ve SQLite'a NULL olarak gider.
    if not math.isfinite(number):
        raise ValidationError(f"{field} sayısal bir değer olmalıdır.", field=field)
    if number < minimum or number > maximum:
        raise ValidationError(
            f"{field} {minimum:g} ile {maximum:g} arasında olmalıdır.", field=field
        )
    return number


def parse_credit(value) -> int:
    number = parse_decimal(value, "Kredi", 1, 10)
    if not float(number).is_integer():
        raise ValidationError("Kredi 1 ile 10 arasında bir tam sayı olmalıdır.", field="Kredi")
    return int(number)


def parse_date(value, field: str = "Tarih") -> str:
    """ISO (YYYY-MM-DD) veya GG.AA.YYYY biçimini ISO'ya çevirir."""
    text = clean(value)
    if not text:
        return date.today().isoformat()
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValidationError(
        f"{field} GG.AA.YYYY veya YYYY-MM-DD biçiminde olmalıdır.", field=field
    )


CLASS_YEARS = (1, 2, 3, 4, 5, 6)
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
MIN_PASSWORD_LENGTH = 8


def parse_class_year(value) -> int | None:
    """Sınıf (1-6) isteğe bağlıdır; boş değer None döner."""
    text = clean(value)
    if not text:
        return None
    if not text.isdigit() or int(text) not in CLASS_YEARS:
        raise ValidationError("Sınıf 1 ile 6 arasında bir tam sayı olmalıdır.", field="Sınıf")
    return int(text)


def validate_username(value) -> str:
    username = clean(value)
    if not username:
        raise ValidationError("Kullanıcı adı zorunludur.", field="Kullanıcı adı")
    if not USERNAME_RE.match(username):
        raise ValidationError(
            "Kullanıcı adı 3-32 karakter olmalı; harf, rakam, nokta, - ve _ içerebilir.",
            field="Kullanıcı adı",
        )
    return username


def validate_password(value, field: str = "Şifre") -> str:
    password = "" if value is None else str(value)
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"{field} en az {MIN_PASSWORD_LENGTH} karakter olmalıdır.", field=field
        )
    if password.strip() != password:
        raise ValidationError(f"{field} boşlukla başlayamaz veya bitemez.", field=field)
    if not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
        raise ValidationError(f"{field} en az bir harf ve bir rakam içermelidir.", field=field)
    if len(password) > 128:
        raise ValidationError(f"{field} en fazla 128 karakter olabilir.", field=field)
    return password
