"""Ayrı demo veritabanı (data/demo.db) için örnek veri seti.

- Gerçek veritabanına (data/notlar.db) asla yüklenmez: main.py bunu engeller,
  ayrıca burada gerçek veri içeren bir veritabanı reddedilir.
- Yalnızca boş veritabanına yüklenir; dolu demo veritabanı korunur (kalıcılık).
  Bilerek sıfırlamak için: python main.py --demo --db data/demo.db --reset-demo
- Veriler sabittir (rastgele üreteç sabit tohumla çalışır); her sıfırlamada aynıdır.
- Demo hesapları basit şifre (1234) kullanır; gerçek hesaplarda şifre kuralı geçerlidir.
"""

import random
from dataclasses import dataclass
from pathlib import Path

from app.database import Database
from app.errors import ValidationError
from app.services.auth_service import AuthService, verify_password
from app.services.course_service import CourseService
from app.services.message_service import MessageService
from app.services.student_service import StudentService

DEMO_FLAG = "demo"
DEMO_PASSWORD = "1234"
TEACHER_PASSWORD = DEMO_PASSWORD
STUDENT_PASSWORD = DEMO_PASSWORD

# (kullanıcı adı, ad soyad, unvanlı ad)
TEACHERS = (
    ("ogretmen1", "Ayşe Kaya", "Dr. Öğr. Üyesi Ayşe Kaya"),
    ("ogretmen2", "Kemal Öztürk", "Prof. Dr. Kemal Öztürk"),
    ("ogretmen3", "Selin Arslan", "Doç. Dr. Selin Arslan"),
    ("ogretmen4", "Murat Şen", "Öğr. Gör. Murat Şen"),
)

# (kod, ad, kredi, dönem, öğretmen, sınıf düzeyi, zorluk: puana eklenen sapma)
COURSES = (
    ("MAT201", "Matematik", 4, "2025-Güz", "ogretmen2", 2, -8),
    ("BIL205", "Algoritmalar", 4, "2025-Güz", "ogretmen2", 2, -4),
    ("BIL203", "Veri Tabanı", 3, "2025-Güz", "ogretmen1", 2, 4),
    ("BIL207", "Ağ Sistemleri", 3, "2025-Güz", "ogretmen4", 2, 0),
    ("BIL302", "İşletim Sistemleri", 4, "2026-Bahar", "ogretmen4", 3, -5),
    ("BIL304", "Yazılım Mimarisi", 3, "2026-Bahar", "ogretmen1", 3, 5),
    ("BIL306", "Yapay Zeka", 4, "2026-Bahar", "ogretmen3", 3, -2),
    ("BIL308", "Görüntü İşleme", 3, "2026-Bahar", "ogretmen3", 3, 1),
)

