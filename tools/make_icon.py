"""Proje ikonunu (mezuniyet kepi) üretir: PNG ve ICO."""

from pathlib import Path

from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS = BASE_DIR / "assets"
SIZE = 1024


def _gradient(size: int) -> Image.Image:
    top = (37, 99, 235)
    bottom = (30, 64, 175)
    gradient = Image.new("RGB", (1, size))
    for y in range(size):
        ratio = y / max(size - 1, 1)
        color = tuple(round(top[index] * (1 - ratio) + bottom[index] * ratio) for index in range(3))
        gradient.putpixel((0, y), color)
    return gradient.resize((size, size))


def build_icon() -> Image.Image:
    image = Image.new("RGB", (SIZE, SIZE), "#ffffff")
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (24, 24, SIZE - 24, SIZE - 24), radius=200, fill=255
    )
    image.paste(_gradient(SIZE), (0, 0), mask)

    draw = ImageDraw.Draw(image)
    # Kepin üst kısmı
    draw.polygon([(512, 250), (180, 392), (512, 534), (844, 392)], fill="#ffffff")
    # Kepin gövdesi
    draw.polygon(
        [(340, 456), (684, 456), (660, 620), (512, 684), (364, 620)],
        fill="#dbeafe",
    )
    # Püskül
    draw.line([(820, 398), (842, 596)], fill="#fbbf24", width=22)
    draw.ellipse((818, 584, 866, 632), fill="#fbbf24")
    # Gövde üzerinde onay işareti
    draw.line([(452, 556), (500, 604), (580, 508)], fill="#2563eb", width=34, joint="curve")
    return image


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = build_icon()
    icon.resize((512, 512), Image.Resampling.LANCZOS).save(ASSETS / "app_icon.png")
    icon.resize((256, 256), Image.Resampling.LANCZOS).save(
        ASSETS / "app_icon.ico",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("İkonlar üretildi:", ASSETS / "app_icon.png", ASSETS / "app_icon.ico")


if __name__ == "__main__":
    main()
