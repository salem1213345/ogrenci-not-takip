"""Öğrenci Not Takip Sistemi - giriş noktası.

Kullanım:
    python main.py                                    # demo (data/demo.db) + demo hesapları
    python main.py --real                             # gerçek veritabanı (data/notlar.db)
    python main.py --demo --db data/demo.db           # demo; var olan veriler korunur
    python main.py --demo --db data/demo.db --reset-demo   # demo verisini sıfırla
    python main.py --db baska.db                      # farklı veritabanı dosyası
"""

import argparse
import sys
from pathlib import Path

from app.config import APP_NAME, APP_VERSION, BASE_DIR, DEFAULT_DB_PATH, DEMO_DB_PATH
from app.database import Database
from app.demo_data import load_demo_data, reset_demo_database
from app.errors import ValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{APP_VERSION}")
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite veritabanı dosyası (varsayılan: demo için data/demo.db, "
             "--real ile data/notlar.db)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--demo",
        action="store_true",
        help="Ayrı demo veritabanını açar; boşsa örnek verilerle doldurur, doluysa korur "
             "(seçenek verilmezse varsayılan budur)",
    )
    mode.add_argument(
        "--real",
        action="store_true",
        help="Gerçek veritabanını (data/notlar.db) açar; demo hesapları gösterilmez",
    )
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="(--demo ile) demo veritabanını silip örnek verilerle yeniden oluşturur",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    return parser


def demo_mode(args) -> bool:
    """Seçenek verilmeden çalıştırma (ör. VS Code'daki çalıştır düğmesi) demo açar.
    Gerçek veritabanı için --real, başka bir dosya için --db kullanılır."""
    return args.demo or (not args.real and not args.db)


def resolve_db_path(args) -> str:
    """Göreli --db yolları, çalışma klasörüne değil proje klasörüne (main.py'nin
    bulunduğu yer) göre çözülür; proje hangi klasöre kopyalanırsa kopyalansın çalışır."""
    if args.db:
        if args.db == ":memory:" or Path(args.db).is_absolute():
            return args.db
        return str(BASE_DIR / args.db)
    return str(DEMO_DB_PATH if demo_mode(args) else DEFAULT_DB_PATH)


def is_real_database(path: str) -> bool:
    return Path(path).resolve() == Path(DEFAULT_DB_PATH).resolve()


def prepare_database(args) -> Database:
    """Veritabanını açar; demo seçeneklerini uygular. Hata halinde ValidationError."""
    db_path = resolve_db_path(args)
    demo = demo_mode(args)
    if args.real and args.db:
        raise ValidationError("--real ile --db birlikte kullanılamaz.")
    if args.reset_demo and not args.demo:
        raise ValidationError("--reset-demo yalnızca --demo ile birlikte kullanılabilir.")
    if demo and is_real_database(db_path):
        raise ValidationError("Demo verileri gerçek veritabanına (data/notlar.db) yüklenemez. "
                              "Demo için: python main.py --demo --db data/demo.db")
    if args.reset_demo:
        db = reset_demo_database(db_path)
        print(f"Demo veritabanı sıfırlandı ve yeniden dolduruldu: {db_path}")
        return db
    db = Database(db_path)
    if db.backup_path:
        print(f"Veritabanı yeni sürüme güncellendi; önceki hali yedeklendi: {db.backup_path}")
    if demo:
        try:
            inserted = load_demo_data(db)
        except ValidationError:
            db.close()
            raise
        if inserted:
            print(f"Demo veritabanı oluşturuldu ({inserted} kayıt): {db_path}")
        else:
            print(f"Demo veritabanı açıldı; mevcut veriler korundu: {db_path}")
    return db


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        db = prepare_database(args)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    # tkinter yalnızca masaüstü arayüzü gerektiğinde içe aktarılır.
    from app.ui.app_window import AppWindow  # pylint: disable=import-outside-toplevel

    try:
        window = AppWindow(db, db_path=resolve_db_path(args))
    except Exception:
        db.close()
        raise
    window.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
