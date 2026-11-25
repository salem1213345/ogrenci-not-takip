"""Hesaplar, parola özetleme ve giriş."""

import pytest

from app.errors import AuthError, ValidationError
from app.services.auth_service import AuthService, hash_password, verify_password


@pytest.fixture()
def auth(db):
    return AuthService(db)


def test_hash_is_salted_and_verifiable():
    first, second = hash_password("Parola123"), hash_password("Parola123")
    assert first != second  # farklı tuz
    assert "Parola123" not in first
    assert verify_password("Parola123", first)
    assert not verify_password("parola123", first)


@pytest.mark.parametrize("stored", ["", "bozuk", "md5$1$00$00", "pbkdf2_sha256$x$zz$00"])
def test_verify_rejects_malformed_hash(stored):
    assert verify_password("Parola123", stored) is False


def test_create_teacher_and_login(auth):
    assert not auth.has_teacher()
    teacher = auth.create_teacher("ayse.kaya", "Ayşe Kaya", "Ogretmen2026", "Ogretmen2026")
    assert teacher.is_teacher and auth.has_teacher()
    user = auth.authenticate("AYSE.KAYA", "Ogretmen2026")  # kullanıcı adı büyük/küçük duyarsız
    assert user.id == teacher.id


@pytest.mark.parametrize("username,password", [
    ("ayse.kaya", "yanlis1234"),
    ("olmayan", "Ogretmen2026"),
    ("", ""),
])
def test_login_failures_share_one_message(auth, username, password):
    auth.create_teacher("ayse.kaya", "Ayşe Kaya", "Ogretmen2026")
    with pytest.raises(AuthError, match="Kullanıcı adı veya şifre hatalı"):
        auth.authenticate(username, password)


@pytest.mark.parametrize("password", ["kisa1", "sadeceharf", "12345678", " Bosluk123"])
def test_weak_passwords_rejected(auth, password):
    with pytest.raises(ValidationError) as info:
        auth.create_teacher("ayse.kaya", "Ayşe Kaya", password)
    assert info.value.field == "Şifre"


def test_password_confirmation_must_match(auth):
    with pytest.raises(ValidationError, match="aynı değil"):
        auth.create_teacher("ayse.kaya", "Ayşe Kaya", "Ogretmen2026", "Ogretmen2027")


def test_duplicate_username_rejected(auth):
    auth.create_teacher("ayse.kaya", "Ayşe Kaya", "Ogretmen2026")
    with pytest.raises(ValidationError, match="zaten kullanılıyor"):
        auth.create_teacher("Ayse.Kaya", "Başka", "Ogretmen2026")


def test_first_teacher_claims_unassigned_courses(auth, course_service):
    course = course_service.add("BIL101", "Programlama", 4)
    teacher = auth.create_teacher("ayse.kaya", "Ayşe Kaya", "Ogretmen2026")
    second = auth.create_teacher("mehmet.oz", "Mehmet Öz", "Ogretmen2026")
    assert course_service.get(course.id).teacher_id == teacher.id
    assert second.id != teacher.id


def test_student_account_uses_student_number(auth, student_service):
    student = student_service.add("2026001", "Elif", "Yılmaz")
    account = auth.set_student_password(student.id, "Ogrenci2026", "Ogrenci2026")
    assert account.username == "2026001" and account.is_student
    assert auth.authenticate("2026001", "Ogrenci2026").student_id == student.id
    # Şifre sıfırlama aynı hesabı günceller.
    again = auth.set_student_password(student.id, "YeniSifre99")
    assert again.id == account.id
    with pytest.raises(AuthError):
        auth.authenticate("2026001", "Ogrenci2026")
    assert auth.authenticate("2026001", "YeniSifre99").id == account.id


def test_student_number_change_updates_username(auth, student_service):
    student = student_service.add("2026001", "Elif", "Yılmaz")
    auth.set_student_password(student.id, "Ogrenci2026")
    student_service.update(student.id, "2026101", "Elif", "Kaya")
    account = auth.student_account(student.id)
    assert account.username == "2026101" and account.full_name == "Elif Kaya"


def test_deleting_student_removes_account(auth, student_service, db):
    student = student_service.add("2026001", "Elif", "Yılmaz")
    auth.set_student_password(student.id, "Ogrenci2026")
    student_service.delete(student.id)
    assert db.query_one("SELECT COUNT(*) AS n FROM users")["n"] == 0


def test_change_password(auth):
    teacher = auth.create_teacher("ayse.kaya", "Ayşe Kaya", "Ogretmen2026")
    with pytest.raises(ValidationError, match="Mevcut şifre hatalı"):
        auth.change_password(teacher.id, "yanlis", "YeniSifre99", "YeniSifre99")
    auth.change_password(teacher.id, "Ogretmen2026", "YeniSifre99", "YeniSifre99")
    assert auth.authenticate("ayse.kaya", "YeniSifre99").id == teacher.id


def test_course_teacher_must_be_teacher_account(auth, course_service, student_service):
    student = student_service.add("2026001", "Elif", "Yılmaz")
    account = auth.set_student_password(student.id, "Ogrenci2026")
    with pytest.raises(ValidationError, match="sorumlu öğretmen"):
        course_service.add("BIL101", "Programlama", 4, teacher_id=account.id)
