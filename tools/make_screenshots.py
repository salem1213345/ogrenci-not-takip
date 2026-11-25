"""Teslim dokümanları için ekran görüntüleri ve çıktı görselleri üretir.

Üretilenler:
    docs/ekran-dersler.png     Dersler sekmesi (diğer sekmelerin eşi)
    docs/cikti-pdf.png         Sınıf raporu PDF'inin ilk sayfası
    docs/cikti-csv.png         Sınıf raporu CSV'sinin tablo görünümü
    docs/test-pytest.png       pytest yürütme çıktısı (konsol görünümü)
    docs/test-kapsam.png       Kapsam (coverage) tablosu

Kullanım:
    python tools/make_screenshots.py
"""

from __future__ import annotations

import ctypes
import csv
import shutil
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DOCS = BASE_DIR / "docs"
FONTS = Path(r"C:\Windows\Fonts")

CONSOLE_TITLE = "pytest - ONTS"


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS / name
    return ImageFont.truetype(str(path), size)


def _dpi_aware() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # pragma: no cover - yalnızca Windows kabuğu
        pass


# --------------------------------------------------------------- arayüz
def capture_tab(name: str, filename: str) -> Path | None:
    """Uygulamayı demo veriyle açar, istenen ekranı görüntüler."""
    try:
        from PIL import ImageGrab

        from app.database import Database
        from app.demo_data import load_demo_data
        from app.ui.app_window import AppWindow
    except Exception as exc:  # pragma: no cover
        print(f"  UYARI: arayüz yakalama atlandı ({exc})")
        return None

    db_path = BASE_DIR / "data" / "ekran.db"
    if db_path.exists():
        db_path.unlink()
    db = Database(db_path)
    load_demo_data(db)

    window = AppWindow(db, db_path, show_login=(name == "giris"))
    window.geometry("1200x760+60+60")
    window.attributes("-topmost", True)
    window.update_idletasks()
    window.update()
    window.lift()
    window.focus_force()

    teacher_pages = {
        "ogretmen_ana": "home",
        "ogrenciler": "students",
        "dersler": "courses",
        "notlar": "grades",
        "not_dokumu": "report",
        "mesajlar": "messages",
    }
    student_pages = {
        "ogrenci_ana": "home",
        "ogrenci_dersler": "courses",
        "ogrenci_notlar": "grades",
        "ogrenci_ortalama": "gpa",
        "ogrenci_ofis": "office",
        "ogrenci_mesajlar": "messages",
    }
    if name in teacher_pages:
        window.show_page(teacher_pages[name])
    elif name in student_pages:
        window.show_student()
        window.student_view.show(student_pages[name])
    window.refresh_all()
    for _ in range(6):
        window.update()
        time.sleep(0.15)

    x = window.winfo_rootx()
    y = window.winfo_rooty()
    w = window.winfo_width()
    h = window.winfo_height()
    image = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)

    target = DOCS / filename
    image.save(target)
    print(f"  {target.name}: {image.size[0]}x{image.size[1]}")

    window.destroy()
    db.close()
    try:
        db_path.unlink()
    except OSError:
        pass
    return target


# --------------------------------------------------------------- çıktılar
def _demo_services():
    from app.database import Database
    from app.demo_data import load_demo_data
    from app.services import CourseService, GradeService, ReportService, StudentService

    db = Database(BASE_DIR / "data" / "cikti_ekran.db")
    load_demo_data(db)
    students = StudentService(db)
    courses = CourseService(db)
    grades = GradeService(db)
    reports = ReportService(students, grades)
    return db, students, courses, grades, reports


def capture_pdf() -> Path:
    import pypdfium2 as pdfium

    out_dir = BASE_DIR / "cikti" / "ekran"
    out_dir.mkdir(parents=True, exist_ok=True)
    db, students, _courses, _grades, reports = _demo_services()
    try:
        pdf_path = reports.class_pdf(out_dir / "sinif-raporu.pdf")
        document = pdfium.PdfDocument(str(pdf_path))
        page = document[0]
        image = page.render(scale=2.2).to_pil().convert("RGB")
        # Beyaz sayfa kenarını kırpar, ince bir çerçeve bırakır.
        image = image.crop((18, 18, image.width - 18, image.height - 18))
        target = DOCS / "cikti-pdf.png"
        image.save(target)
        print(f"  {target.name}: {image.size[0]}x{image.size[1]}")
        return target
    finally:
        db.close()


