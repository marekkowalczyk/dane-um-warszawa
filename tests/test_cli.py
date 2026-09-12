"""CLI tests for lines-at-stop, departures, and vehicle-locations."""

from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from io import BytesIO
from unittest.mock import patch
from urllib.request import Request

from dane_um_warszawa.cli import ATTRIBUTION, main
from dane_um_warszawa.client import ACTION_LINES_AT_STOP


FAKE_JWT = "eyJhbGciOiJub25lIn0.e30.test-fixture-key-not-real"
WARSAW_TZ = "Europe/Warsaw"


class FakeHTTPResponse:
    def __init__(self, payload: object, status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self._buf = BytesIO(raw)
        self.status = status

    def read(self) -> bytes:
        return self._buf.read()

    def __enter__(self) -> FakeHTTPResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _auth_header(req: Request) -> str:
    headers = {key.lower(): value for key, value in req.header_items()}
    return headers["authorization"]


class CliTests(unittest.TestCase):
    def _run(self, argv: list[str], fake_urlopen):
        out = io.StringIO()
        err = io.StringIO()
        with patch.dict("os.environ", {"UM_WARSZAWA_API_KEY": FAKE_JWT}, clear=False):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                with redirect_stdout(out), patch("sys.stderr", err):
                    code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_lines_at_stop_prints_lines_attribution_and_warsaw_time(self) -> None:
        def fake_urlopen(req: Request, timeout: float | None = None):
            self.assertTrue(req.full_url.endswith(ACTION_LINES_AT_STOP))
            self.assertEqual(_auth_header(req), FAKE_JWT)
            return FakeHTTPResponse({"result": [{"linia": "157"}, {"linia": "523"}]})

        code, out, err = self._run(["lines-at-stop", "1001", "01"], fake_urlopen)
        self.assertEqual(code, 0)
        self.assertIn("157", out)
        self.assertIn("523", out)
        self.assertIn(ATTRIBUTION, err)
        self.assertIn(WARSAW_TZ, err)
        self.assertNotIn(ATTRIBUTION, out)
        self.assertNotIn(FAKE_JWT, out + err)

    def test_departures_command(self) -> None:
        def fake_urlopen(req: Request, timeout: float | None = None):
            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual(body["line"], "191")
            return FakeHTTPResponse(
                {"result": [{"czas": "09:00:00", "kierunek": "Wilków"}]}
            )

        code, out, err = self._run(["departures", "3003", "02", "191"], fake_urlopen)
        self.assertEqual(code, 0)
        self.assertIn("09:00:00", out)
        self.assertIn("Wilków", out)
        self.assertIn(ATTRIBUTION, err)
        self.assertNotIn(FAKE_JWT, out + err)

    def test_vehicle_locations_command(self) -> None:
        def fake_urlopen(req: Request, timeout: float | None = None):
            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual(body["type"], 2)
            return FakeHTTPResponse(
                {"result": [{"Lines": "17", "Lat": 52.2, "Lon": 21.0}]}
            )

        code, out, err = self._run(["vehicle-locations", "tram"], fake_urlopen)
        self.assertEqual(code, 0)
        self.assertIn("17", out)
        self.assertIn(ATTRIBUTION, err)

    def test_json_flag_after_subcommand_is_parseable(self) -> None:
        def fake_urlopen(req: Request, timeout: float | None = None):
            return FakeHTTPResponse({"result": [{"linia": "157"}]})

        code, out, err = self._run(
            ["lines-at-stop", "1001", "01", "--json"],
            fake_urlopen,
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), ["157"])
        self.assertIn(ATTRIBUTION, err)
        self.assertNotIn(ATTRIBUTION, out)

    def test_missing_key_exits_nonzero_without_secret(self) -> None:
        buf = io.StringIO()
        err = io.StringIO()
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in {"UM_WARSZAWA_API_KEY", "DANE_UM_KEY_FILE"}
        }
        env["DANE_UM_KEY_FILE"] = "/tmp/missing-dane-um-key"
        with patch.dict("os.environ", env, clear=True):
            with redirect_stdout(buf), patch("sys.stderr", err):
                code = main(["lines-at-stop", "1", "01"])
        self.assertEqual(code, 2)
        self.assertNotIn(FAKE_JWT, err.getvalue() + buf.getvalue())
        self.assertIn("UM_WARSZAWA_API_KEY", err.getvalue())
        self.assertIn("/tmp/missing-dane-um-key", err.getvalue())


if __name__ == "__main__":
    unittest.main()
