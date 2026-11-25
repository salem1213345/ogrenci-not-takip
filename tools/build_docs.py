"""Markdown kaynaklarından teslim PDF'lerini üretir.

Akış:
1. Markdown -> HTML (kapak, içindekiler, gövde).
2. Görseller base64 data URI olarak gömülür (Türkçe yol sorunu yaşanmaz).
3. HTML, Edge/Chrome headless ile A4 PDF'e yazdırılır.
4. pypdf + fpdf2 ile alt bilgi ve "Sayfa X / Y" eklenir (kapak hariç).

Kullanım:
    python tools/build_docs.py            # dört PDF + Project_Definition.txt
    python tools/build_docs.py --only Design_Doc
"""

from __future__ import annotations

import argparse
import base64
import io
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import markdown
from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "docs" / "src"
OUT_DIR = BASE_DIR / "docs" / "deliverables"
ICON_PATH = BASE_DIR / "assets" / "app_icon.png"

APP_NAME = "Öğrenci Not Takip Sistemi"
APP_VERSION = "1.0.0"
DOC_DATE = "31.10.2026"

TEAM = (
    "Abbas Jabbarli",
    "Salem Abdssalam S Shwaya",
    "Mostafa Ayman Atta Khalil Hussein",
)

BROWSERS = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)

FONT_CANDIDATES = (
    (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")),
    (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), None),
    (Path("/Library/Fonts/Arial.ttf"), None),
)

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml", ".gif": "image/gif"}


@dataclass(frozen=True)
class DocSpec:
    stem: str
    title: str
    subtitle: str
    status: str = "Teslim"


DOCS = (
    DocSpec(
        "Coding_Standards",
        "Kodlama Standartları",
        "Kod biçimi, adlandırma, test, veritabanı ve inceleme kuralları",
    ),
    DocSpec(
        "Requirement_Spec_Doc",
        "Gereksinim Şartnamesi",
        "İşlevsel/işlevsel olmayan gereksinimler, veri ve arayüz tasarımı",
    ),
    DocSpec(
        "Design_Doc",
        "Tasarım Dokümanı",
        "Mimari, ayrıntılı tasarım, veri modeli ve arayüz kararları",
    ),
    DocSpec(
        "Test_Results_Doc",
        "Test Sonuçları Dokümanı",
        "Test stratejisi, yürütme kayıtları, kapsam ve hata günlüğü",
    ),
)


