"""Veri modeli: veritabanı satırlarının tip güvenli temsilleri."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Student:
    id: int | None
    student_no: str
    first_name: str
    last_name: str
    department: str = ""
    email: str = ""
    created_at: str = ""
    class_year: int | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def label(self) -> str:
        return f"{self.student_no} - {self.full_name}"

    @classmethod
    def from_row(cls, row: dict) -> "Student":
        return cls(
            id=row["id"],
            student_no=row["student_no"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            department=row.get("department", ""),
            email=row.get("email", ""),
            created_at=row.get("created_at", ""),
            class_year=row.get("class_year"),
        )


@dataclass(frozen=True)
class Course:
    id: int | None
    code: str
    name: str
    credit: int = 3
    instructor: str = ""
    semester: str = ""
    teacher_id: int | None = None

    @property
    def label(self) -> str:
        return f"{self.code} - {self.name}"

    @classmethod
    def from_row(cls, row: dict) -> "Course":
        return cls(
            id=row["id"],
            code=row["code"],
            name=row["name"],
            credit=row["credit"],
            instructor=row.get("instructor", ""),
            semester=row.get("semester", ""),
            teacher_id=row.get("teacher_id"),
        )


@dataclass(frozen=True)
class Grade:
    id: int
    student_id: int
    course_id: int
    exam_type: str
    score: float
    weight: float
    exam_date: str
    course_code: str = ""
    course_name: str = ""

    @classmethod
    def from_row(cls, row: dict) -> "Grade":
        return cls(
            id=row["id"],
            student_id=row["student_id"],
            course_id=row["course_id"],
            exam_type=row["exam_type"],
            score=float(row["score"]),
            weight=float(row["weight"]),
            exam_date=row["exam_date"],
            course_code=row.get("course_code", ""),
            course_name=row.get("course_name", ""),
        )


@dataclass(frozen=True)
class CourseAverage:
    """Bir öğrencinin tek bir dersteki ağırlıklı sonucu."""

    course_id: int
    course_code: str
    course_name: str
    credit: int
    average: float
    letter: str
    point: float
    passed: bool
    grade_count: int

    @property
    def status(self) -> str:
        return "Geçti" if self.passed else "Kaldı"


@dataclass
class StudentReport:
    """Bir öğrencinin tüm derslerini kapsayan karne özeti."""

    student: Student
    courses: list[CourseAverage] = field(default_factory=list)
    gpa: float | None = None
    total_credit: int = 0

    @property
    def failed_count(self) -> int:
        return sum(1 for course in self.courses if not course.passed)

    @property
    def status(self) -> str:
        if not self.courses:
            return "Not yok"
        return "Kaldı" if self.failed_count else "Geçti"


@dataclass(frozen=True)
class ClassSummary:
    """Sınıf listesi için öğrenci başına özet satır."""

    student_id: int
    student_no: str
    full_name: str
    department: str
    course_count: int
    gpa: float | None
    failed_count: int
    status: str


@dataclass(frozen=True)
class User:
    """Giriş yapabilen hesap (öğretmen veya öğrenci)."""

    id: int
    username: str
    role: str
    full_name: str
    student_id: int | None = None

    @property
    def is_teacher(self) -> bool:
        return self.role == "teacher"

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @classmethod
    def from_row(cls, row: dict) -> "User":
        return cls(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            full_name=row["full_name"],
            student_id=row.get("student_id"),
        )


@dataclass(frozen=True)
class Message:
    """Bir kullanıcının gördüğü mesaj satırı (gelen veya gönderilen)."""

    id: int
    sender_id: int
    sender_name: str
    subject: str
    body: str
    target_type: str
    target_label: str
    created_at: str
    parent_id: int | None = None
    read_at: str | None = None
    recipient_count: int = 0

    @property
    def is_unread(self) -> bool:
        return self.read_at is None

    @classmethod
    def from_row(cls, row: dict) -> "Message":
        return cls(
            id=row["id"],
            sender_id=row["sender_id"],
            sender_name=row.get("sender_name", ""),
            subject=row["subject"],
            body=row["body"],
            target_type=row["target_type"],
            target_label=row.get("target_label", ""),
            created_at=row["created_at"],
            parent_id=row.get("parent_id"),
            read_at=row.get("read_at"),
            recipient_count=int(row.get("recipient_count") or 0),
        )
