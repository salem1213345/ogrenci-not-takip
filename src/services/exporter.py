"""PDF transkript ve CSV ders listesi (FR-09, FR-10)."""
import csv
from datetime import date
from pathlib import Path

from src.services import grade_calculator as calc

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/Library/Fonts/Arial.ttf",
]
FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def _register_fonts():
    """Turkce karakterler icin TTF yazi tipi kaydeder; bulunamazsa Helvetica."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    regular = next((p for p in FONT_CANDIDATES if Path(p).exists()), None)
    bold = next((p for p in FONT_BOLD_CANDIDATES if Path(p).exists()), None)
    if regular:
        pdfmetrics.registerFont(TTFont("AppFont", regular))
        pdfmetrics.registerFont(TTFont("AppFont-Bold", bold or regular))
        return "AppFont", "AppFont-Bold"
    return "Helvetica", "Helvetica-Bold"


class ReportExporter:
    def __init__(self, student_service, course_service, enrollment_service,
                 grade_service):
        self.students = student_service
        self.courses = course_service
        self.enrollments = enrollment_service
        self.grades = grade_service

    def transcript_rows(self, student_id):
        """(kod, ad, kredi, donem, ortalama, harf, durum) satirlari + GPA."""
        rows, gpa_items = [], []
        for enr_id, term, course in self.enrollments.list_by_student(student_id):
            r = self.grades.evaluate(enr_id, course)
            rows.append((course.code, course.name, course.credit, term,
                         r["average"], r["letter"], r["status"]))
            if r["coef"] is not None:
                gpa_items.append((r["coef"], course.credit))
        return rows, calc.calculate_gpa(gpa_items)

    def export_transcript_pdf(self, student_id, path):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                        Table, TableStyle)
        student = next((s for s in self.students.list_all()
                        if s.id == student_id), None)
        if student is None:
            raise ValueError("Öğrenci bulunamadı.")
        rows, gpa = self.transcript_rows(student_id)
        font, bold = _register_fonts()
        title = ParagraphStyle("t", fontName=bold, fontSize=16, spaceAfter=8)
        body = ParagraphStyle("b", fontName=font, fontSize=10, leading=14)
        doc = SimpleDocTemplate(str(path), pagesize=A4, title="Transkript")
        data = [["Kod", "Ders", "Kredi", "Dönem", "Ort.", "Harf", "Durum"]]
        for code, name, credit, term, avg, letter, status in rows:
            data.append([code, name, credit, term,
                         "-" if avg is None else f"{avg:.2f}", letter or "-",
                         status])
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("FONTNAME", (0, 0), (-1, 0), bold),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        doc.build([
            Paragraph("Öğrenci Transkripti", title),
            Paragraph(f"Öğrenci: {student.full_name()} ({student.student_no})", body),
            Paragraph(f"Tarih: {date.today().isoformat()}", body),
            Spacer(1, 12), table, Spacer(1, 12),
            Paragraph(f"Genel ortalama (GPA): {gpa:.2f}", body),
        ])
        return Path(path)

    def export_course_csv(self, course_id, path, term=None):
        course = next((c for c in self.courses.list_all() if c.id == course_id),
                      None)
        if course is None:
            raise ValueError("Ders bulunamadı.")
        header = ["ogrenci_no", "ad", "soyad", "vize", "final", "odev",
                  "ortalama", "harf", "durum"]
        # utf-8-sig: Excel'de Turkce karakterler dogru acilir
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            for enr_id, _term, s in self.enrollments.list_by_course(course_id, term):
                r = self.grades.evaluate(enr_id, course)
                fmt = lambda v: "" if v is None else v  # noqa: E731
                w.writerow([s.student_no, s.first_name, s.last_name,
                            fmt(r["midterm"]), fmt(r["final"]),
                            fmt(r["assignment"]),
                            "" if r["average"] is None else f"{r['average']:.2f}",
                            fmt(r["letter"]), r["status"]])
        return Path(path)