CSS = """
@page {
    size: A4;
    margin: 20mm 16mm 20mm 16mm;
}

* {
    box-sizing: border-box;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}

html { font-size: 10pt; }

body {
    margin: 0;
    font-family: "Segoe UI", "Arial", "DejaVu Sans", sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #1f2937;
}

p { margin: 0 0 6pt; text-align: justify; orphans: 2; widows: 2; }

h1, h2, h3, h4 {
    font-family: "Segoe UI", "Arial", sans-serif;
    color: #1e3a8a;
    line-height: 1.25;
}

#content > h1 {
    font-size: 19pt;
    margin: 20pt 0 12pt;
    padding-bottom: 5pt;
    border-bottom: 2.5pt solid #2563eb;
    color: #1d4ed8;
    break-after: avoid;
}

#content > h1:first-of-type { margin-top: 0; }

h2 {
    font-size: 13pt;
    margin: 16pt 0 6pt;
    padding-left: 6pt;
    border-left: 4pt solid #93c5fd;
    break-after: avoid;
}

h3 {
    font-size: 11pt;
    margin: 12pt 0 4pt;
    color: #1e40af;
    break-after: avoid;
}

h4 { font-size: 10pt; margin: 10pt 0 3pt; color: #1e40af; break-after: avoid; }

ul, ol { margin: 0 0 6pt; padding-left: 18pt; }
li { margin-bottom: 2pt; }

strong { color: #111827; }

a { color: #1d4ed8; text-decoration: none; }

code {
    font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 8.6pt;
    background: #eef2ff;
    border-radius: 2pt;
    padding: 0.5pt 2pt;
    color: #312e81;
}

pre {
    background: #f8fafc;
    border: 0.6pt solid #dbe3ef;
    border-left: 3pt solid #2563eb;
    border-radius: 3pt;
    padding: 7pt 9pt;
    margin: 0 0 8pt;
    font-size: 8.2pt;
    line-height: 1.4;
    white-space: pre-wrap;
    word-break: break-word;
    break-inside: avoid;
    color: #0f172a;
}

pre code {
    background: transparent;
    padding: 0;
    font-size: 8.2pt;
    color: inherit;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 9pt;
    font-size: 8.8pt;
    line-height: 1.35;
}

thead { display: table-header-group; }
tr { break-inside: avoid; }

th, td {
    border: 0.6pt solid #cbd5e1;
    padding: 3.4pt 4.5pt;
    vertical-align: top;
    text-align: left;
    overflow-wrap: break-word;
}

th {
    background: #e8effc;
    color: #1e3a8a;
    font-weight: 600;
}

tbody tr:nth-child(even) td { background: #f7f9fd; }

blockquote {
    margin: 0 0 8pt;
    padding: 6pt 10pt;
    background: #eff6ff;
    border-left: 3pt solid #2563eb;
    color: #1e3a8a;
    font-style: italic;
}

img {
    display: block;
    max-width: 100%;
    max-height: 185mm;
    margin: 6pt auto 10pt;
    border: 0.6pt solid #dbe3ef;
    border-radius: 2pt;
}

hr { border: none; border-top: 0.8pt solid #dbe3ef; margin: 10pt 0; }

/* ---------------------------------------------------------------- kapak */
.cover {
    break-after: page;
    height: 256mm;
    border-top: 9mm solid #2563eb;
    padding: 14mm 10mm 0;
    position: relative;
}

.cover-brand {
    font-size: 9pt;
    letter-spacing: 0.8pt;
    text-transform: uppercase;
    color: #2563eb;
    font-weight: 600;
}

.cover-icon {
    width: 26mm;
    margin: 16mm auto 8mm;
    border: none;
    max-height: none;
}

.cover-kicker {
    text-align: center;
    font-size: 9pt;
    letter-spacing: 1pt;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 6mm;
}

.cover-title {
    font-size: 30pt;
    text-align: center;
    color: #1d4ed8;
    margin: 0 0 4mm;
    line-height: 1.15;
}

.cover-subtitle {
    text-align: center;
    font-size: 11pt;
    color: #374151;
    margin: 0 auto 14mm;
    max-width: 130mm;
}

.cover-meta {
    width: 112mm;
    margin: 0 auto 12mm;
    font-size: 9.5pt;
    text-align: center;
}

.cover-meta .date {
    color: #374151;
}

.cover-team {
    width: 150mm;
    margin: 0 auto;
    text-align: center;
    font-size: 10pt;
    color: #1f2937;
}

.cover-team .label {
    font-size: 8.5pt;
    letter-spacing: 0.8pt;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 3mm;
}

.cover-team ul {
    list-style: none;
    margin: 0;
    padding: 0;
}

.cover-team li {
    margin: 0 0 2.2mm;
    font-weight: 600;
}

.cover-footer {
    position: absolute;
    bottom: 8mm;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 8pt;
    color: #6b7280;
    letter-spacing: 0.4pt;
}

/* ---------------------------------------------------------- içindekiler */
.toc-page { break-before: page; break-after: page; }

.toc-title {
    font-size: 20pt;
    color: #1d4ed8;
    border-bottom: 2.5pt solid #2563eb;
    border-left: none;
    padding: 0 0 5pt;
    margin: 0 0 12pt;
}

.toc-page .toc { font-size: 8.9pt; line-height: 1.38; }
.toc-page .toc > ul { padding-left: 0; column-count: 2; column-gap: 11mm; }
.toc-page .toc ul { list-style: none; padding-left: 0; margin: 0; }
.toc-page .toc ul ul { padding-left: 10pt; }
.toc-page .toc li { margin: 0 0 2pt; break-inside: avoid; }
.toc-page .toc > ul > li { margin-bottom: 4pt; }
.toc-page .toc > ul > li > a { font-weight: 600; color: #1e3a8a; }
.toc-page .toc a { color: #374151; }

p.caption {
    text-align: center;
    font-size: 8.4pt;
    color: #4b5563;
    font-style: italic;
    margin: -2pt 0 11pt;
}
"""


