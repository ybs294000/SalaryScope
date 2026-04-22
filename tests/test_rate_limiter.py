import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Stub out streamlit with a real dict for session_state BEFORE any import
# of rate_limiter, so st.session_state behaves exactly like the real thing.
# ---------------------------------------------------------------------------
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules['streamlit'] = mock_st

import app.core.rate_limiter as rl
from app.core.rate_limiter import (
    check_rate_limit,
    _session_check,
    _session_record,
    _session_clear,
    _fs_doc_id,
    _blocked_message,
    _LIMITS,
)

# Patch target for time.time as used inside rate_limiter's own namespace.
_TIME_TARGET = "app.core.rate_limiter.time.time"


class TestRateLimiterSessionLayer(unittest.TestCase):

    def setUp(self):
        # Always replace the dict object on BOTH the mock AND the module
        # so they are always in sync, regardless of test order.
        fresh = {}
        mock_st.session_state = fresh
        rl.st.session_state = fresh

    # ------------------------------------------------------------------
    # _blocked_message
    # ------------------------------------------------------------------

    def test_blocked_message_format(self):
        msg = _blocked_message(300.0)
        self.assertIsInstance(msg, str)
        self.assertIn("minute", msg)

    def test_blocked_message_minimum_one_minute(self):
        msg = _blocked_message(0.0)
        self.assertIn("1 minute", msg)

    def test_blocked_message_non_numeric_input(self):
        msg = _blocked_message("bad")
        self.assertIsInstance(msg, str)
        self.assertIn("minute", msg)

    # ------------------------------------------------------------------
    # _fs_doc_id
    # ------------------------------------------------------------------

    def test_doc_id_hides_pii(self):
        doc_id = _fs_doc_id("login", "secret@example.com")
        self.assertNotIn("secret", doc_id)
        self.assertNotIn("example.com", doc_id)
        self.assertTrue(doc_id.startswith("login__"))

    def test_doc_id_deterministic(self):
        self.assertEqual(
            _fs_doc_id("login", "user@test.com"),
            _fs_doc_id("login", "user@test.com"),
        )

    def test_doc_id_different_for_different_users(self):
        self.assertNotEqual(
            _fs_doc_id("login", "user1@test.com"),
            _fs_doc_id("login", "user2@test.com"),
        )

    def test_doc_id_different_for_different_actions(self):
        self.assertNotEqual(
            _fs_doc_id("login", "user@test.com"),
            _fs_doc_id("register", "user@test.com"),
        )

    # ------------------------------------------------------------------
    # _LIMITS config
    # ------------------------------------------------------------------

    def test_rate_limiter_limits_config(self):
        expected = {"login", "register", "resend_verify",
                    "change_password", "delete_account", "forgot_password"}
        self.assertEqual(set(_LIMITS.keys()), expected)

    def test_all_limits_have_positive_values(self):
        for action, (max_attempts, window) in _LIMITS.items():
            self.assertGreater(max_attempts, 0, action)
            self.assertGreater(window, 0, action)

    # ------------------------------------------------------------------
    # _session_check
    # ------------------------------------------------------------------

    def test_session_check_empty_state_allows(self):
        blocked, wait = _session_check("login", "user@test.com", 5, 300)
        self.assertFalse(blocked)
        self.assertEqual(wait, 0.0)

    def test_session_check_below_limit_allows(self):
        with patch(_TIME_TARGET, return_value=1000):
            for _ in range(4):          # 4 < limit of 5
                _session_record("login", "user@test.com")
            blocked, _ = _session_check("login", "user@test.com", 5, 300)
        self.assertFalse(blocked)

    def test_session_check_at_limit_blocks(self):
        with patch(_TIME_TARGET, return_value=1000):
            for _ in range(5):          # exactly at limit
                _session_record("login", "user@test.com")
            blocked, wait = _session_check("login", "user@test.com", 5, 300)
        self.assertTrue(blocked)
        self.assertGreater(wait, 0)

    def test_session_check_over_limit_blocks(self):
        with patch(_TIME_TARGET, return_value=1000):
            for _ in range(6):          # over limit
                _session_record("login", "user@test.com")
            blocked, wait = _session_check("login", "user@test.com", 5, 300)
        self.assertTrue(blocked)
        self.assertGreater(wait, 0)

    def test_session_check_expired_window_allows(self):
        # Record attempts at t=1000, then check after window has passed.
        with patch(_TIME_TARGET, return_value=1000):
            for _ in range(6):
                _session_record("login", "user@test.com")
        # Check at t=1000+300+1 — window has expired.
        with patch(_TIME_TARGET, return_value=1302):
            blocked, _ = _session_check("login", "user@test.com", 5, 300)
        self.assertFalse(blocked)

    def test_session_check_corrupted_record_allows(self):
        key = rl._session_key("login", "user@test.com")
        rl.st.session_state[key] = "corrupted"
        blocked, _ = _session_check("login", "user@test.com", 5, 300)
        self.assertFalse(blocked)

    # ------------------------------------------------------------------
    # _session_record
    # ------------------------------------------------------------------

    def test_session_record_increments_counter(self):
        key = rl._session_key("login", "user@test.com")
        with patch(_TIME_TARGET, return_value=1000):
            _session_record("login", "user@test.com")
            _session_record("login", "user@test.com")
        attempts, _ = rl.st.session_state[key]
        self.assertEqual(attempts, 2)

    def test_session_record_resets_on_expired_window(self):
        key = rl._session_key("login", "user@test.com")
        with patch(_TIME_TARGET, return_value=1000):
            for _ in range(3):
                _session_record("login", "user@test.com")
        # Record again after window expires — counter should reset to 1.
        with patch(_TIME_TARGET, return_value=1400):
            _session_record("login", "user@test.com")
        attempts, _ = rl.st.session_state[key]
        self.assertEqual(attempts, 1)

    # ------------------------------------------------------------------
    # _session_clear
    # ------------------------------------------------------------------

    def test_session_clear_removes_record(self):
        with patch(_TIME_TARGET, return_value=1000):
            for _ in range(5):
                _session_record("login", "user@test.com")
        _session_clear("login", "user@test.com")
        blocked, _ = _session_check("login", "user@test.com", 5, 300)
        self.assertFalse(blocked)

    def test_session_clear_on_missing_key_is_safe(self):
        # Should not raise even if the key doesn't exist.
        _session_clear("login", "nonexistent@test.com")

    # ------------------------------------------------------------------
    # check_rate_limit (public API — session layer only, Firestore stubbed)
    # ------------------------------------------------------------------

    def test_check_rate_limit_unknown_action_allowed(self):
        allowed, msg = check_rate_limit("nonexistent_action", "user@test.com")
        self.assertTrue(allowed)
        self.assertIsNone(msg)

    def test_check_rate_limit_non_string_args_allowed(self):
        allowed, msg = check_rate_limit(None, "user@test.com")
        self.assertTrue(allowed)
        self.assertIsNone(msg)

    def test_check_rate_limit_blocks_after_exceeded(self):
        # Stub Firestore so only the session layer matters.
        with patch("app.core.rate_limiter._firestore_check", return_value=(False, 0)), \
             patch("app.core.rate_limiter._firestore_record"), \
             patch(_TIME_TARGET, return_value=1000):
            for _ in range(6):
                _session_record("login", "user@test.com")
            allowed, msg = check_rate_limit("login", "user@test.com")
        self.assertFalse(allowed)
        self.assertIsNotNone(msg)
        self.assertIn("minute", msg)

    def test_check_rate_limit_allows_after_clear(self):
        with patch("app.core.rate_limiter._firestore_check", return_value=(False, 0)), \
             patch("app.core.rate_limiter._firestore_record"), \
             patch("app.core.rate_limiter._firestore_clear"), \
             patch(_TIME_TARGET, return_value=1000):
            for _ in range(6):
                _session_record("login", "user@test.com")
            _session_clear("login", "user@test.com")
            allowed, msg = check_rate_limit("login", "user@test.com")
        self.assertTrue(allowed)
        self.assertIsNone(msg)


if __name__ == '__main__':
    unittest.main()