# (ad, soyad, bölüm)  ilk 15 -> 2. sınıf, son 15 -> 3. sınıf
STUDENT_NAMES = (
    ("Elif", "Yılmaz", "Bilgisayar Mühendisliği"),
    ("Ahmet", "Demir", "Bilgisayar Mühendisliği"),
    ("Zeynep", "Kaya", "Yazılım Mühendisliği"),
    ("Mehmet", "Çelik", "Bilgisayar Mühendisliği"),
    ("Ayşe", "Şahin", "Yazılım Mühendisliği"),
    ("Burak", "Aydın", "Bilgisayar Mühendisliği"),
    ("Selin", "Yıldız", "Yazılım Mühendisliği"),
    ("Emre", "Koç", "Bilgisayar Mühendisliği"),
    ("Merve", "Kurt", "Yazılım Mühendisliği"),
    ("Can", "Özdemir", "Bilgisayar Mühendisliği"),
    ("İrem", "Aslan", "Yazılım Mühendisliği"),
    ("Oğuz", "Doğan", "Bilgisayar Mühendisliği"),
    ("Deniz", "Erdoğan", "Bilgisayar Mühendisliği"),
    ("Cem", "Polat", "Yazılım Mühendisliği"),
    ("Ece", "Güneş", "Bilgisayar Mühendisliği"),
    ("Kaan", "Tekin", "Bilgisayar Mühendisliği"),
    ("Buse", "Kılıç", "Yazılım Mühendisliği"),
    ("Yusuf", "Aksoy", "Bilgisayar Mühendisliği"),
    ("Esra", "Şimşek", "Yazılım Mühendisliği"),
    ("Arda", "Karaca", "Bilgisayar Mühendisliği"),
    ("Gizem", "Uçar", "Yazılım Mühendisliği"),
    ("Hakan", "Bulut", "Bilgisayar Mühendisliği"),
    ("Nazlı", "Ekinci", "Yazılım Mühendisliği"),
    ("Onur", "Taş", "Bilgisayar Mühendisliği"),
    ("Pınar", "Acar", "Yazılım Mühendisliği"),
    ("Serkan", "Yavuz", "Bilgisayar Mühendisliği"),
    ("Tuğba", "Özkan", "Yazılım Mühendisliği"),
    ("Umut", "Sarı", "Bilgisayar Mühendisliği"),
    ("Yağmur", "Ateş", "Yazılım Mühendisliği"),
    ("Barış", "Kara", "Bilgisayar Mühendisliği"),
)

# Dönem -> (sınav türü, ağırlık, tarih)
EXAMS = {
    "2025-Güz": (("Vize", 40, "2025-11-12"), ("Ödev", 20, "2025-12-10"),
                 ("Final", 60, "2026-01-14")),
    "2026-Bahar": (("Vize", 40, "2026-04-08"), ("Ödev", 20, "2026-05-13"),
                   ("Final", 60, "2026-06-10")),
}

_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def _email(first: str, last: str) -> str:
    return f"{first}.{last}".lower().translate(_TR) + "@ogrenci.okul.edu.tr"


def _students():
    """(kullanıcı adı, öğrenci no, ad, soyad, bölüm, sınıf)"""
    rows = []
    for index, (first, last, department) in enumerate(STUDENT_NAMES, start=1):
        level = 2 if index <= 15 else 3
        number = f"{2026 - level}{index:03d}"  # 2024001..., 2023016...
        rows.append((f"ogrenci{index}", number, first, last, department, level))
    return rows


def is_demo(db: Database) -> bool:
    return db.get_meta(DEMO_FLAG) == "1"


def has_any_data(db: Database) -> bool:
    return bool(db.query_one(
        "SELECT (SELECT COUNT(*) FROM students) + (SELECT COUNT(*) FROM courses) "
        "+ (SELECT COUNT(*) FROM users) AS total"
    )["total"])


def load_demo_data(db: Database) -> int:
    """Demo veri setini yükler; eklenen kayıt sayısını döndürür.

    Zaten demo veritabanıysa hiçbir şeye dokunmaz (0 döner): kullanıcının test
    sırasında eklediği/düzenlediği veriler korunur. Gerçek veri içeren bir
    veritabanına yükleme reddedilir.
    """
    if is_demo(db):
        return 0
    if has_any_data(db):
        raise ValidationError(
            "Demo verileri yalnızca boş, ayrı bir veritabanına yüklenebilir "
            "(örn. data/demo.db). Bu veritabanında kayıtlı veriler var."
        )
    rng = random.Random(2026)
    teachers = _demo_teachers(db)
    courses = _demo_courses(db, teachers)
    accounts, students = _demo_students(db)
    inserted = len(teachers) + len(courses) + 2 * len(students)
    inserted += _demo_grades(db, rng, courses, students)
    inserted += _demo_messages(db, rng, teachers, courses, accounts)
    db.set_meta(DEMO_FLAG, "1")
    return inserted


