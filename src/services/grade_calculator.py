"""Not hesaplama kurallari (FR-08). Arayuzden ve veritabanindan bagimsizdir."""

LETTER_TABLE = [  # (alt sinir, harf, katsayi)
    (90, "AA", 4.0),
    (85, "BA", 3.5),
    (80, "BB", 3.0),
    (75, "CB", 2.5),
    (70, "CC", 2.0),
    (60, "DD", 1.0),
    (0, "FF", 0.0),
]
PASS_AVERAGE = 60
PASS_FINAL = 50
WEIGHTS_WITH_ASSIGNMENT = (30, 50, 20)


def validate_score(value, name="Not"):
    """None gecerlidir (girilmemis); aksi halde 0-100 arasi sayi olmalidir."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} sayısal olmalıdır.")
    if value != value or value < 0 or value > 100:
        raise ValueError(f"{name} 0 ile 100 arasında olmalıdır.")
    return float(value)


def calculate_average(midterm, final, assignment=None, weights=None):
    """Agirlikli ortalamayi 2 basamaga yuvarlayarak dondurur.

    weights: (vize, final, odev) toplami 100 olan uclu. Verilmezse odev yokken
    (40, 60, 0), odev varken (30, 50, 20) kullanilir.
    """
    midterm = validate_score(midterm, "Vize")
    final = validate_score(final, "Final")
    assignment = validate_score(assignment, "Ödev")
    if midterm is None or final is None:
        raise ValueError("Vize ve final notu olmadan ortalama hesaplanamaz.")
    if weights is None:
        weights = WEIGHTS_WITH_ASSIGNMENT if assignment is not None else (40, 60, 0)
    if len(weights) != 3 or abs(sum(weights) - 100) > 1e-9:
        raise ValueError("Ağırlıklar toplamı 100 olmalıdır.")
    if assignment is None:
        if weights[2] != 0:
            raise ValueError("Ödev ağırlığı var ancak ödev notu girilmemiş.")
        assignment = 0.0
    total = (midterm * weights[0] + final * weights[1]
             + assignment * weights[2]) / 100
    return round(total, 2)


def to_letter(average):
    """Ortalamaya karsilik gelen (harf, katsayi) cifti."""
    average = validate_score(average, "Ortalama")
    for lower, letter, coef in LETTER_TABLE:
        if average >= lower:
            return letter, coef
    raise ValueError("Geçersiz ortalama.")  # ulasilamaz


def is_passed(average, final):
    return average >= PASS_AVERAGE and final >= PASS_FINAL


def calculate_gpa(items):
    """items: (katsayi, kredi) listesi. Kredi agirlikli genel ortalama (GPA)."""
    total_credit = sum(credit for _, credit in items)
    if total_credit == 0:
        return 0.0
    return round(sum(c * k for c, k in items) / total_credit, 2)
