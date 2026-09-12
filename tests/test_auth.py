"""Tests for JWT loading and redaction (never print the full key)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dane_um_warszawa.auth import MissingApiKey, load_api_key, redact_key


FAKE_JWT = "eyJhbGciOiJub25lIn0.e30.test-fixture-key-not-real"


class RedactKeyTests(unittest.TestCase):
    def test_redacts_middle_of_long_key(self) -> None:
        redacted = redact_key(FAKE_JWT)
        self.assertNotIn(FAKE_JWT, redacted)
        self.assertTrue(redacted.startswith("eyJh"))
        self.assertTrue(redacted.endswith("real"))
        self.assertIn("…", redacted)

    def test_short_key_is_fully_masked(self) -> None:
        self.assertEqual(redact_key("abcd"), "****")

    def test_empty_key_is_marked(self) -> None:
        self.assertEqual(redact_key(""), "<empty>")


class LoadApiKeyTests(unittest.TestCase):
    def test_explicit_argument_wins_over_env_and_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            key_file = Path(tmp) / "apiKey.txt"
            key_file.write_text("file-key\n", encoding="utf-8")
            env = {
                "UM_WARSZAWA_API_KEY": "env-key",
                "DANE_UM_KEY_FILE": str(key_file),
            }
            with patch.dict(os.environ, env, clear=False):
                self.assertEqual(load_api_key(api_key="  arg-key  "), "arg-key")

    def test_env_um_warszawa_api_key(self) -> None:
        with patch.dict(os.environ, {"UM_WARSZAWA_API_KEY": f"  {FAKE_JWT}  "}, clear=False):
            os.environ.pop("DANE_UM_KEY_FILE", None)
            self.assertEqual(load_api_key(), FAKE_JWT)

    def test_key_file_env_and_default_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            key_file = Path(tmp) / "apiKey.txt"
            key_file.write_text(f"{FAKE_JWT}\n", encoding="utf-8")
            with patch.dict(os.environ, {"DANE_UM_KEY_FILE": str(key_file)}, clear=False):
                os.environ.pop("UM_WARSZAWA_API_KEY", None)
                self.assertEqual(load_api_key(), FAKE_JWT)

    def test_explicit_key_file_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            key_file = Path(tmp) / "mykey.txt"
            key_file.write_text(FAKE_JWT, encoding="utf-8")
            with patch.dict(os.environ, {"UM_WARSZAWA_API_KEY": "env-should-lose"}, clear=False):
                self.assertEqual(load_api_key(key_file=str(key_file)), FAKE_JWT)

    def test_missing_key_raises_without_leaking_paths_as_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.txt"
            with patch.dict(os.environ, {"DANE_UM_KEY_FILE": str(missing)}, clear=False):
                os.environ.pop("UM_WARSZAWA_API_KEY", None)
                with self.assertRaises(MissingApiKey) as ctx:
                    load_api_key()
                message = str(ctx.exception)
                self.assertIn("UM_WARSZAWA_API_KEY", message)
                self.assertIn("DANE_UM_KEY_FILE", message)
                self.assertNotIn(FAKE_JWT, message)


if __name__ == "__main__":
    unittest.main()
