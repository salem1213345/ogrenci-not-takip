"""Not hesaplama kuralları (saf fonksiyonlar, veritabanından bağımsız).

Ağırlıklı ortalama:  sum(not * ağırlık) / sum(ağırlık)
GNO:                 sum(harf_puanı * kredi) / sum(kredi)
Geçme eşiği:         60.0 puan (DD ve üzeri)
"""

from collections.abc import Iterable

PASS_THRESHOLD = 60.0

# (alt sınır, harf, katsayı) - büyükten küçüğe sıralıdır.
LETTER_SCALE: tuple[tuple[float, str, float], ...] = (
    (90.0, "AA", 4.0),
    (85.0, "BA", 3.5),
    (80.0, "BB", 3.0),
    (75.0, "CB", 2.5),
    (70.0, "CC", 2.0),
    (65.0, "DC", 1.5),
    (60.0, "DD", 1.0),
    (50.0, "FD", 0.5),
    (0.0, "FF", 0.0),
)


def weighted_average(items: Iterable[tuple[float, float]]) -> float | None:
    """(not, ağırlık) çiftlerinden ağırlıklı ortalama üretir.

    Ağırlık toplamı sıfır veya negatifse ``None`` döner.
    """
    total_weight = 0.0
    total_score = 0.0
    for score, weight in items:
        if weight <= 0:
            continue
        total_score += float(score) * float(weight)
        total_weight += float(weight)
    if total_weight <= 0:
        return None
    return round(total_score / total_weight, 2)


def letter_grade(score: float) -> str:
    """Puanı Türk yükseköğretim harf notuna çevirir."""
    for threshold, letter, _ in LETTER_SCALE:
        if score >= threshold:
            return letter
    return "FF"


def grade_point(score: float) -> float:
    """Puanı 4'lük sistemdeki katsayıya çevirir."""
    for threshold, _, point in LETTER_SCALE:
        if score >= threshold:
            return point
    return 0.0


def is_passed(score: float) -> bool:
    return score >= PASS_THRESHOLD


def compute_gpa(items: Iterable[tuple[float, float]]) -> float | None:
    """(harf_puanı, kredi) çiftlerinden kredi ağırlıklı GNO üretir."""
    total_credit = 0.0
    total_point = 0.0
    for point, credit in items:
        if credit <= 0:
            continue
        total_point += float(point) * float(credit)
        total_credit += float(credit)
    if total_credit <= 0:
        return None
    return round(total_point / total_credit, 2)


def format_score(score: float | None, digits: int = 2) -> str:
    """Puanı ekranda/raporda göstermek için biçimlendirir."""
    if score is None:
        return "-"
    return f"{score:.{digits}f}"
