"""Rol tabanlı mesajlaşma ve ders kayıtları."""

from types import SimpleNamespace

import pytest

from app.errors import AuthError, NotFoundError, ValidationError
from app.services.auth_service import AuthService
from app.services.enrollment_service import EnrollmentService
from app.services.message_service import MessageService

PW = "Sifre2026"


@pytest.fixture()
def school(db, student_service, course_service):
    """İki öğretmen, üç öğrenci; her öğretmenin bir dersi."""
    auth, enroll = AuthService(db), EnrollmentService(db)
    t1 = auth.create_teacher("ayse.kaya", "Ayşe Kaya", PW)
    t2 = auth.create_teacher("mehmet.oz", "Mehmet Öz", PW)
    c1 = course_service.add("BIL101", "Programlama", 4, teacher_id=t1.id)
    c2 = course_service.add("MAT101", "Matematik", 4, teacher_id=t2.id)
    s1 = student_service.add("2026001", "Elif", "Yılmaz", class_year=1)
    s2 = student_service.add("2026002", "Ahmet", "Demir", class_year=2)
    s3 = student_service.add("2026003", "Zeynep", "Kaya", class_year=1)
    enroll.enroll(s1.id, c1.id)
    enroll.enroll(s2.id, c1.id)
    enroll.enroll(s3.id, c2.id)
    users = {s.student_no: auth.set_student_password(s.id, PW) for s in (s1, s2, s3)}
    return SimpleNamespace(t1=t1, t2=t2, c1=c1, c2=c2, s1=s1, s2=s2, s3=s3, users=users,
                           svc=MessageService(db), enroll=enroll)


def test_student_writes_only_to_own_teachers(school):
    elif_ = school.users["2026001"]
    assert [t.id for t in school.svc.teachers_of_student(school.s1.id)] == [school.t1.id]
    school.svc.send_to_teacher(elif_, school.t1.id, "Vize", "Vize notumu görebilir miyim?")
    with pytest.raises(ValidationError, match="kayıtlı olduğunuz"):
        school.svc.send_to_teacher(elif_, school.t2.id, "Soru", "Merhaba")


def test_teacher_inbox_unread_and_read(school):
    elif_ = school.users["2026001"]
    school.svc.send_to_teacher(elif_, school.t1.id, "Vize", "Vize notumu görebilir miyim?")
    inbox = school.svc.inbox(school.t1)
    assert len(inbox) == 1 and inbox[0].is_unread
    assert inbox[0].sender_name == "Elif Yılmaz" and inbox[0].subject == "Vize"
    assert school.svc.unread_count(school.t1) == 1
    school.svc.mark_read(school.t1, inbox[0].id)
    assert school.svc.unread_count(school.t1) == 0
    assert school.svc.inbox(school.t2) == []  # başka öğretmen göremez


def test_reply_goes_back_to_sender(school):
    elif_ = school.users["2026001"]
    message_id = school.svc.send_to_teacher(elif_, school.t1.id, "Vize", "Soru")
    school.svc.reply(school.t1, message_id, "Notunuz 80.")
    reply = school.svc.inbox(elif_)[0]
    assert reply.subject == "Ynt: Vize" and reply.parent_id == message_id
    assert school.svc.sent(school.t1)[0].body == "Notunuz 80."


def test_teacher_targets_course_class_student(school):
    svc, t1 = school.svc, school.t1
    svc.send_to_course(t1, school.c1.id, "Duyuru", "Vize tarihi değişti.")
    assert svc.unread_count(school.users["2026001"]) == 1
    assert svc.unread_count(school.users["2026002"]) == 1
    assert svc.unread_count(school.users["2026003"]) == 0  # başka dersin öğrencisi

    svc.send_to_class(t1, 1, "1. sınıflar", "Toplantı")  # yalnızca t1'in 1. sınıf öğrencileri
    assert svc.unread_count(school.users["2026001"]) == 2
    assert svc.unread_count(school.users["2026002"]) == 1
    assert svc.unread_count(school.users["2026003"]) == 0

    svc.send_to_student(t1, school.s2.id, "Ödev", "Ödevini teslim et.")
    assert svc.unread_count(school.users["2026002"]) == 2
    with pytest.raises(ValidationError, match="kayıtlı değil"):
        svc.send_to_student(t1, school.s3.id, "Ödev", "Başka dersin öğrencisi")
    with pytest.raises(ValidationError, match="kendi derslerinize"):
        svc.send_to_course(t1, school.c2.id, "Duyuru", "Başkasının dersi")


def test_users_cannot_read_others_messages(school):
    elif_, ahmet = school.users["2026001"], school.users["2026002"]
    message_id = school.svc.send_to_teacher(elif_, school.t1.id, "Özel", "Kişisel soru")
    with pytest.raises(NotFoundError):
        school.svc.get(ahmet, message_id)
    with pytest.raises(NotFoundError):
        school.svc.get(school.t2, message_id)
    assert school.svc.get(elif_, message_id).subject == "Özel"


def test_role_checks(school):
    elif_ = school.users["2026001"]
    with pytest.raises(AuthError):
        school.svc.send_to_course(elif_, school.c1.id, "x", "y")
    with pytest.raises(AuthError):
        school.svc.send_to_teacher(school.t1, school.t2.id, "x", "y")


@pytest.mark.parametrize("subject,body,field", [("", "metin", "Konu"), ("Konu", " ", "Mesaj")])
def test_message_requires_subject_and_body(school, subject, body, field):
    with pytest.raises(ValidationError) as info:
        school.svc.send_to_course(school.t1, school.c1.id, subject, body)
    assert info.value.field == field


def test_target_without_accounts_is_rejected(school, student_service, course_service):
    course = course_service.add("FIZ101", "Fizik", 3, teacher_id=school.t1.id)
    loner = student_service.add("2026009", "Hesapsız", "Öğrenci")
    school.enroll.enroll(loner.id, course.id)
    with pytest.raises(ValidationError, match="portal hesabı"):
        school.svc.send_to_course(school.t1, course.id, "Duyuru", "Metin")


def test_enrollment_rules(school, grade_service):
    enroll = school.enroll
    assert [s.student_no for s in enroll.students_of(school.c1.id)] == ["2026001", "2026002"]
    assert [s.student_no for s in enroll.students_of(school.c1.id, class_year=2)] == ["2026002"]
    assert enroll.enroll(school.s1.id, school.c1.id) is False  # zaten kayıtlı
    grade_service.add(school.s1.id, school.c1.id, "Vize", 70)
    with pytest.raises(ValidationError, match="notları var"):
        enroll.unenroll(school.s1.id, school.c1.id)
    enroll.unenroll(school.s2.id, school.c1.id)
    assert not enroll.is_enrolled(school.s2.id, school.c1.id)
