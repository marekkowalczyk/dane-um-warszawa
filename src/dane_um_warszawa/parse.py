"""Normalize dane.um.warszawa.pl / CKAN-style ZTM payloads."""

from __future__ import annotations

from typing import Any


LINE_KEYS = ("linia", "line", "Lines")


class ApiError(RuntimeError):
    """API or HTTP error. Messages must never include the JWT."""


def _error_message(error: Any) -> str:
    if isinstance(error, str) and error.strip():
        return error
    if isinstance(error, dict):
        for key in ("message", "Message", "__type", "error"):
            value = error.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return str(error)
    return str(error)


def _raise_if_error_payload(payload: Any) -> None:
    if isinstance(payload, str) and payload.strip():
        raise ApiError(payload)
    if not isinstance(payload, dict):
        return
    if payload.get("success") is False:
        raise ApiError(_error_message(payload.get("error") or payload))
    error = payload.get("error")
    if error:
        raise ApiError(_error_message(error))


def _unwrap_result(payload: Any) -> Any:
    _raise_if_error_payload(payload)
    if isinstance(payload, dict) and "result" in payload:
        return _unwrap_result(payload["result"])
    return payload


def _flatten_values(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    values = item.get("values")
    if not isinstance(values, list) or not values:
        return item
    pairs: dict[str, Any] = {}
    for entry in values:
        if not isinstance(entry, dict):
            return item
        key = entry.get("key", entry.get("Key"))
        if key is None:
            return item
        value = entry.get("value", entry.get("Value"))
        pairs[str(key)] = value
    return pairs


def normalize_records(payload: Any) -> list[dict[str, Any]]:
    """Return a list of dicts from a list, ``result`` wrapper, or values rows."""
    if payload is None:
        return []
    result = _unwrap_result(payload)
    if result is None:
        return []
    if isinstance(result, dict):
        if isinstance(result.get("records"), list):
            result = result["records"]
        else:
            result = [result]
    if not isinstance(result, list):
        raise ApiError(f"Unexpected API payload type: {type(result).__name__}")

    records: list[dict[str, Any]] = []
    for item in result:
        if isinstance(item, str):
            records.append({"linia": item})
            continue
        flat = _flatten_values(item)
        if isinstance(flat, dict):
            records.append(flat)
    return records


def extract_line_ids(records: list[dict[str, Any]]) -> list[str]:
    """Pull line identifiers from mixed record shapes."""
    lines: list[str] = []
    for record in records:
        found = False
        for key in LINE_KEYS:
            if key in record and record[key] not in (None, ""):
                lines.append(str(record[key]))
                found = True
                break
        if not found and len(record) == 1:
            value = next(iter(record.values()))
            if value not in (None, ""):
                lines.append(str(value))
    return lines
