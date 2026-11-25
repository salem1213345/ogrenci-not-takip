"""Alan modelleri (Student, Course, Enrollment, Grade)."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Student:
    student_no: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    id: Optional[int] = None

    def full_name(self):
        return f"{self.first_name} {self.last_name}"


@dataclass
class Course:
    code: str
    name: str
    credit: int
    midterm_weight: float = 40.0
    final_weight: float = 60.0
    id: Optional[int] = None

    def validate_weights(self):
        total = self.midterm_weight + self.final_weight
        if abs(total - 100) > 1e-9:
            raise ValueError("Ağırlıklar toplamı 100 olmalıdır.")


@dataclass
class Enrollment:
    student_id: int
    course_id: int
    term: str
    id: Optional[int] = None


@dataclass
class Grade:
    enrollment_id: int
    midterm: Optional[float] = None
    final: Optional[float] = None
    assignment: Optional[float] = None
    id: Optional[int] = None

    def is_complete(self):
        return self.midterm is not None and self.final is not None
