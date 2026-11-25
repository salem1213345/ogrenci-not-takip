"""CSV ve PDF rapor üretimi."""

import csv
from datetime import date
from pathlib import Path

from fpdf import FPDF

from app import config
from app.grading import format_score
from app.models import ClassSummary, Student, StudentReport
from app.services.grade_service import GradeService
from app.services.student_service import StudentService

_TRANSLATION = str.maketrans(
    {
        "ı": "i",
        "İ": "I",
        "ş": "s",
        "Ş": "S",
        "ğ": "g",
        "Ğ": "G",
        "ç": "c",
        "Ç": "C",
        "ö": "o",
        "Ö": "O",
        "ü": "u",
        "Ü": "U",
    }
)

# Türkçe karakterleri destekleyen ilk bulunan sistem fontu kullanılır.
_FONT_CANDIDATES = (
    ("Arial", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("SegoeUI", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    (
        "DejaVu",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    (
        "Liberation",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
)


def _resolve_font() -> tuple[str, str | None, str | None]:
    for family, regular, bold in _FONT_CANDIDATES:
        if Path(regular).is_file():
            return family, regular, bold if Path(bold).is_file() else regular
    return "Helvetica", None, None


FONT_FAMILY, FONT_REGULAR, FONT_BOLD = _resolve_font()


def _ensure_parent(path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# Excel/LibreOffice bu karakterlerle başlayan hücreleri formül olarak çalıştırır
# (CSV formül enjeksiyonu). Böyle hücrelerin başına ' eklenerek düz metin yapılır.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value):
    if isinstance(value, str) and len(value) > 1 and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


class _SafeCsvWriter:
    """csv.writer sarmalayıcısı: her hücreyi formül enjeksiyonuna karşı temizler."""

    def __init__(self, handle):
        self._writer = csv.writer(handle, delimiter=config.CSV_DELIMITER)

    def writerow(self, row) -> None:
        self._writer.writerow([_csv_safe(value) for value in row])


def _shorten(value, width: float, font_size: float = 9.0) -> str:
    text = str(value)
    limit = max(4, int(width / (font_size * 0.18)))
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


class ReportPDF(FPDF):
    """Ortak başlık/alt bilgi ve Türkçe metin desteği olan PDF sınıfı."""

    def __init__(self, title: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report_title = title
        self.unicode_font = FONT_REGULAR is not None
        self.set_margins(12, 14, 12)
        self.set_auto_page_break(True, margin=18)
        if self.unicode_font:
            self.add_font(FONT_FAMILY, "", FONT_REGULAR)
            if FONT_BOLD and FONT_BOLD != FONT_REGULAR:
                self.add_font(FONT_FAMILY, "B", FONT_BOLD)
        self.set_title(title)
        self.set_author(config.APP_NAME)
        self.alias_nb_pages()

    def s(self, value) -> str:
        """Unicode font yoksa metni latin-1 uyumlu hale getirir."""
        text = str(value)
        return text if self.unicode_font else text.translate(_TRANSLATION)

    def header(self) -> None:
        self.set_font(FONT_FAMILY, "B", 15)
        self.set_text_color(31, 41, 55)
        self.cell(0, 10, self.s(self.report_title), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font(FONT_FAMILY, "", 9)
        self.set_text_color(107, 114, 128)
        self.cell(
            0,
            5,
            self.s(f"{config.APP_NAME} - {date.today():%d.%m.%Y}"),
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_text_color(31, 41, 55)
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font(FONT_FAMILY, "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, self.s(f"Sayfa {self.page_no()}/{{nb}}"), align="C")


def _draw_table(pdf: ReportPDF, headers, rows, widths, aligns) -> None:
    pdf.set_font(FONT_FAMILY, "B", 9)
    pdf.set_fill_color(232, 238, 251)
    pdf.set_draw_color(203, 213, 225)
    for header, width in zip(headers, widths):
        pdf.cell(width, 9, pdf.s(header), border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font(FONT_FAMILY, "", 9)
    for index, row in enumerate(rows):
        if index % 2 == 0:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        for value, width, align in zip(row, widths, aligns):
            text = _shorten(value, width)
            pdf.cell(width, 8, pdf.s(text), border=1, align=align, fill=True)
        pdf.ln()


def _draw_section_title(pdf: ReportPDF, title: str) -> None:
    pdf.ln(3)
    pdf.set_font(FONT_FAMILY, "B", 11)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 8, pdf.s(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(31, 41, 55)


def _draw_student_info(pdf: ReportPDF, student: Student) -> None:
    rows = (
        ("Öğrenci No", student.student_no),
        ("Ad Soyad", student.full_name),
        ("Bölüm", student.department or "-"),
        ("E-posta", student.email or "-"),
    )
    for label, value in rows:
        pdf.set_font(FONT_FAMILY, "B", 10)
        pdf.cell(32, 7, pdf.s(label))
        pdf.set_font(FONT_FAMILY, "", 10)
        pdf.cell(0, 7, pdf.s(value), new_x="LMARGIN", new_y="NEXT")


def _student_rows(report: StudentReport) -> list[list]:
    rows = [
        [
            course.course_code,
            course.course_name,
            course.credit,
            format_score(course.average),
            course.letter,
            course.status,
        ]
        for course in report.courses
    ]
    if not rows:
        rows = [["-", "Henüz not girilmemiş", "-", "-", "-", "Not yok"]]
    return rows


def _draw_student_summary(pdf: ReportPDF, report: StudentReport) -> None:
    _draw_section_title(pdf, "Özet")
    pdf.set_font(FONT_FAMILY, "", 10)
    text = (
        f"GNO: {format_score(report.gpa)}    "
        f"Toplam Kredi: {report.total_credit}    "
        f"Kalan Ders: {report.failed_count}    "
        f"Durum: {report.status}"
    )
    pdf.multi_cell(0, 7, pdf.s(text))
    pdf.ln(2)


class ReportService:
    """Karne ve sınıf raporlarını dosyaya yazar."""

    def __init__(self, student_service: StudentService, grade_service: GradeService):
        self.students = student_service
        self.grades = grade_service

    # ------------------------------------------------------------------- CSV
    def student_csv(self, student_id, path) -> Path:
        report = self.grades.student_report(student_id)
        target = _ensure_parent(Path(path))
        with target.open("w", newline="", encoding=config.CSV_ENCODING) as handle:
            writer = _SafeCsvWriter(handle)
            student = report.student
            writer.writerow(["Öğrenci No", student.student_no])
            writer.writerow(["Ad Soyad", student.full_name])
            writer.writerow(["Bölüm", student.department])
            writer.writerow(["E-posta", student.email])
            writer.writerow(["GNO", format_score(report.gpa)])
            writer.writerow(["Durum", report.status])
            writer.writerow([])
            writer.writerow(
                ["Ders Kodu", "Ders Adı", "Kredi", "Ağırlıklı Ortalama", "Harf Notu", "Durum"]
            )
            for course in report.courses:
                writer.writerow(
                    [
                        course.course_code,
                        course.course_name,
                        course.credit,
                        format_score(course.average),
                        course.letter,
                        course.status,
                    ]
                )
        return target

    def class_csv(self, path) -> Path:
        summaries = self.grades.class_summary()
        target = _ensure_parent(Path(path))
        with target.open("w", newline="", encoding=config.CSV_ENCODING) as handle:
            writer = _SafeCsvWriter(handle)
            writer.writerow(
                ["Öğrenci No", "Ad Soyad", "Bölüm", "Ders Sayısı", "GNO", "Kalan Ders", "Durum"]
            )
            for row in summaries:
                writer.writerow(
                    [
                        row.student_no,
                        row.full_name,
                        row.department,
                        row.course_count,
                        format_score(row.gpa),
                        row.failed_count,
                        row.status,
                    ]
                )
        return target

    # ------------------------------------------------------------------- PDF
    def student_pdf(self, student_id, path) -> Path:
        report = self.grades.student_report(student_id)
        target = _ensure_parent(Path(path))
        pdf = ReportPDF("Öğrenci Not Raporu")
        pdf.add_page()
        _draw_student_info(pdf, report.student)
        _draw_section_title(pdf, "Ders Bazlı Sonuçlar")
        _draw_table(
            pdf,
            ("Kod", "Ders Adı", "Kredi", "Ortalama", "Harf", "Durum"),
            _student_rows(report),
            (22, 62, 16, 30, 20, 36),
            ("C", "L", "C", "C", "C", "C"),
        )
        _draw_student_summary(pdf, report)
        pdf.output(str(target))
        return target

    def class_pdf(self, path) -> Path:
        summaries = self.grades.class_summary()
        target = _ensure_parent(Path(path))
        pdf = ReportPDF("Sınıf Not Özeti")
        pdf.add_page()
        _draw_section_title(pdf, "Öğrenci Özetleri")
        rows = [
            [
                row.student_no,
                row.full_name,
                row.department or "-",
                row.course_count,
                format_score(row.gpa),
                row.status,
            ]
            for row in summaries
        ]
        if not rows:
            rows = [["-", "Kayıtlı öğrenci yok", "-", "-", "-", "-"]]
        _draw_table(
            pdf,
            ("No", "Ad Soyad", "Bölüm", "Ders", "GNO", "Durum"),
            rows,
            (28, 56, 50, 16, 20, 16),
            ("C", "L", "L", "C", "C", "C"),
        )
        pdf.ln(6)
        pdf.set_font(FONT_FAMILY, "", 10)
        pdf.multi_cell(0, 7, pdf.s(f"Toplam öğrenci: {len(summaries)}"))
        pdf.output(str(target))
        return target

    # ------------------------------------------------------------- önizleme
    def student_preview(self, student_id) -> str:
        report = self.grades.student_report(student_id)
        student = report.student
        lines = [
            "ÖĞRENCİ KARNESİ",
            "=" * 92,
            f"Öğrenci No : {student.student_no}",
            f"Ad Soyad   : {student.full_name}",
            f"Bölüm      : {student.department or '-'}",
            f"E-posta    : {student.email or '-'}",
            "",
            f"{'Kod':<10}{'Ders Adı':<38}{'Kredi':>6}{'Ortalama':>10}{'Harf':>7}{'Durum':>9}",
            "-" * 92,
        ]
        for course in report.courses:
            name = course.course_name[:36]
            lines.append(
                f"{course.course_code:<10}{name:<38}{course.credit:>6}"
                f"{format_score(course.average):>10}{course.letter:>7}{course.status:>9}"
            )
        if not report.courses:
            lines.append("Henüz not girilmemiş.")
        lines.extend(
            [
                "-" * 92,
                "",
                f"GNO: {format_score(report.gpa)}   "
                f"Toplam Kredi: {report.total_credit}   "
                f"Durum: {report.status}",
            ]
        )
        return "\n".join(lines)

    def class_preview(self) -> str:
        summaries: list[ClassSummary] = self.grades.class_summary()
        lines = [
            "SINIF NOT ÖZETİ",
            "=" * 96,
            f"{'No':<12}{'Ad Soyad':<26}{'Bölüm':<32}{'Ders':>5}{'GNO':>8}{'Durum':>13}",
            "-" * 96,
        ]
        for row in summaries:
            name = row.full_name[:24]
            department = (row.department or "-")[:30]
            lines.append(
                f"{row.student_no:<12}{name:<26}{department:<32}"
                f"{row.course_count:>5}{format_score(row.gpa):>8}{row.status:>13}"
            )
        if not summaries:
            lines.append("Henüz kayıtlı öğrenci yok.")
        lines.extend(["-" * 96, "", f"Toplam öğrenci: {len(summaries)}"])
        return "\n".join(lines)
