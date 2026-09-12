"""HTTP client for POST /api/action/<name> on dane.um.warszawa.pl."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any
from urllib.request import Request

from .auth import load_api_key, redact_key
from .parse import ApiError, extract_line_ids, normalize_records

DEFAULT_BASE_URL = "https://dane.um.warszawa.pl"
ACTION_LINES_AT_STOP = "get_ztm_lista_linii_na_przystanku"
ACTION_DEPARTURES = "get_ztm_odjazdy_linii_z_przystanku"
ACTION_VEHICLE_LOCATIONS = "get_ztm_lokalizacja_pojazdow"
VEHICLE_BUSES = 1
VEHICLE_TRAMS = 2

_VEHICLE_TYPE_ALIASES = {
    "1": VEHICLE_BUSES,
    "bus": VEHICLE_BUSES,
    "buses": VEHICLE_BUSES,
    "2": VEHICLE_TRAMS,
    "tram": VEHICLE_TRAMS,
    "trams": VEHICLE_TRAMS,
}


def _as_stop_id(value: Any) -> str:
    return str(value).strip()


def _as_stop_nr(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:02d}"
    text = str(value).strip()
    if text.isdigit():
        return f"{int(text):02d}"
    return text


def _as_line(value: Any) -> str:
    return str(value).strip()


def resolve_vehicle_type(value: Any) -> int:
    if isinstance(value, int) and value in (VEHICLE_BUSES, VEHICLE_TRAMS):
        return value
    key = str(value).strip().lower()
    try:
        return _VEHICLE_TYPE_ALIASES[key]
    except KeyError as exc:
        raise ApiError("vehicle type must be 1/bus or 2/tram") from exc


class ZtmClient:
    """Universal client: any stop id, pole number, and line."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        key_file: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30,
    ) -> None:
        self._api_key = load_api_key(api_key=api_key, key_file=key_file)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def __repr__(self) -> str:
        return f"ZtmClient(base_url={self._base_url!r}, api_key={redact_key(self._api_key)!r})"

    def call(self, action: str, body: dict[str, Any]) -> list[dict[str, Any]]:
        """POST JSON to ``/api/action/<action>`` and normalize the payload."""
        return normalize_records(self._post(action, body))

    def lines_at_stop(self, busstop_id: Any, busstop_nr: Any) -> list[str]:
        records = self.call(
            ACTION_LINES_AT_STOP,
            {"busstopId": _as_stop_id(busstop_id), "busstopNr": _as_stop_nr(busstop_nr)},
        )
        return extract_line_ids(records)

    def departures(self, busstop_id: Any, busstop_nr: Any, line: Any) -> list[dict[str, Any]]:
        return self.call(
            ACTION_DEPARTURES,
            {
                "busstopId": _as_stop_id(busstop_id),
                "busstopNr": _as_stop_nr(busstop_nr),
                "line": _as_line(line),
            },
        )

    def vehicle_locations(self, vehicle_type: Any) -> list[dict[str, Any]]:
        return self.call(
            ACTION_VEHICLE_LOCATIONS,
            {"type": resolve_vehicle_type(vehicle_type)},
        )

    def _post(self, action: str, body: dict[str, Any]) -> Any:
        url = f"{self._base_url}/api/action/{action}"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(url, data=data, method="POST")
        request.add_header("Authorization", self._api_key)
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = getattr(exc, "code", None)
            raise ApiError(f"HTTP {status} from {url}") from None
        except urllib.error.URLError as exc:
            raise ApiError(f"Network error calling {url}: {exc.reason}") from None

        if not raw:
            return []
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError("API returned non-JSON body") from exc
