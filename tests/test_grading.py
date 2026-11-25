"""Not hesaplama kurallarının birim testleri."""

import pytest

from app.grading import (
    compute_gpa,
    format_score,
    grade_point,
    is_passed,
    letter_grade,
    weighted_average,
)


def test_weighted_average_basic():
    assert weighted_average([(80, 40), (60, 60)]) == 68.0


def test_weighted_average_normalizes_weights():
    assert weighted_average([(100, 1), (50, 1)]) == 75.0


def test_weighted_average_ignores_zero_weight():
    assert weighted_average([(100, 0)]) is None
    assert weighted_average([(100, 0), (70, 2)]) == 70.0


def test_weighted_average_empty():
    assert weighted_average([]) is None


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, "AA"),
        (90, "AA"),
        (89.99, "BA"),
        (85, "BA"),
        (80, "BB"),
        (75, "CB"),
        (70, "CC"),
        (65, "DC"),
        (60, "DD"),
        (59.99, "FD"),
        (50, "FD"),
        (49.99, "FF"),
        (0, "FF"),
    ],
)
def test_letter_grade_boundaries(score, expected):
    assert letter_grade(score) == expected


@pytest.mark.parametrize(
    ("score", "expected"),
    [(95, 4.0), (85, 3.5), (80, 3.0), (75, 2.5), (70, 2.0),
     (65, 1.5), (60, 1.0), (55, 0.5), (40, 0.0)],
)
def test_grade_point(score, expected):
    assert grade_point(score) == expected


def test_is_passed_threshold():
    assert is_passed(60) is True
    assert is_passed(59.99) is False


def test_compute_gpa_uses_credits():
    assert compute_gpa([(4.0, 4), (2.0, 4)]) == 3.0
    assert compute_gpa([(1.5, 4), (4.0, 4)]) == 2.75


def test_compute_gpa_without_credits():
    assert compute_gpa([]) is None
    assert compute_gpa([(4.0, 0)]) is None


def test_format_score():
    assert format_score(68.0) == "68.00"
    assert format_score(3.5, 1) == "3.5"
    assert format_score(None) == "-"
