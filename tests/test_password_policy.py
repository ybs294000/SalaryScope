import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from app.core.password_policy import validate_password_strength, password_strength_hint


class TestPasswordPolicy(unittest.TestCase):

    def test_valid_password_passes(self):
        """A password meeting all requirements should return no errors."""
        errors = validate_password_strength("Secure#Pass12")
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_too_short_rejected(self):
        """Password under 12 characters should be rejected."""
        errors = validate_password_strength("Short#1A")
        self.assertTrue(any("12 characters" in e for e in errors))

    def test_too_long_rejected(self):
        """Password over 128 characters should be rejected."""
        long_pass = "A" * 64 + "b" * 64 + "#1"
        errors = validate_password_strength(long_pass)
        self.assertTrue(any("128" in e for e in errors))

    def test_no_uppercase_rejected(self):
        errors = validate_password_strength("nouppercase#12")
        self.assertTrue(any("uppercase" in e for e in errors))

    def test_no_lowercase_rejected(self):
        errors = validate_password_strength("NOLOWERCASE#12")
        self.assertTrue(any("lowercase" in e for e in errors))

    def test_no_digit_rejected(self):
        errors = validate_password_strength("NoDigitHere!!!")
        self.assertTrue(any("digit" in e for e in errors))

    def test_no_special_char_rejected(self):
        errors = validate_password_strength("NoSpecial123Abc")
        self.assertTrue(any("special character" in e for e in errors))

    def test_leading_space_rejected(self):
        errors = validate_password_strength(" LeadingSpace#1")
        self.assertTrue(any("space" in e for e in errors))

    def test_trailing_space_rejected(self):
        errors = validate_password_strength("TrailingSpace#1 ")
        self.assertTrue(any("space" in e for e in errors))

    def test_consecutive_identical_chars_rejected(self):
        errors = validate_password_strength("Passsword#12345")
        self.assertTrue(any("identical" in e.lower() or "consecutive" in e.lower() for e in errors))

    def test_common_password_rejected(self):
        errors = validate_password_strength("password123!AB")
        self.assertTrue(any("common" in e.lower() for e in errors))

    def test_non_string_input_handled(self):
        errors = validate_password_strength(None)
        self.assertTrue(len(errors) > 0)
        errors = validate_password_strength(12345)
        self.assertTrue(len(errors) > 0)

    def test_empty_string_handled(self):
        errors = validate_password_strength("")
        self.assertTrue(len(errors) > 0)

    def test_hint_is_string(self):
        hint = password_strength_hint()
        self.assertIsInstance(hint, str)
        self.assertGreater(len(hint), 0)

    def test_valid_password_with_various_special_chars(self):
        for special in ["!", "@", "#", "$", "%", "^", "&", "*"]:
            pw = f"ValidPass{special}123"
            errors = validate_password_strength(pw)
            self.assertEqual(errors, [], f"Password with '{special}' should pass")

    def test_exactly_12_chars_accepted(self):
        errors = validate_password_strength("Secure#Pass1")
        self.assertEqual(errors, [])

    def test_exactly_128_chars_accepted(self):
        pw = "Aa1!" + "".join(chr(97 + i % 26) for i in range(124))
        errors = validate_password_strength(pw)
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()