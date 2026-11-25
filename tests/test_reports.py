"""PDF ve CSV rapor testleri."""

import csv

from app.services.report_service import ReportService


def _read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle, delimiter=";"))


def test_student_csv_content(report_service, sample, tmp_path):
    path = report_service.student_csv(sample.student.id, tmp_path / "karne.csv")
    assert path.exists()
    rows = _read_csv(path)
    assert rows[0] == ["Öğrenci No", "2026001"]
    assert rows[1] == ["Ad Soyad", "Elif Yılmaz"]
    headers = ["Ders Kodu", "Ders Adı", "Kredi", "Ağırlıklı Ortalama", "Harf Notu", "Durum"]
    assert rows[7] == headers
    assert rows[8][0] == "BIL101"
    assert rows[8][3] == "68.00"
    assert rows[8][4] == "DC"
    assert rows[9][0] == "MAT101"
    assert rows[9][4] == "AA"


def test_class_csv_content(report_service, sample, tmp_path):
    path = report_service.class_csv(tmp_path / "sinif.csv")
    rows = _read_csv(path)
    assert rows[0][0] == "Öğrenci No"
    assert rows[1][0] == "2026001"
    assert rows[1][3] == "2"
    assert rows[1][4] == "2.75"
    assert rows[1][6] == "Geçti"


def test_student_pdf_created(report_service, sample, tmp_path):
    path = report_service.student_pdf(sample.student.id, tmp_path / "karne.pdf")
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


def test_class_pdf_created(report_service, sample, tmp_path):
    path = report_service.class_pdf(tmp_path / "sinif.pdf")
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


def test_export_creates_missing_directories(report_service, sample, tmp_path):
    target = tmp_path / "alt" / "klasor" / "karne.pdf"
    path = report_service.student_pdf(sample.student.id, target)
    assert path.exists()


def test_empty_class_exports(report_service, tmp_path):
    pdf_path = report_service.class_pdf(tmp_path / "bos.pdf")
    csv_path = report_service.class_csv(tmp_path / "bos.csv")
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert len(_read_csv(csv_path)) == 1


def test_previews_contain_expected_text(report_service, sample):
    student_preview = report_service.student_preview(sample.student.id)
    assert "Elif Yılmaz" in student_preview
    assert "BIL101" in student_preview
    assert "GNO: 2.75" in student_preview

    class_preview = report_service.class_preview()
    assert "SINIF NOT ÖZETİ" in class_preview
    assert "2026001" in class_preview


def test_report_service_uses_given_services(report_service, student_service, grade_service):
    assert isinstance(report_service, ReportService)
    assert report_service.students is student_service
    assert report_service.grades is grade_service


def test_csv_neutralizes_formula_injection(student_service, report_service, tmp_path):
    student_service.add("2026099", '=HYPERLINK("http://x","tikla")', "+Kaya", "@Bölüm")
    rows = _read_csv(report_service.class_csv(tmp_path / "sinif.csv"))
    row = next(r for r in rows if r[0] == "2026099")
    assert row[1] == "'=HYPERLINK(\"http://x\",\"tikla\") +Kaya"
    assert row[2] == "'@Bölüm"
    assert row[4] == "-"  # boş GNO yer tutucusu değişmez