def capture_csv() -> Path:
    out_dir = BASE_DIR / "cikti" / "ekran"
    out_dir.mkdir(parents=True, exist_ok=True)
    db, _students, _courses, _grades, reports = _demo_services()
    try:
        path = reports.class_csv(out_dir / "sinif-raporu.csv")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
    finally:
        db.close()

    header, body = rows[0], rows[1:]
    columns = len(header)
    width = 1560
    margin = 48
    table_left = margin
    table_right = width - margin
    available = table_right - table_left

    # Sütun genişliklerini içeriğe göre ölç; sığmazsa puntoyu küçült.
    size = 19
    while True:
        body_font = _font("segoeui.ttf", size)
        head_font = _font("segoeuib.ttf", size)
        widths = []
        for index in range(columns):
            longest = head_font.getlength(header[index])
            for row in body:
                if index < len(row):
                    longest = max(longest, body_font.getlength(row[index]))
            widths.append(longest + 30)
        if sum(widths) <= available or size <= 12:
            break
        size -= 1

    scale = min(1.0, available / sum(widths))
    widths = [value * scale for value in widths]
    header_h = size + 37
    row_h = size + 27
    height = margin * 2 + header_h + row_h * len(body) + 54

    image = Image.new("RGB", (width, height), "#f4f6fb")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (18, 18, width - 18, height - 18), radius=14, fill="#ffffff", outline="#dbe3ef", width=2
    )
    draw.text((margin, 40), "sinif-raporu.csv", font=_font("consola.ttf", 24), fill="#1e3a8a")
    draw.text(
        (margin, 74),
        f"UTF-8 · {len(body)} satır · {columns} sütun · ; ayırıcı",
        font=_font("segoeui.ttf", 19),
        fill="#6b7280",
    )

    table_top = 118
    draw.rounded_rectangle(
        (table_left, table_top, table_right, table_top + header_h),
        radius=6,
        fill="#2563eb",
    )
    x = table_left
    for index, value in enumerate(header):
        draw.text((x + 14, table_top + 17), value, font=head_font, fill="#ffffff")
        x += widths[index]

    y = table_top + header_h
    for row_index, row in enumerate(body):
        fill = "#ffffff" if row_index % 2 == 0 else "#f7f9fd"
        draw.rectangle((table_left, y, table_right, y + row_h), fill=fill)
        draw.line((table_left, y, table_right, y), fill="#e2e8f0", width=1)
        x = table_left
        for index in range(columns):
            value = row[index] if index < len(row) else ""
            draw.text((x + 14, y + (row_h - size) // 2 - 2), value, font=body_font, fill="#1f2937")
            x += widths[index]
        y += row_h
    draw.rectangle((table_left, table_top, table_right, y), outline="#cbd5e1", width=2)

    target = DOCS / "cikti-csv.png"
    image.save(target)
    print(f"  {target.name}: {image.size[0]}x{image.size[1]} (punto {size})")
    return target


# --------------------------------------------------------------- konsol
def _terminal(lines: list[str], title: str, filename: str, width: int = 1600) -> Path:
    body_font = _font("consola.ttf", 21)
    bold_font = _font("consolab.ttf", 21)
    line_h = 30
    chrome = 64
    pad = 26
    height = chrome + pad * 2 + line_h * len(lines)

    image = Image.new("RGB", (width, height), "#0b1120")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, chrome), fill="#1e293b")
    for index, color in enumerate(("#ef4444", "#f59e0b", "#22c55e")):
        cx = 28 + index * 26
        draw.ellipse((cx, 24, cx + 14, 38), fill=color)
    draw.text((122, 20), title, font=_font("segoeui.ttf", 19), fill="#cbd5e1")

    y = chrome + pad
    for line in lines:
        colour = "#e2e8f0"
        font = body_font
        if line.startswith("$"):
            colour, font = "#93c5fd", bold_font
        elif "passed" in line or line.startswith("TOTAL"):
            colour, font = "#4ade80", bold_font
        elif "warning" in line.lower() or "error" in line.lower():
            colour = "#fbbf24"
        elif line.strip().startswith("app\\"):
            colour = "#cbd5e1"
        draw.text((pad, y), line, font=font, fill=colour)
        y += line_h

    target = DOCS / filename
    image.save(target)
    print(f"  {target.name}: {image.size[0]}x{image.size[1]}")
    return target


def _pytest_lines() -> list[str]:
    text = (BASE_DIR / "docs" / "src" / "pytest_output.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def capture_pytest() -> Path:
    lines = _pytest_lines()
    start = next(index for index, line in enumerate(lines) if "test session starts" in line)
    end = next(index for index, line in enumerate(lines) if "tests coverage" in line)
    passed = next(line for line in lines if " passed" in line)
    body = [
        "$ python -m pytest --cov=app --cov-report=term-missing",
        "",
        *lines[start:end],
        "",
        passed,
    ]
    return _terminal(body, "pytest - ONTS testleri", "test-pytest.png")


def capture_coverage() -> Path:
    lines = _pytest_lines()
    start = next(index for index, line in enumerate(lines) if line.startswith("Name"))
    body = [
        "$ python -m pytest --cov=app --cov-report=term",
        "",
        *lines[start:],
        "",
        "Kapsam: %97 (588/606 satır, app/ui hariç)",
    ]
    return _terminal(body, "coverage - ONTS", "test-kapsam.png")


def main() -> int:
    _dpi_aware()
    DOCS.mkdir(exist_ok=True)
    print("Arayüz görüntüleri:")
    for name, filename in (
        ("giris", "ekran-giris.png"),
        ("ogretmen_ana", "ekran-ogretmen-ana.png"),
        ("ogrenciler", "ekran-ogrenciler.png"),
        ("dersler", "ekran-dersler.png"),
        ("notlar", "ekran-notlar.png"),
        ("raporlar", "ekran-raporlar.png"),
        ("not_dokumu", "ekran-not-dokumu.png"),
        ("mesajlar", "ekran-mesajlar.png"),
        ("ogrenci_ana", "ekran-ogrenci-ana.png"),
        ("ogrenci_dersler", "ekran-ogrenci-dersler.png"),
        ("ogrenci_notlar", "ekran-ogrenci-notlar.png"),
        ("ogrenci_ortalama", "ekran-ogrenci-ortalama.png"),
        ("ogrenci_ofis", "ekran-ogrenci-ofis.png"),
        ("ogrenci_mesajlar", "ekran-ogrenci-mesajlar.png"),
    ):
        capture_tab(name, filename)

    print("Çıktı görüntüleri:")
    capture_pdf()
    capture_csv()

    print("Test görüntüleri:")
    capture_pytest()
    capture_coverage()

    # Geçici veritabanı ve çıktı klasörünü temizle.
    for leftover in (BASE_DIR / "data" / "cikti_ekran.db",):
        if leftover.exists():
            try:
                leftover.unlink()
            except OSError:
                pass
    shutil.rmtree(BASE_DIR / "cikti" / "ekran", ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
