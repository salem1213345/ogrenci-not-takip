"""Mermaid diyagramlarını mermaid.ink üzerinden PNG'ye dönüştürür."""

import base64
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE = BASE_DIR / "docs" / "mermaid"
TARGET = BASE_DIR / "docs" / "diagrams"
API = "https://mermaid.ink/img/"
HEADERS = {"User-Agent": "Mozilla/5.0 (ogrenci-not-takip docs builder)"}

DIAGRAMS = {
    "er": "er.png",
    "mimari": "mimari.png",
    "kullanim-durumu": "kullanim-durumu.png",
    "not-girisi-sira": "not-girisi-sira.png",
    "not-hesaplama": "not-hesaplama.png",
}


def render(source: Path, target: Path, width: int = 1600) -> Path:
    code = source.read_text(encoding="utf-8")
    encoded = base64.urlsafe_b64encode(code.encode("utf-8")).decode("ascii")
    url = f"{API}{encoded}?bgColor=FFFFFF&type=png&width={width}"
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    if not data.startswith(b"\x89PNG"):
        raise RuntimeError(f"{target.name}: beklenen PNG değil ({data[:8]!r})")
    target.write_bytes(data)
    return target


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    failures = 0
    for stem, filename in DIAGRAMS.items():
        source = SOURCE / f"{stem}.mmd"
        target = TARGET / filename
        try:
            for attempt in range(3):
                try:
                    render(source, target)
                    break
                except Exception as exc:  # ağ hatalarında yeniden dene
                    if attempt == 2:
                        raise
                    print(f"  yeniden denenecek ({exc})")
                    time.sleep(2)
            print(f"OK  {filename:28} {target.stat().st_size:>8} bayt")
        except Exception as exc:
            failures += 1
            print(f"HATA {filename}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
