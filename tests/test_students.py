"""Öğrenci servisi testleri."""

import pytest

from app.errors import NotFoundError, ValidationError


def test_add_and_get(student_service):
    student = student_service.add(
        "2026001", "Elif", "Yılmaz", "Bilgisayar Mühendisliği", "elif@okul.edu.tr"
    )
    assert student.id is not None
    assert student.full_name == "Elif Yılmaz"
    assert student.label == "2026001 - Elif Yılmaz"
    fetched = student_service.get(student.id)
    assert fetched == student


def test_add_trims_whitespace(student_service):
    student = student_service.add(" 2026009 ", "  Ali ", " Veli ")
    assert student.student_no == "2026009"
    assert student.first_name == "Ali"
    assert student.last_name == "Veli"


def test_duplicate_student_number_rejected(student_service):
    student_service.add("2026001", "Elif", "Yılmaz")
    with pytest.raises(ValidationError, match="zaten kayıtlı"):
        student_service.add("2026001", "Başka", "Kişi")


def test_empty_fields_rejected(student_service):
    with pytest.raises(ValidationError, match="Öğrenci numarası"):
        student_service.add("", "Elif", "Yılmaz")
    with pytest.raises(ValidationError, match="Ad"):
        student_service.add("2026001", "", "Yılmaz")
    with pytest.raises(ValidationError, match="Soyad"):
        student_service.add("2026001", "Elif", "")


@pytest.mark.parametrize("number", ["12", "abc 123", "2026001!", "x" * 21])
def test_invalid_student_number(student_service, number):
    with pytest.raises(ValidationError):
        student_service.add(number, "Elif", "Yılmaz")


@pytest.mark.parametrize("email", ["elif", "elif@", "elif@okul", "@okul.edu.tr"])
def test_invalid_email(student_service, email):
    with pytest.raises(ValidationError, match="e-posta"):
        student_service.add("2026001", "Elif", "Yılmaz", email=email)


def test_update_changes_fields(student_service):
    student = student_service.add("2026001", "Elif", "Yılmaz")
    updated = student_service.update(
        student.id, "2026002", "Elif", "Kaya", "Yazılım Mühendisliği", "elif.kaya@okul.edu.tr"
    )
    assert updated.student_no == "2026002"
    assert updated.last_name == "Kaya"
    assert updated.department == "Yazılım Mühendisliği"


def test_update_duplicate_number_rejected(student_service):
    first = student_service.add("2026001", "Elif", "Yılmaz")
    student_service.add("2026002", "Ahmet", "Demir")
    with pytest.raises(ValidationError, match="zaten kayıtlı"):
        student_service.update(first.id, "2026002", "Elif", "Yılmaz")


def test_update_missing_student(student_service):
    with pytest.raises(NotFoundError):
        student_service.update(999, "2026001", "Elif", "Yılmaz")


def test_delete_student(student_service):
    student = student_service.add("2026001", "Elif", "Yılmaz")
    student_service.delete(student.id)
    assert student_service.list() == []
    with pytest.raises(NotFoundError):
        student_service.delete(student.id)


def test_list_and_search(student_service):
    student_service.add("2026001", "Elif", "Yılmaz", "Bilgisayar Mühendisliği")
    student_service.add("2026002", "Ahmet", "Demir", "Yazılım Mühendisliği")
    student_service.add("2026003", "Zeynep", "Kaya", "Bilgisayar Mühendisliği")

    assert len(student_service.list()) == 3
    assert [s.student_no for s in student_service.list("zeynep")] == ["2026003"]
    assert len(student_service.list("Bilgisayar")) == 2
    assert student_service.list("e-posta yok") == []


def test_count(student_service):
    assert student_service.count() == 0
    student_service.add("2026001", "Elif", "Yılmaz")
    assert student_service.count() == 1
