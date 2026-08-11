import unittest
from intelligence.general_auditor import calculate_grade


class TestCalculateGrade(unittest.TestCase):
    def test_max_score_zero(self):
        """Test edge case where max_score is 0 to prevent division by zero."""
        self.assertEqual(calculate_grade(10, 0), "N/A")
        self.assertEqual(calculate_grade(0, 0), "N/A")

    def test_grade_a_plus(self):
        """Test A+ grade boundaries."""
        self.assertEqual(calculate_grade(90, 100), "A+")
        self.assertEqual(calculate_grade(100, 100), "A+")
        self.assertEqual(calculate_grade(110, 100), "A+")  # > 100%

    def test_grade_a(self):
        """Test A grade boundaries."""
        self.assertEqual(calculate_grade(85, 100), "A")
        self.assertEqual(calculate_grade(89, 100), "A")

    def test_grade_a_minus(self):
        """Test A- grade boundaries."""
        self.assertEqual(calculate_grade(80, 100), "A-")
        self.assertEqual(calculate_grade(84, 100), "A-")

    def test_grade_b_plus(self):
        """Test B+ grade boundaries."""
        self.assertEqual(calculate_grade(75, 100), "B+")
        self.assertEqual(calculate_grade(79, 100), "B+")

    def test_grade_b(self):
        """Test B grade boundaries."""
        self.assertEqual(calculate_grade(70, 100), "B")
        self.assertEqual(calculate_grade(74, 100), "B")

    def test_grade_b_minus(self):
        """Test B- grade boundaries."""
        self.assertEqual(calculate_grade(65, 100), "B-")
        self.assertEqual(calculate_grade(69, 100), "B-")

    def test_grade_c_plus(self):
        """Test C+ grade boundaries."""
        self.assertEqual(calculate_grade(60, 100), "C+")
        self.assertEqual(calculate_grade(64, 100), "C+")

    def test_grade_c(self):
        """Test C grade boundaries."""
        self.assertEqual(calculate_grade(55, 100), "C")
        self.assertEqual(calculate_grade(59, 100), "C")

    def test_grade_c_minus(self):
        """Test C- grade boundaries."""
        self.assertEqual(calculate_grade(50, 100), "C-")
        self.assertEqual(calculate_grade(54, 100), "C-")

    def test_grade_d_plus(self):
        """Test D+ grade boundaries."""
        self.assertEqual(calculate_grade(45, 100), "D+")
        self.assertEqual(calculate_grade(49, 100), "D+")

    def test_grade_d(self):
        """Test D grade boundaries."""
        self.assertEqual(calculate_grade(40, 100), "D")
        self.assertEqual(calculate_grade(44, 100), "D")

    def test_grade_f(self):
        """Test F grade boundaries."""
        self.assertEqual(calculate_grade(39, 100), "F")
        self.assertEqual(calculate_grade(0, 100), "F")
        self.assertEqual(calculate_grade(-10, 100), "F")  # < 0%

    def test_fractional_percentages(self):
        """Test handling of percentages with fractions."""
        # 89.5 / 100 = 89.5% -> A
        self.assertEqual(calculate_grade(895, 1000), "A")
        # 89.9 / 100 = 89.9% -> A
        self.assertEqual(calculate_grade(899, 1000), "A")
        # 90.0 / 100 = 90.0% -> A+
        self.assertEqual(calculate_grade(900, 1000), "A+")


if __name__ == "__main__":
    unittest.main()
