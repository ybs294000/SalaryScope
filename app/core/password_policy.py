# password_policy.py
#
# Enforces strong password requirements aligned with:
#   - NIST SP 800-63B (2024 revision)
#   - OWASP Authentication Cheat Sheet (2024)
#
# Rules applied:
#   - Minimum 12 characters (NIST recommends >= 8; 12 is the current
#     industry baseline for user-facing applications)
#   - Maximum 128 characters (NIST upper bound to prevent DoS via bcrypt)
#   - At least one uppercase letter
#   - At least one lowercase letter
#   - At least one digit
#   - At least one special character from the printable ASCII set
#   - No leading or trailing whitespace
#   - No sequences of 3 or more identical consecutive characters
#     (e.g. "aaa", "111") -- reduces trivially guessable passwords
#   - Not in the common-password blocklist defined below
#
# Rollback:
#   Delete this file.
#   In auth.py, remove:
#     - the import of validate_password_strength / password_strength_hint
#     - call sites in register_ui (marked -- ROLLBACK: password_policy --)
#   In account_management.py, remove:
#     - the import of validate_password_strength / password_strength_hint
#     - call sites in render_change_password_ui (same marker)
#   No other files are affected.

import string

# ---------------------------------------------------------------------------
# COMMON PASSWORD BLOCKLIST
# A minimal set of the most frequently observed passwords. Supplements the
# structural rules. Kept deliberately small to avoid memory bloat on
# Streamlit Cloud. Expand as needed.
# ---------------------------------------------------------------------------

_COMMON_PASSWORDS: frozenset = frozenset({
    "password", "password1", "password12", "password123",
    "password1234", "password12345", "password123456",
    "123456", "1234567", "12345678", "123456789", "1234567890",
    "qwerty", "qwerty123", "qwertyuiop",
    "iloveyou", "iloveyou1",
    "admin", "admin123", "admin1234",
    "letmein", "letmein1",
    "welcome", "welcome1", "welcome123",
    "monkey", "monkey123",
    "dragon", "dragon123",
    "master", "master123",
    "sunshine", "sunshine1",
    "princess", "princess1",
    "football", "football1",
    "shadow", "shadow123",
    "superman", "superman1",
    "michael", "michael1",
    "charlie", "charlie1",
    "donald", "donald123",
    "abc123", "abc1234",
    "pass", "pass123", "pass1234",
    "test", "test123", "test1234",
    "login", "login123",
    "user", "user123",
    "guest", "guest123",
})

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

_SPECIAL_CHARS: frozenset = frozenset(string.punctuation)

_MIN_LENGTH: int = 12
_MAX_LENGTH: int = 128
_CONSECUTIVE_LIMIT: int = 3  # block runs of N or more identical chars


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def validate_password_strength(password: object) -> list:
    """
    Validate a candidate password against the policy rules.

    Accepts any type -- returns a type-error message for non-string input
    rather than raising, so callers need no prior isinstance guard.

    Returns a list of human-readable failure messages.
    An empty list means the password passed all checks.

    This function performs no I/O and has no side effects.
    """
    if not isinstance(password, str):
        return ["Password must be a text string."]

    errors: list = []
    length: int = len(password)

    # --- Length ---
    # Check both bounds before checking character classes. A very short or
    # very long password should not produce a flood of character-class errors.
    if length < _MIN_LENGTH:
        errors.append(
            f"Password must be at least {_MIN_LENGTH} characters long."
        )

    if length > _MAX_LENGTH:
        errors.append(
            f"Password must not exceed {_MAX_LENGTH} characters."
        )

    # --- Boundary whitespace ---
    if password != password.strip():
        errors.append("Password must not start or end with a space.")

    # --- Character class checks ---
    # Skipped on empty input to avoid a confusing cascade; the length error
    # above is sufficient to communicate the problem.
    if length > 0:
        if not any(c.isupper() for c in password):
            errors.append(
                "Password must contain at least one uppercase letter."
            )

        if not any(c.islower() for c in password):
            errors.append(
                "Password must contain at least one lowercase letter."
            )

        if not any(c.isdigit() for c in password):
            errors.append(
                "Password must contain at least one digit (0-9)."
            )

        if not any(c in _SPECIAL_CHARS for c in password):
            errors.append(
                "Password must contain at least one special character "
                "(!@#$%^&* etc.)."
            )

        # --- Consecutive identical characters ---
        if _has_consecutive_identical(password, _CONSECUTIVE_LIMIT):
            errors.append(
                f"Password must not contain {_CONSECUTIVE_LIMIT} or more "
                "identical characters in a row (e.g. 'aaa', '111')."
            )

    # --- Common password blocklist ---
    # The try/except is a belt-and-suspenders guard against any unexpected
    # AttributeError if this function is ever called in an unusual context.
    try:
        if password.lower() in _COMMON_PASSWORDS:
            errors.append(
                "This password is too common. "
                "Please choose a more unique password."
            )
    except AttributeError:
        pass

    return errors


def password_strength_hint() -> str:
    """
    Return a concise hint string suitable for display below a password field.
    """
    return (
        f"At least {_MIN_LENGTH} characters, with uppercase, lowercase, "
        "a digit, and a special character. "
        "No three identical characters in a row."
    )


# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _has_consecutive_identical(text: str, limit: int) -> bool:
    """
    Return True if text contains a run of >= limit identical characters.

    Preconditions (enforced defensively):
      - text is a non-empty string
      - limit >= 2

    Returns False for any input that does not meet the preconditions rather
    than raising.
    """
    if not isinstance(text, str):
        return False
    if len(text) < limit or limit < 2:
        return False

    run: int = 1
    for i in range(1, len(text)):
        if text[i] == text[i - 1]:
            run += 1
            if run >= limit:
                return True
        else:
            run = 1
    return False
