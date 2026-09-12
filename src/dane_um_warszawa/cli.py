"""Command-line interface for the dane.um.warszawa.pl ZTM actions."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Sequence

from .auth import MissingApiKey
from .client import ZtmClient
from .parse import ApiError

ATTRIBUTION = (
    "Źródło: Miasto Stołeczne Warszawa / Urząd m.st. Warszawy — "
    "https://dane.um.warszawa.pl"
)
def _warsaw_now() -> str:
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Europe/Warsaw")
    now = datetime.now(tz)
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')} Europe/Warsaw"


def _print_footer() -> None:
    # Attribution stays on stderr so --json stdout remains parseable.
    print(ATTRIBUTION, file=sys.stderr)
    print(_warsaw_now(), file=sys.stderr)


def _format_record(record: dict[str, Any]) -> str:
    parts = []
    for key, value in record.items():
        parts.append(f"{key}={value}")
    return "  ".join(parts)


def _cmd_lines_at_stop(client: ZtmClient, args: argparse.Namespace) -> int:
    lines = client.lines_at_stop(args.busstop_id, args.busstop_nr)
    if args.json:
        print(json.dumps(lines, ensure_ascii=False, indent=2))
    elif lines:
        print("\n".join(lines))
    else:
        print("No results.")
    _print_footer()
    return 0


def _cmd_departures(client: ZtmClient, args: argparse.Namespace) -> int:
    rows = client.departures(args.busstop_id, args.busstop_nr, args.line)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif rows:
        for row in rows:
            print(_format_record(row))
    else:
        print("No results.")
    _print_footer()
    return 0


def _cmd_vehicle_locations(client: ZtmClient, args: argparse.Namespace) -> int:
    rows = client.vehicle_locations(args.vehicle_type)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif rows:
        for row in rows:
            print(_format_record(row))
    else:
        print("No results.")
    _print_footer()
    return 0


def _common_flags() -> argparse.ArgumentParser:
    flags = argparse.ArgumentParser(add_help=False)
    flags.add_argument(
        "--key-file",
        help="JWT file (default: DANE_UM_KEY_FILE or ~/Downloads/apiKey.txt)",
    )
    flags.add_argument(
        "--json",
        action="store_true",
        help="Print records as JSON (attribution goes to stderr)",
    )
    return flags


def _build_parser() -> argparse.ArgumentParser:
    flags = _common_flags()
    parser = argparse.ArgumentParser(
        prog="dane-um",
        description=(
            "Universal client for the City of Warsaw Open Data ZTM API "
            "(dane.um.warszawa.pl). Not the legacy api.um.warszawa.pl UUID API."
        ),
        parents=[flags],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    lines = sub.add_parser(
        "lines-at-stop",
        help="Lines serving a stop pole",
        parents=[flags],
    )
    lines.add_argument("busstop_id", help="Stop group id (busstopId), e.g. 1001")
    lines.add_argument("busstop_nr", help="Pole number (busstopNr), e.g. 01")
    lines.set_defaults(func=_cmd_lines_at_stop)

    deps = sub.add_parser(
        "departures",
        help="Departures of a line from a stop pole",
        parents=[flags],
    )
    deps.add_argument("busstop_id", help="Stop group id (busstopId)")
    deps.add_argument("busstop_nr", help="Pole number (busstopNr)")
    deps.add_argument("line", help="Line id, e.g. 157 or N11")
    deps.set_defaults(func=_cmd_departures)

    veh = sub.add_parser(
        "vehicle-locations",
        help="Live bus (1) or tram (2) positions",
        parents=[flags],
    )
    veh.add_argument(
        "vehicle_type",
        help="1/bus/buses or 2/tram/trams",
    )
    veh.set_defaults(func=_cmd_vehicle_locations)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        client = ZtmClient(key_file=args.key_file)
    except MissingApiKey as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        return int(args.func(client, args))
    except ApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