def reset_demo_database(path) -> Database:
    """Demo veritabanı dosyasını silip yeniden oluşturur ve doldurur.

    Dosya demo değilse ve içinde veri varsa (gerçek veri olabilir) reddedilir.
    """
    target = Path(path)
    if target.is_file():
        existing = Database(target)
        try:
            if not is_demo(existing) and has_any_data(existing):
                raise ValidationError(
                    "Bu dosya bir demo veritabanı değil ve veri içeriyor; sıfırlanmadı.")
        finally:
            existing.close()
        for suffix in ("", "-wal", "-shm", "-journal"):
            candidate = Path(str(target) + suffix)
            if candidate.exists():
                candidate.unlink()
    db = Database(target)
    load_demo_data(db)
    return db


# ----------------------------------------------------------------- oluşturma
def _demo_teachers(db) -> dict:
    auth = AuthService(db)
    return {
        username: auth.create_teacher(username, full_name, DEMO_PASSWORD,
                                      enforce_policy=False)
        for username, full_name, _ in TEACHERS
    }


def _demo_courses(db, teachers) -> list:
    """(Course, sınıf düzeyi, zorluk) listesi."""
    service = CourseService(db)
    titles = {username: title for username, _, title in TEACHERS}
    rows = []
    for code, name, credit, semester, owner, level, difficulty in COURSES:
        course = service.add(code, name, credit, titles[owner], semester,
                             teacher_id=teachers[owner].id)
        rows.append((course, level, difficulty))
    return rows


def _demo_students(db) -> tuple[dict, list]:
    """Öğrenciler ve portal hesapları. (hesaplar {kullanıcı adı: User}, öğrenciler)"""
    students_service, auth = StudentService(db), AuthService(db)
    accounts, students = {}, []
    for username, number, first, last, department, level in _students():
        student = students_service.add(number, first, last, department,
                                       _email(first, last), level)
        accounts[username] = auth.set_student_password(
            student.id, DEMO_PASSWORD, username=username, enforce_policy=False)
        students.append(student)
    return accounts, students


def _demo_grades(db, rng, courses, students) -> int:
    """Kayıtlar ve notlar: her öğrenci kendi sınıf düzeyinin 4 dersine kayıtlıdır.

    Öğrenci başarısı ve ders zorluğu birleştirilir; notların yaklaşık %5'i eksiktir
    (ör. finale girmemiş ya da ödev teslim etmemiş öğrenci).
    """
    enrollments, grades = [], []
    for student in students:
        ability = rng.choice((38, 48, 55, 62, 68, 74, 80, 86, 92)) + rng.randint(-4, 4)
        for course, level, difficulty in courses:
            if level != student.class_year:
                continue
            enrollments.append((student.id, course.id))
            for exam, weight, exam_date in EXAMS[course.semester]:
                if rng.random() < 0.05:
                    continue  # eksik not
                score = ability + difficulty + rng.randint(-12, 12)
                if exam == "Ödev":
                    score += 6  # ödevler genelde biraz daha yüksek
                grades.append((student.id, course.id, exam, max(0, min(100, score)),
                               weight, exam_date))
    with db.cursor() as cur:
        cur.executemany(
            "INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)", enrollments)
        cur.executemany(
            "INSERT INTO grades (student_id, course_id, exam_type, score, weight, exam_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            grades,
        )
    return len(enrollments) + len(grades)


