"""Ders servisi testleri."""

import pytest

from app.errors import NotFoundError, ValidationError


def test_add_course_uppercases_code(course_service):
    course = course_service.add("bil101", "Programlamaya Giriş", 4, "Dr. Kaya", "2026-Güz")
    assert course.code == "BIL101"
    assert course.label == "BIL101 - Programlamaya Giriş"
    assert course.credit == 4


def test_default_credit(course_service):
    course = course_service.add("MAT101", "Matematik I")
    assert course.credit == 3


def test_duplicate_code_rejected_case_insensitive(course_service):
    course_service.add("BIL101", "Programlamaya Giriş")
    with pytest.raises(ValidationError, match="zaten kayıtlı"):
        course_service.add("bil101", "Başka Ders")


@pytest.mark.parametrize("credit", [0, 11, -3, "abc", 3.5, ""])
def test_invalid_credit_rejected(course_service, credit):
    with pytest.raises(ValidationError, match="Kredi"):
        course_service.add("BIL101", "Programlamaya Giriş", credit)


@pytest.mark.parametrize("code", ["", "A", "BIL 101", "BIL@101"])
def test_invalid_code_rejected(course_service, code):
    with pytest.raises(ValidationError, match="Ders kodu"):
        course_service.add(code, "Programlamaya Giriş")


def test_missing_name_rejected(course_service):
    with pytest.raises(ValidationError, match="Ders adı"):
        course_service.add("BIL101", "  ")


def test_update_course(course_service):
    course = course_service.add("BIL101", "Programlamaya Giriş")
    updated = course_service.update(course.id, "BIL102", "İleri Programlama", 5, "Dr. Şen",
                                    "2026-Bahar")
    assert updated.code == "BIL102"
    assert updated.name == "İleri Programlama"
    assert updated.credit == 5
    assert updated.semester == "2026-Bahar"


def test_update_missing_course(course_service):
    with pytest.raises(NotFoundError):
        course_service.update(42, "BIL101", "Programlamaya Giriş")


def test_delete_course(course_service):
    course = course_service.add("BIL101", "Programlamaya Giriş")
    course_service.delete(course.id)
    assert course_service.list() == []
    with pytest.raises(NotFoundError):
        course_service.delete(course.id)


def test_search_courses(course_service):
    course_service.add("BIL101", "Programlamaya Giriş", 4, "Dr. Kaya", "2026-Güz")
    course_service.add("MAT101", "Matematik I", 4, "Prof. Dr. Öztürk", "2026-Güz")
    assert len(course_service.list()) == 2
    assert [c.code for c in course_service.list("matematik")] == ["MAT101"]
    assert [c.code for c in course_service.list("Kaya")] == ["BIL101"]
    assert course_service.list("hukuk") == []