def data_uri(path: Path) -> str:
    mime = MIME.get(path.suffix.lower(), "application/octet-stream")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def embed_images(html: str) -> str:
    """Göreli <img src> yollarını base64 data URI'ye çevirir."""
    def replace(match: re.Match) -> str:
        raw = match.group(1)
        if raw.startswith("data:"):
            return match.group(0)
        target = (SRC_DIR / raw).resolve()
        if not target.is_file():
            print(f"  UYARI: görsel bulunamadı: {raw}")
            return match.group(0)
        return f'src="{data_uri(target)}"'

    return re.sub(r'src="([^"]+)"', replace, html)


def cover_html(spec: DocSpec) -> str:
    icon = data_uri(ICON_PATH) if ICON_PATH.is_file() else ""
    icon_tag = f'<img class="cover-icon" src="{icon}" alt="Uygulama ikonu">' if icon else ""
    team_items = "".join(f"<li>{name}</li>" for name in TEAM)
    return f"""
<section class="cover">
  <div class="cover-brand">{APP_NAME} · {APP_VERSION}</div>
  {icon_tag}
  <div class="cover-kicker">Yazılım Mühendisliği Proje Dokümanı</div>
  <h1 class="cover-title">{spec.title}</h1>
  <p class="cover-subtitle">{spec.subtitle}</p>
  <div class="cover-meta">
    <div class="date">{DOC_DATE}</div>
  </div>
  <div class="cover-team">
    <div class="label">Hazırlayanlar</div>
    <ul>{team_items}</ul>
  </div>
  <div class="cover-footer">{APP_NAME}</div>
</section>
"""


def build_html(spec: DocSpec) -> str:
    source = SRC_DIR / f"{spec.stem}.md"
    if not source.is_file():
        raise FileNotFoundError(source)

    text = source.read_text(encoding="utf-8")
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "1-2", "title": ""}},
    )
    body = md.convert(text)
    toc = md.toc
    body = embed_images(body)

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>{spec.title}</title>
<style>{CSS}</style>
</head>
<body>
{cover_html(spec)}
<section class="toc-page">
  <h2 class="toc-title">İçindekiler</h2>
  {toc}
