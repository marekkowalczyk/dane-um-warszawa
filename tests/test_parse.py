"""Flexible response parsing: list, result wrapper, values key/value."""

from __future__ import annotations

import unittest

from dane_um_warszawa.parse import ApiError, extract_line_ids, normalize_records


class NormalizeRecordsTests(unittest.TestCase):
    def test_bare_list_of_dicts(self) -> None:
        payload = [{"Lines": "157", "Lat": 52.2}]
        self.assertEqual(normalize_records(payload), payload)

    def test_result_wrapper(self) -> None:
        payload = {"result": [{"linia": "523"}]}
        self.assertEqual(normalize_records(payload), [{"linia": "523"}])

    def test_ckan_success_wrapper(self) -> None:
        payload = {"help": "…", "success": True, "result": [{"linia": "N11"}]}
        self.assertEqual(normalize_records(payload), [{"linia": "N11"}])

    def test_values_key_value_rows(self) -> None:
        payload = {
            "result": [
                {
                    "values": [
                        {"key": "linia", "value": "157"},
                        {"key": "czas", "value": "12:34:00"},
                    ]
                }
            ]
        }
        self.assertEqual(
            normalize_records(payload),
            [{"linia": "157", "czas": "12:34:00"}],
        )

    def test_empty_result_is_empty_list(self) -> None:
        self.assertEqual(normalize_records({"result": []}), [])
        self.assertEqual(normalize_records(None), [])

    def test_list_of_line_strings(self) -> None:
        self.assertEqual(
            normalize_records(["157", "523"]),
            [{"linia": "157"}, {"linia": "523"}],
        )

    def test_error_string_payload(self) -> None:
        with self.assertRaises(ApiError) as ctx:
            normalize_records("Błędna metoda")
        self.assertIn("Błędna metoda", str(ctx.exception))

    def test_error_object_payload(self) -> None:
        with self.assertRaises(ApiError):
            normalize_records({"error": "Access denied"})

    def test_ckan_success_false(self) -> None:
        with self.assertRaises(ApiError) as ctx:
            normalize_records(
                {"success": False, "error": {"message": "Authorization Error"}}
            )
        self.assertIn("Authorization Error", str(ctx.exception))


class ExtractLineIdsTests(unittest.TestCase):
    def test_reads_linia_line_and_lines_keys(self) -> None:
        records = [
            {"linia": "157"},
            {"line": "523"},
            {"Lines": "N11"},
        ]
        self.assertEqual(extract_line_ids(records), ["157", "523", "N11"])

    def test_single_value_dict_fallback(self) -> None:
        self.assertEqual(extract_line_ids([{"foo": "191"}]), ["191"])


if __name__ == "__main__":
    unittest.main()
