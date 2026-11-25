import unittest

from src.services import grade_calculator as calc


class TestCalculateAverage(unittest.TestCase):
    def test_default_weights_two_components(self):  # TC-01
        self.assertEqual(calc.calculate_average(70, 80), 76.0)

    def test_with_assignment_default_weights(self):  # TC-02
        self.assertEqual(calc.calculate_average(70, 85, 90), 81.5)

    def test_custom_weights(self):  # TC-03
        self.assertEqual(calc.calculate_average(50, 100, None, (50, 50, 0)), 75.0)

    def test_rounding_two_decimals(self):  # TC-04
        self.assertEqual(calc.calculate_average(33.33, 66.67), 53.33)

    def test_boundary_zero_and_hundred(self):  # TC-05
        self.assertEqual(calc.calculate_average(0, 0), 0.0)
        self.assertEqual(calc.calculate_average(100, 100), 100.0)

    def test_negative_score_rejected(self):  # TC-06
        with self.assertRaises(ValueError):
            calc.calculate_average(-1, 50)

    def test_over_100_rejected(self):  # TC-07
        with self.assertRaises(ValueError):
            calc.calculate_average(50, 100.01)

    def test_non_numeric_rejected(self):  # TC-08
        with self.assertRaises(ValueError):
            calc.calculate_average("abc", 50)

    def test_missing_final_rejected(self):  # TC-09
        with self.assertRaises(ValueError):
            calc.calculate_average(50, None)

    def test_weights_must_sum_to_100(self):  # TC-10
        with self.assertRaises(ValueError):
            calc.calculate_average(50, 50, None, (40, 50, 0))

    def test_bool_rejected(self):  # TC-11
        with self.assertRaises(ValueError):
            calc.calculate_average(True, 50)


class TestLetterAndPass(unittest.TestCase):
    def test_letter_boundaries(self):  # TC-12
        cases = {100: "AA", 90: "AA", 89.99: "BA", 85: "BA", 84.99: "BB",
                 80: "BB", 75: "CB", 70: "CC", 69.99: "DD", 60: "DD",
                 59.99: "FF", 0: "FF"}
        for avg, letter in cases.items():
            with self.subTest(avg=avg):
                self.assertEqual(calc.to_letter(avg)[0], letter)

    def test_pass_rule(self):  # TC-13
        self.assertTrue(calc.is_passed(60, 50))
        self.assertFalse(calc.is_passed(59.99, 80))
        self.assertFalse(calc.is_passed(70, 49))  # final alt siniri

    def test_gpa(self):  # TC-14
        self.assertEqual(calc.calculate_gpa([(4.0, 3), (2.0, 3)]), 3.0)
        self.assertEqual(calc.calculate_gpa([(4.0, 4), (1.0, 2)]), 3.0)

    def test_gpa_empty(self):  # TC-15
        self.assertEqual(calc.calculate_gpa([]), 0.0)


if __name__ == "__main__":
    unittest.main()