</section>
<div id="content">
{body}
</div>
</body>
</html>
"""


def find_browser() -> Path:
    for candidate in BROWSERS:
        if candidate.is_file():
            return candidate
    raise RuntimeError(
        "Edge veya Chrome bulunamadı. Aranan yollar:\n"
        + "\n".join(str(path) for path in BROWSERS)
    )


def html_to_pdf(browser: Path, html_path: Path, pdf_path: Path) -> None:
    result = subprocess.run(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=8000",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if not pdf_path.is_file() or pdf_path.stat().st_size < 1000:
        raise RuntimeError(
            f"PDF üretilemedi (çıkış kodu {result.returncode}).\n{result.stderr[-800:]}"
        )


def overlay_font() -> tuple[Path, Path | None]:
    for regular, bold in FONT_CANDIDATES:
        if regular.is_file():
            return regular, bold if bold and bold.is_file() else None
    raise RuntimeError("Alt bilgi için Unicode font bulunamadı.")


def build_overlay(page_count: int) -> PdfReader:
    regular, _ = overlay_font()
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_font("Doc", "", str(regular))

    for index in range(page_count):
        pdf.add_page()
        if index == 0:
            continue

        pdf.set_draw_color(203, 213, 225)
        pdf.set_line_width(0.25)
        pdf.line(16, 282.6, 194, 282.6)

        pdf.set_text_color(107, 114, 128)
        pdf.set_font("Doc", "", 8)
        pdf.set_xy(16, 284.2)
        pdf.cell(120, 4, APP_NAME, align="L")
        pdf.set_xy(140, 284.2)
        pdf.cell(54, 4, f"Sayfa {index + 1} / {page_count}", align="R")

    return PdfReader(io.BytesIO(bytes(pdf.output())))


def stamp(raw_pdf: Path, target: Path, spec: DocSpec) -> int:
    reader = PdfReader(str(raw_pdf))
    overlay = build_overlay(len(reader.pages))

    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        page.merge_page(overlay.pages[index])
        writer.add_page(page)

    writer.add_metadata(
        {
            "/Title": spec.title,
            "/Author": APP_NAME,
            "/Subject": spec.subtitle,
            "/Keywords": "öğrenci not takip sistemi, Python, SQLite",
            "/Creator": APP_NAME,
            "/Producer": "Edge headless + pypdf + fpdf2",
        }
    )

    with target.open("wb") as handle:
        writer.write(handle)
    return len(reader.pages)


def verify(target: Path, spec: DocSpec, pages: int) -> bool:
    reader = PdfReader(str(target))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    images = sum(len(page.images) for page in reader.pages)
    size_kb = target.stat().st_size / 1024
    has_turkish = "ö" in text and "ş" in text and "İ" in text
    has_footer = "Sayfa 2 /" in text.replace("\u00a0", " ")
    print(
        f"  {target.name:28} {pages:>3} sayfa  {size_kb:>7.0f} KB  "
        f"{images:>2} görsel  Türkçe:{'OK' if has_turkish else 'HATA'}  "
        f"altbilgi:{'OK' if has_footer else 'HATA'}"
    )
    return has_turkish and has_footer and images >= 0


def build(spec: DocSpec, browser: Path, keep_html: bool = False) -> bool:
    print(f"\n[{spec.stem}]")
    html = build_html(spec)
    work = Path(tempfile.mkdtemp(prefix="onts-docs-"))
    html_path = work / f"{spec.stem}.html"
    raw_pdf = work / f"{spec.stem}-raw.pdf"
    html_path.write_text(html, encoding="utf-8")

    try:
        html_to_pdf(browser, html_path, raw_pdf)
        pages = stamp(raw_pdf, OUT_DIR / f"{spec.stem}.pdf", spec)
        ok = verify(OUT_DIR / f"{spec.stem}.pdf", spec, pages)
        if keep_html:
            shutil.copy2(html_path, OUT_DIR / f"{spec.stem}.html")
        return ok
    finally:
        shutil.rmtree(work, ignore_errors=True)


def resolve_specs(only: list[str]) -> list[DocSpec]:
    if not only:
        return list(DOCS)
    selected = [doc for doc in DOCS if doc.stem in only]
    missing = set(only) - {doc.stem for doc in selected}
    if missing:
        raise SystemExit(f"Bilinmeyen doküman: {', '.join(sorted(missing))}")
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Teslim PDF'lerini üretir.")
    parser.add_argument(
        "--only",
        nargs="+",
        default=[],
        metavar="AD",
        help="Yalnızca belirtilen kaynakları üret (ör. Design_Doc).",
    )
    parser.add_argument(
        "--keep-html",
        action="store_true",
        help="Üretilen ara HTML dosyalarını deliverables klasörüne kopyala.",
    )
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    browser = find_browser()
    specs = resolve_specs(args.only)

    print(f"Tarayıcı: {browser}")
    print(f"Çıktı   : {OUT_DIR}")

    failures = 0
    for spec in specs:
        try:
            if not build(spec, browser, args.keep_html):
                failures += 1
        except Exception as exc:  # tek doküman hatası diğerlerini durdurmasın
            failures += 1
            print(f"  HATA: {exc}")

    project_definition = SRC_DIR / "Project_Definition.txt"
    if project_definition.is_file():
        text = project_definition.read_text(encoding="utf-8")
        target = OUT_DIR / project_definition.name
        target.write_text(text, encoding="utf-8-sig")
        print(f"\nKopyalandı: {project_definition.name}")

    print("\nSonuç:", "tamamlandı" if failures == 0 else f"{failures} doküman başarısız")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
