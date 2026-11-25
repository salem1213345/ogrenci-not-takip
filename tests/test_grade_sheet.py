"""Ders not çizelgesi, toplu not girişi ve öğretmen özeti."""

from datetime import date, timedelta

import pytest

from app.errors import ValidationError
from app.services.enrollment_service import EnrollmentService
from app.services.grade_service import SheetValidationError


@pytest.fixture()
def course_with_students(db, student_service, course_service):
    course = course_service.add("BIL101", "Programlama", 4)
    students = [student_service.add(f"20260{i:02d}", f"Ad{i}", "Soyad") for i in (1, 2, 3)]
    enroll = EnrollmentService(db)
    for student in students:
        enroll.enroll(student.id, course.id)
    return course, students


def test_adding_grade_enrolls_student(db, grade_service, sample):
    assert EnrollmentService(db).is_enrolled(sample.student.id, sample.other_course.id)


def test_course_sheet_rows(grade_service, course_with_students):
    course, students = course_with_students
    grade_service.add(students[0].id, course.id, "Vize", 80)
    grade_service.add(students[0].id, course.id, "Final", 60)
    sheet = grade_service.course_sheet(course.id)
    assert [row.student.id for row in sheet] == [s.id for s in students]
    assert sheet[0].average == 68.0 and sheet[0].letter == "DC" and sheet[0].status == "Geçti"
    assert sheet[1].average is None and sheet[1].status == "Not yok"


def test_save_sheet_adds_updates_and_skips_blanks(grade_service, course_with_students):
    course, students = course_with_students
    grade_service.add(students[0].id, course.id, "Vize", 50)
    added, updated = grade_service.save_sheet(course.id, {
        students[0].id: {"Vize": "55", "Final": "70,5"},
        students[1].id: {"Vize": "", "Final": "90"},
        students[2].id: {"Vize": "", "Final": ""},
    })
    assert (added, updated) == (2, 1)
    sheet = {row.student.id: row for row in grade_service.course_sheet(course.id)}
    assert sheet[students[0].id].grades["Vize"].score == 55
    assert sheet[students[0].id].grades["Final"].score == 70.5
    assert sheet[students[0].id].grades["Final"].weight == 60  # varsayılan ağırlık
    assert "Vize" not in sheet[students[1].id].grades


def test_save_sheet_is_all_or_nothing(grade_service, course_with_students):
    course, students = course_with_students
    with pytest.raises(SheetValidationError) as info:
        grade_service.save_sheet(course.id, {
            students[0].id: {"Vize": "75"},
            students[1].id: {"Vize": "120", "Final": "abc"},
        })
    assert set(info.value.errors) == {(students[1].id, "Vize"), (students[1].id, "Final")}
    assert grade_service.count() == 0  # hiçbir şey kaydedilmedi


def test_save_sheet_rejects_unenrolled(grade_service, course_with_students, student_service):
    course, _ = course_with_students
    outsider = student_service.add("2026099", "Dış", "Öğrenci")
    with pytest.raises(SheetValidationError, match="kayıtlı değil"):
        grade_service.save_sheet(course.id, {outsider.id: {"Vize": "50"}})


@pytest.mark.parametrize("value", ["31.02.2026", "1999-12-31",
                                   (date.today() + timedelta(days=400)).isoformat()])
def test_exam_date_must_be_valid_and_reasonable(grade_service, sample, value):
    with pytest.raises(ValidationError) as info:
        grade_service.add(sample.student.id, sample.other_course.id, "Final", 50, None, value)
    assert info.value.field == "Sınav tarihi"


def test_teacher_stats_are_computed(db, grade_service, course_service, sample):
    from app.services.auth_service import AuthService

    teacher = AuthService(db).create_teacher("ayse.kaya", "Ayşe Kaya", "Sifre2026")
    other = AuthService(db).create_teacher("mehmet.oz", "Mehmet Öz", "Sifre2026")
    course_service.add("FIZ101", "Fizik", 3, teacher_id=other.id)
    stats = grade_service.teacher_stats(teacher.id)
    # İlk öğretmen sample'daki iki dersi üstlendi; FIZ101 başkasının.
    assert stats["courses"] == 2 and stats["students"] == 1 and stats["grades"] == 3
    assert stats["average_gpa"] is not None
    assert grade_service.teacher_stats(other.id)["courses"] == 1