STUDENT_QUESTIONS = (
    ("Vize notu hakkında", "Hocam merhaba, vize sınavındaki ikinci sorunun puanlamasını "
                           "görüşmek istiyorum. Uygun olduğunuz bir saat var mı?"),
    ("Ödev teslim tarihi", "Hocam, ödevin teslim tarihini bir gün uzatma imkânı var mı? "
                           "Aynı hafta iki sınavım çakışıyor."),
    ("Final kapsamı", "Hocam, final sınavı dönemin tüm konularını mı kapsayacak?"),
    ("Proje grubu", "Hocam, proje grubumuza bir arkadaşımızı daha ekleyebilir miyiz?"),
    ("Devamsızlık durumu", "Hocam, sağlık raporum nedeniyle geçen haftaki derse "
                           "katılamadım. Raporu nasıl iletmeliyim?"),
    ("Ders notları", "Hocam, geçen haftaki dersin sunumunu sisteme yükleyebilir misiniz?"),
    ("Ofis saati", "Hocam, bu hafta ofis saatinizde konuyu tekrar sormak için "
                   "gelebilir miyim?"),
    ("Bütünleme sınavı", "Hocam, bütünleme sınavının tarihi belli oldu mu?"),
    ("Staj belgesi", "Hocam, staj başvurum için ders başarı belgesine ihtiyacım var."),
)

TEACHER_REPLIES = (
    "Merhaba, Perşembe 13.30'da ofisime gelebilirsin.",
    "Teslim tarihini bir gün uzatıyorum; sisteme Cuma 17.00'ye kadar yükleyebilirsin.",
    "Evet, final dönemin tüm konularını kapsayacak; özellikle son üç haftaya ağırlık ver.",
    "Uygundur, grup listesini güncelleyip bana iletin.",
    "Raporunu öğrenci işlerine teslim etmen yeterli, ben de not aldım.",
    "Sunumu bu akşam sisteme yükleyeceğim.",
)


def _demo_messages(db, rng, teachers, courses, accounts) -> int:
    """Yaklaşık 40 mesaj: duyurular, öğrenci soruları, yanıtlar ve bireysel mesajlar.

    Tarihler 2026 Eylül-Kasım arasına yayılır; eski mesajların çoğu okunmuş,
    son mesajların bir kısmı okunmamıştır.
    """
    service = MessageService(db)
    script = _announcements(service, teachers, courses)
    questions, question_script = _student_questions(service, accounts)
    script += question_script
    ids = []
    for send, day in script:
        message_id = send()
        _set_date(db, message_id,
                  f"{day} {rng.randint(8, 18):02d}:{rng.randint(0, 59):02d}:00")
        ids.append(message_id)
    ids += _replies(db, service, questions, ids[-len(questions):])
    ids += _direct_messages(db, service, accounts)
    _mark_read(db, rng)
    return len(ids)


def _set_date(db, message_id, created_at) -> None:
    db.run("UPDATE messages SET created_at = ? WHERE id = ?", (created_at, message_id))


def _announcements(service, teachers, courses) -> list:
    """Her dersin duyurusu ve iki sınıf duyurusu: (gönderme işlevi, gün)."""
    by_id = {user.id: user for user in teachers.values()}
    script = []
    for index, (course, _, _) in enumerate(courses):
        teacher = by_id[course.teacher_id]
        script.append((lambda t=teacher, c=course: service.send_to_course(
            t, c.id, f"{c.name}: dönem duyurusu",
            f"Sevgili öğrenciler, {c.name} dersinin not dökümü sisteme girilmiştir. "
            "İtirazlarınızı bir hafta içinde iletebilirsiniz."), f"2026-09-{15 + index:02d}"))
    script.append((lambda: service.send_to_class(
        teachers["ogretmen2"], 2, "2. sınıf danışmanlık toplantısı",
        "2. sınıf öğrencilerimizle danışmanlık toplantısı Çarşamba 14.00'te B-204 "
        "numaralı derslikte yapılacaktır."), "2026-09-28"))
    script.append((lambda: service.send_to_class(
        teachers["ogretmen3"], 3, "Bitirme projesi konuları",
        "3. sınıf öğrencileri için bitirme projesi konu listesi yayımlanmıştır. "
        "Tercihlerinizi ay sonuna kadar iletiniz."), "2026-10-02"))
    return script


