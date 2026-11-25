"""Not servisi ve karne hesaplamaları testleri."""

import pytest

from app.errors import NotFoundError, ValidationError


def test_add_grade_uses_default_weight(grade_service, sample):
    grade = grade_service.add(sample.student.id, sample.other_course.id, "Final", 70)
    assert grade.weight == 60.0
    assert grade.exam_date  # bugünün tarihi atanır


def test_add_grade_with_comma_decimal(grade_service, sample):
    grade = grade_service.add(
        sample.student.id, sample.other_course.id, "Ödev", "78,5", None, "01.11.2026"
    )
    assert grade.score == 78.5
    assert grade.weight == 20.0
    assert grade.exam_date == "2026-11-01"


def test_duplicate_exam_type_rejected(grade_service, sample):
    with pytest.raises(ValidationError, match="zaten girilmiş"):
        grade_service.add(sample.student.id, sample.course.id, "Vize", 50)


@pytest.mark.parametrize("exam_type", ["Quiz", "", "vize"])
def test_invalid_exam_type(grade_service, sample, exam_type):
    with pytest.raises(ValidationError, match="Sınav türü"):
        grade_service.add(sample.student.id, sample.course.id, exam_type, 50)


@pytest.mark.parametrize("score", [-1, 101, "abc", "", "nan", "NaN", "inf", "-inf"])
def test_invalid_score(grade_service, sample, score):
    with pytest.raises(ValidationError, match="Puan"):
        grade_service.add(sample.student.id, sample.other_course.id, "Final", score)


@pytest.mark.parametrize("weight", [0, 150, "ağır", "nan"])
def test_invalid_weight(grade_service, sample, weight):
    with pytest.raises(ValidationError, match="Ağırlık"):
        grade_service.add(sample.student.id, sample.other_course.id, "Final", 70, weight)


def test_invalid_date(grade_service, sample):
    with pytest.raises(ValidationError, match="tarihi"):
        grade_service.add(sample.student.id, sample.other_course.id, "Final", 70, 60,
                          "2026-13-40")


def test_grade_requires_existing_student_and_course(grade_service, sample):
    with pytest.raises(NotFoundError):
        grade_service.add(999, sample.course.id, "Vize", 80)
    with pytest.raises(NotFoundError):
        grade_service.add(sample.student.id, 999, "Vize", 80)


def test_student_report_calculates_averages(grade_service, sample):
    report = grade_service.student_report(sample.student.id)
    assert len(report.courses) == 2
    bil = next(course for course in report.courses if course.course_code == "BIL101")
    mat = next(course for course in report.courses if course.course_code == "MAT101")
    assert bil.average == 68.0
    assert bil.letter == "DC"
    assert bil.passed is True
    assert bil.grade_count == 2
    assert mat.average == 90.0
    assert mat.letter == "AA"
    assert report.gpa == 2.75
    assert report.total_credit == 8
    assert report.status == "Geçti"
    assert report.failed_count == 0


def test_student_report_marks_failing_course(grade_service, student_service, course_service):
    student = student_service.add("2026010", "Ali", "Vural")
    course = course_service.add("BIL101", "Programlamaya Giriş", 4)
    grade_service.add(student.id, course.id, "Final", 45)
    report = grade_service.student_report(student.id)
    assert report.courses[0].letter == "FF"
    assert report.courses[0].status == "Kaldı"
    assert report.status == "Kaldı"
    assert report.failed_count == 1


def test_report_without_grades(grade_service, student_service):
    student = student_service.add("2026011", "Boş", "Öğrenci")
    report = grade_service.student_report(student.id)
    assert report.courses == []
    assert report.gpa is None
    assert report.total_credit == 0
    assert report.status == "Not yok"


def test_report_missing_student(grade_service):
    with pytest.raises(NotFoundError):
        grade_service.student_report(999)


def test_update_grade_changes_average(grade_service, sample):
    final = next(
        grade for grade in grade_service.list_by_student(sample.student.id)
        if grade.course_code == "BIL101" and grade.exam_type == "Final"
    )
    updated = grade_service.update(
        final.id, sample.student.id, sample.course.id, "Final", 100, 60, final.exam_date
    )
    assert updated.score == 100.0
    report = grade_service.student_report(sample.student.id)
    bil = next(course for course in report.courses if course.course_code == "BIL101")
    assert bil.average == 92.0
    assert bil.letter == "AA"


def test_list_by_student_and_course(grade_service, sample):
    student_grades = grade_service.list_by_student(sample.student.id)
    assert len(student_grades) == 3
    assert [grade.exam_type for grade in student_grades[:2]] == ["Final", "Vize"]

    course_grades = grade_service.list_by_course(sample.course.id)
    assert [grade.score for grade in course_grades] == [80.0, 60.0]


def test_delete_grade(grade_service, sample):
    grade = grade_service.list_by_student(sample.student.id)[0]
    grade_service.delete(grade.id)
    with pytest.raises(NotFoundError):
        grade_service.get(grade.id)
    assert grade_service.count() == 2


def test_class_summary(grade_service, student_service, course_service):
    first = student_service.add("2026001", "Elif", "Yılmaz", "Bilgisayar")
    second = student_service.add("2026002", "Ahmet", "Demir", "Yazılım")
    course = course_service.add("BIL101", "Programlamaya Giriş", 4)
    grade_service.add(first.id, course.id, "Final", 90)
    grade_service.add(second.id, course.id, "Final", 40)

    summary = grade_service.class_summary()
    assert [row.student_no for row in summary] == ["2026001", "2026002"]
    assert summary[0].gpa == 4.0
    assert summary[0].status == "Geçti"
    assert summary[1].gpa == 0.0
    assert summary[1].status == "Kaldı"
    assert summary[1].failed_count == 1
