"""Rol tabanlı mesajlaşma.

Kurallar (arayüzden bağımsız olarak burada uygulanır):
- Öğrenci yalnızca kayıtlı olduğu derslerin sorumlu öğretmenlerine yazabilir.
- Öğretmen kendi derslerine kayıtlı bir öğrenciye, bir sınıfa (o derslerdeki
  belirli sınıf düzeyindeki öğrenciler) veya bir dersin tüm öğrencilerine yazabilir.
- Herkes yalnızca gönderdiği veya alıcısı olduğu mesajları görür.
"""

from app.database import Database
from app.errors import AuthError, NotFoundError, ValidationError
from app.models import Message, User
from app.validators import clean, require_text

MAX_BODY = 4000

_SELECT = """
    SELECT m.*, u.full_name AS sender_name,
           (SELECT COUNT(*) FROM message_recipients r2 WHERE r2.message_id = m.id)
               AS recipient_count
    FROM messages m
    JOIN users u ON u.id = m.sender_id
"""


class MessageService:
    def __init__(self, db: Database):
        self.db = db

    # ---------------------------------------------------- izinli alıcılar
    def teachers_of_student(self, student_id) -> list[User]:
        rows = self.db.query(
            """SELECT DISTINCT u.* FROM enrollments e
               JOIN courses c ON c.id = e.course_id
               JOIN users u ON u.id = c.teacher_id
               WHERE e.student_id = ? ORDER BY u.full_name""",
            (student_id,),
        )
        return [User.from_row(row) for row in rows]

    def _teacher_course_ids(self, teacher_id) -> list[int]:
        rows = self.db.query(
            "SELECT id FROM courses WHERE teacher_id = ? OR teacher_id IS NULL", (teacher_id,)
        )
        return [int(row["id"]) for row in rows]

    def students_of_teacher(self, teacher_id) -> list[dict]:
        """Öğretmenin derslerine kayıtlı ve portal hesabı olan öğrenciler."""
        return self.db.query(
            """SELECT DISTINCT s.id AS student_id, s.student_no, s.first_name, s.last_name,
                      s.class_year, u.id AS user_id
               FROM enrollments e
               JOIN courses c ON c.id = e.course_id
               JOIN students s ON s.id = e.student_id
               JOIN users u ON u.student_id = s.id
               WHERE c.teacher_id = ? OR c.teacher_id IS NULL
               ORDER BY s.student_no""",
            (teacher_id,),
        )

    def class_years_of_teacher(self, teacher_id) -> list[int]:
        return sorted({int(row["class_year"]) for row in self.students_of_teacher(teacher_id)
                       if row["class_year"]})

    # ---------------------------------------------------------- gönderme
    @staticmethod
    def _content(subject, body) -> tuple[str, str]:
        return (require_text(subject, "Konu", max_length=120),
                require_text(body, "Mesaj", max_length=MAX_BODY))

    def _store(self, sender: User, subject, body, target_type, target_label,
               recipient_ids, parent_id=None) -> int:
        recipients = sorted({int(rid) for rid in recipient_ids if int(rid) != sender.id})
        if not recipients:
            raise ValidationError("Bu hedefte mesaj alabilecek (portal hesabı olan) kimse yok.",
                                  field="Alıcı")
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (sender_id, subject, body, target_type, target_label, "
                "parent_id) VALUES (?, ?, ?, ?, ?, ?)",
                (sender.id, subject, body, target_type, target_label, parent_id),
            )
            message_id = int(cur.lastrowid)
            cur.executemany(
                "INSERT INTO message_recipients (message_id, user_id) VALUES (?, ?)",
                [(message_id, rid) for rid in recipients],
            )
        return message_id

    def send_to_teacher(self, sender: User, teacher_id, subject, body) -> int:
        if not sender.is_student:
            raise AuthError("Bu işlem yalnızca öğrenciler içindir.")
        subject, body = self._content(subject, body)
        allowed = {t.id: t for t in self.teachers_of_student(sender.student_id)}
        if teacher_id is None or int(teacher_id) not in allowed:
            raise ValidationError("Yalnızca kayıtlı olduğunuz derslerin öğretmenlerine "
                                  "yazabilirsiniz.", field="Alıcı")
        teacher = allowed[int(teacher_id)]
        return self._store(sender, subject, body, "teacher", teacher.full_name, [teacher.id])

    def send_to_student(self, sender: User, student_id, subject, body) -> int:
        self._require_teacher(sender)
        subject, body = self._content(subject, body)
        match = [row for row in self.students_of_teacher(sender.id)
                 if int(row["student_id"]) == int(student_id or 0)]
        if not match:
            raise ValidationError("Bu öğrenci derslerinize kayıtlı değil veya portal hesabı yok.",
                                  field="Alıcı")
        row = match[0]
        label = f"{row['student_no']} - {row['first_name']} {row['last_name']}"
        return self._store(sender, subject, body, "student", label, [row["user_id"]])

    def send_to_class(self, sender: User, class_year, subject, body) -> int:
        self._require_teacher(sender)
        subject, body = self._content(subject, body)
        if not class_year:
            raise ValidationError("Sınıf seçin.", field="Alıcı")
        users = [row["user_id"] for row in self.students_of_teacher(sender.id)
                 if row["class_year"] and int(row["class_year"]) == int(class_year)]
        return self._store(sender, subject, body, "class", f"{int(class_year)}. Sınıf", users)

    def send_to_course(self, sender: User, course_id, subject, body) -> int:
        self._require_teacher(sender)
        subject, body = self._content(subject, body)
        if course_id is None or int(course_id) not in self._teacher_course_ids(sender.id):
            raise ValidationError("Yalnızca kendi derslerinize mesaj gönderebilirsiniz.",
                                  field="Alıcı")
        course = self.db.query_one("SELECT code, name FROM courses WHERE id = ?", (course_id,))
        rows = self.db.query(
            "SELECT u.id FROM enrollments e JOIN users u ON u.student_id = e.student_id "
            "WHERE e.course_id = ?",
            (course_id,),
        )
        return self._store(sender, subject, body, "course",
                           f"{course['code']} - {course['name']}", [r["id"] for r in rows])

    def reply(self, sender: User, message_id, body) -> int:
        original = self.get(sender, message_id)
        if original.sender_id == sender.id:
            raise ValidationError("Kendi gönderdiğiniz mesajı yanıtlayamazsınız.")
        body = require_text(body, "Mesaj", max_length=MAX_BODY)
        subject = original.subject if original.subject.startswith("Ynt: ") \
            else f"Ynt: {original.subject}"[:120]
        target_type = "teacher" if sender.is_student else "student"
        return self._store(sender, subject, body, target_type, original.sender_name,
                           [original.sender_id], parent_id=original.id)

    @staticmethod
    def _require_teacher(user: User) -> None:
        if not user.is_teacher:
            raise AuthError("Bu işlem yalnızca öğretmenler içindir.")

    # ----------------------------------------------------------- okuma
    def inbox(self, user: User) -> list[Message]:
        rows = self.db.query(
            _SELECT.replace("FROM messages m", ", r.read_at AS read_at FROM messages m")
            + " JOIN message_recipients r ON r.message_id = m.id AND r.user_id = ?"
              " ORDER BY m.created_at DESC, m.id DESC",
            (user.id,),
        )
        return [Message.from_row(row) for row in rows]

    def sent(self, user: User) -> list[Message]:
        rows = self.db.query(
            _SELECT.replace("FROM messages m", ", m.created_at AS read_at FROM messages m")
            + " WHERE m.sender_id = ? ORDER BY m.created_at DESC, m.id DESC",
            (user.id,),
        )
        return [Message.from_row(row) for row in rows]

    def get(self, user: User, message_id) -> Message:
        row = self.db.query_one(
            _SELECT.replace("FROM messages m", ", r.read_at AS read_at FROM messages m")
            + " LEFT JOIN message_recipients r ON r.message_id = m.id AND r.user_id = ?"
              " WHERE m.id = ? AND (m.sender_id = ? OR r.user_id IS NOT NULL)",
            (user.id, message_id, user.id),
        )
        if row is None:
            raise NotFoundError("Mesaj bulunamadı.")
        return Message.from_row(row)

    def mark_read(self, user: User, message_id) -> None:
        self.db.run(
            "UPDATE message_recipients SET read_at = datetime('now', 'localtime') "
            "WHERE message_id = ? AND user_id = ? AND read_at IS NULL",
            (message_id, user.id),
        )

    def unread_count(self, user: User) -> int:
        row = self.db.query_one(
            "SELECT COUNT(*) AS total FROM message_recipients WHERE user_id = ? "
            "AND read_at IS NULL",
            (user.id,),
        )
        return int(row["total"]) if row else 0

    @staticmethod
    def preview(text: str, length: int = 80) -> str:
        flat = " ".join(clean(text).split())
        return flat if len(flat) <= length else flat[: length - 1] + "…"