def _student_questions(service, accounts) -> tuple[list, list]:
    """18 öğrenci sorusu (öğrenci yalnızca kendi öğretmenine yazar)."""
    students = list(accounts.values())
    questions, script = [], []
    for index in range(18):
        student = students[(index * 7) % len(students)]
        own_teachers = service.teachers_of_student(student.student_id)
        teacher = own_teachers[index % len(own_teachers)]
        subject, body = STUDENT_QUESTIONS[index % len(STUDENT_QUESTIONS)]
        day = 5 + index * 3
        questions.append(teacher)
        script.append((lambda s=student, t=teacher, su=subject, b=body:
                       service.send_to_teacher(s, t.id, su, b),
                       f"2026-{10 + day // 31:02d}-{day % 31 + 1:02d}"))
    return questions, script


def _replies(db, service, questions, question_ids) -> list:
    """İlk 10 soru, öğretmen tarafından 5 saat sonra yanıtlanmış."""
    ids = []
    for index in range(10):
        reply = service.reply(questions[index], question_ids[index],
                              TEACHER_REPLIES[index % len(TEACHER_REPLIES)])
        db.run("UPDATE messages SET created_at = datetime("
               "(SELECT created_at FROM messages WHERE id = ?), '+5 hours') WHERE id = ?",
               (question_ids[index], reply))
        ids.append(reply)
    return ids


def _direct_messages(db, service, accounts) -> list:
    ids = []
    for index, username in enumerate(("ogrenci3", "ogrenci11", "ogrenci19", "ogrenci27")):
        student = accounts[username]
        teacher = service.teachers_of_student(student.student_id)[0]
        message_id = service.send_to_student(
            teacher, student.student_id, "Ödev geri bildirimi",
            "Ödevini inceledim; kaynakça bölümünü düzenleyip yeniden yüklemeni rica ederim.")
        _set_date(db, message_id, f"2026-11-{18 + index:02d} 10:30:00")
        ids.append(message_id)
    return ids


def _mark_read(db, rng) -> None:
    """20 Kasım'dan önceki mesajların ~%80'i okunmuş; sonrakiler okunmamış."""
    for row in db.query(
            "SELECT r.message_id, r.user_id, m.created_at FROM message_recipients r "
            "JOIN messages m ON m.id = r.message_id"):
        if row["created_at"] < "2026-11-20" and rng.random() < 0.8:
            db.run("UPDATE message_recipients SET read_at = datetime(?, '+1 day') "
                   "WHERE message_id = ? AND user_id = ?",
                   (row["created_at"], row["message_id"], row["user_id"]))


@dataclass(frozen=True)
class DemoAccount:
    """Giriş ekranındaki "Demo Hesapları" panelinde gösterilen bir hesap."""

    role: str  # "teacher" | "student"
    username: str
    password: str
    full_name: str

    @property
    def role_label(self) -> str:
        return "Öğretmen" if self.role == "teacher" else "Öğrenci"


PANEL_LIMITS = (("teacher", 4), ("student", 5))


def demo_accounts(db: Database) -> list[DemoAccount]:
    """Giriş ekranında gösterilecek demo hesapları, veritabanından okunur.

    Yalnızca demo veritabanında dolu döner. Her hesap için saklanan parola özeti
    demo şifresiyle doğrulanır; şifresi değiştirilmiş hesaplar gösterilmez, yerine
    sıradaki geçerli hesap gelir. Giriş yapılmaz (last_login değişmez).
    En fazla 4 öğretmen ve 5 öğrenci, oluşturulma sırasıyla döner.
    """
    if not is_demo(db):
        return []
    accounts = []
    for role, limit in PANEL_LIMITS:
        found = 0
        for row in db.query("SELECT username, password_hash, full_name FROM users "
                            "WHERE role = ? ORDER BY id", (role,)):
            if found == limit:
                break
            if verify_password(DEMO_PASSWORD, row["password_hash"]):
                accounts.append(DemoAccount(role, row["username"], DEMO_PASSWORD,
                                            row["full_name"]))
                found += 1
    return accounts
