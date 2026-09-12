"""Mocked HTTP tests for the universal ZTM client (no live network)."""

from __future__ import annotations

import json
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

from dane_um_warszawa.client import (
    ACTION_DEPARTURES,
    ACTION_LINES_AT_STOP,
    ACTION_VEHICLE_LOCATIONS,
    DEFAULT_BASE_URL,
    ZtmClient,
)
from dane_um_warszawa.parse import ApiError


FAKE_JWT = "eyJhbGciOiJub25lIn0.e30.test-fixture-key-not-real"


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


class ClientHttpTests(unittest.TestCase):
    def test_posts_raw_authorization_and_json_body(self) -> None:
        captured: dict[str, Request] = {}

        def fake_urlopen(req: Request, timeout: float | None = None):
            captured["req"] = req
            self.assertEqual(timeout, 30)
            return FakeHTTPResponse({"result": [{"linia": "157"}]})

        client = ZtmClient(api_key=FAKE_JWT)
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            lines = client.lines_at_stop("1001", "01")

        self.assertEqual(lines, ["157"])
        req = captured["req"]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(
            req.full_url,
            f"{DEFAULT_BASE_URL}/api/action/{ACTION_LINES_AT_STOP}",
        )
        headers = {key.lower(): value for key, value in req.header_items()}
        self.assertEqual(headers["authorization"], FAKE_JWT)
        self.assertFalse(headers["authorization"].lower().startswith("bearer"))
        self.assertNotIn("token ", headers["authorization"].lower())
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(req.unredirected_hdrs.get("Authorization"), FAKE_JWT)
        self.assertEqual(
            json.loads(req.data.decode("utf-8")),
            {"busstopId": "1001", "busstopNr": "01"},
        )

    def test_departures_sends_line_and_normalizes_values(self) -> None:
        def fake_urlopen(req: Request, timeout: float | None = None):
            self.assertTrue(req.full_url.endswith(ACTION_DEPARTURES))
            self.assertEqual(
                json.loads(req.data.decode("utf-8")),
                {"busstopId": "2002", "busstopNr": "07", "line": "523"},
            )
            return FakeHTTPResponse(
                {
                    "result": [
                        {
                            "values": [
                                {"key": "czas", "value": "08:15:00"},
                                {"key": "kierunek", "value": "CM Północny"},
                            ]
                        }
                    ]
                }
            )

        client = ZtmClient(api_key=FAKE_JWT)
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            rows = client.departures("2002", "07", "523")
        self.assertEqual(rows, [{"czas": "08:15:00", "kierunek": "CM Północny"}])

    def test_vehicle_locations_type_aliases(self) -> None:
        seen: list[int] = []

        def fake_urlopen(req: Request, timeout: float | None = None):
            self.assertTrue(req.full_url.endswith(ACTION_VEHICLE_LOCATIONS))
            body = json.loads(req.data.decode("utf-8"))
            seen.append(body["type"])
            return FakeHTTPResponse(
                [
                    {
                        "Lines": "17",
                        "Lat": 52.23,
                        "Lon": 21.01,
                        "VehicleNumber": "1001",
                        "Brigade": "2",
                        "Time": "2026-09-12 12:00:00",
                    }
                ]
            )

        client = ZtmClient(api_key=FAKE_JWT)
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            buses = client.vehicle_locations("bus")
            trams = client.vehicle_locations("trams")
        self.assertEqual(seen, [1, 2])
        self.assertEqual(buses[0]["Lines"], "17")
        self.assertEqual(trams[0]["VehicleNumber"], "1001")

    def test_busstop_nr_int_is_zero_padded(self) -> None:
        def fake_urlopen(req: Request, timeout: float | None = None):
            self.assertEqual(
                json.loads(req.data.decode("utf-8"))["busstopNr"],
                "03",
            )
            return FakeHTTPResponse([])

        client = ZtmClient(api_key=FAKE_JWT)
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(client.lines_at_stop(9999, 3), [])

    def test_core_has_no_hardcoded_home_stop(self) -> None:
        import dane_um_warszawa.client as client_mod
        import inspect

        source = inspect.getsource(client_mod)
        self.assertNotIn("6045", source)
        self.assertNotIn("Piaski", source)

    def test_repr_does_not_include_full_key(self) -> None:
        client = ZtmClient(api_key=FAKE_JWT)
        self.assertNotIn(FAKE_JWT, repr(client))
        self.assertNotIn(FAKE_JWT, str(client))

    def test_http_error_does_not_include_key(self) -> None:
        def fake_urlopen(req: Request, timeout: float | None = None):
            raise HTTPError(
                req.full_url, 401, "Unauthorized", hdrs=None, fp=BytesIO(b"nope")
            )

        client = ZtmClient(api_key=FAKE_JWT)
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(ApiError) as ctx:
                client.lines_at_stop("1", "01")
        self.assertNotIn(FAKE_JWT, str(ctx.exception))
        self.assertIn("401", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
