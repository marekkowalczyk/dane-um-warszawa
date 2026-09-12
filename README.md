# dane-um-warszawa

Thin, **universal** Python client and CLI for the City of Warsaw Open Data ZTM API
on [`dane.um.warszawa.pl`](https://dane.um.warszawa.pl).

The library takes **any** `busstopId`, `busstopNr`, and `line`. It does not hardcode
a home stop.

## This is not the legacy API

`dane.um.warszawa.pl` and `api.um.warszawa.pl` are **different systems**.

| | New portal (this client) | Legacy |
| --- | --- | --- |
| Host | `https://dane.um.warszawa.pl` | `https://api.um.warszawa.pl` |
| Auth | JWT in `Authorization` (raw token, **no** `Bearer`, **no** `token ` prefix) | UUID query param `?apikey=` |
| Call | `POST /api/action/<name>` with a JSON body | `GET` with dataset UUIDs |

A JWT from [https://dane.um.warszawa.pl/pl/key-api](https://dane.um.warszawa.pl/pl/key-api)
**will not work** on `api.um.warszawa.pl`. This package does not treat the legacy
API as primary and does not send `?apikey=`.

Official action examples (request/response specimens) are published as
`https://dane.um.warszawa.pl/files/ztm_*_{pw,pa}.json`.

## Install

```bash
pip install -e .
```

Requires Python 3.10+. Stdlib only — no runtime dependencies.

The CLI entrypoint is `dane-um` (`python -m dane_um_warszawa` also works).

## Authentication

Keys are JWTs issued at https://dane.um.warszawa.pl/pl/key-api.

Resolution order:

1. `ZtmClient(api_key=...)` argument
2. Explicit `key_file=` / CLI `--key-file`
3. Environment variable `UM_WARSZAWA_API_KEY`
4. File path from `DANE_UM_KEY_FILE`
5. Default file `~/Downloads/apiKey.txt`

The full token is never printed or logged. Failed auth errors mention the status
code only.

```bash
export UM_WARSZAWA_API_KEY='<jwt from key-api>'
# or
export DANE_UM_KEY_FILE="$HOME/Downloads/apiKey.txt"
```

## Library (any stop)

```python
from dane_um_warszawa import ZtmClient

client = ZtmClient()  # loads the JWT from env or key file

# Any stop pole — pass the ids you care about
lines = client.lines_at_stop("1001", "01")
departures = client.departures("1001", "01", "523")
buses = client.vehicle_locations(1)       # or "bus"
trams = client.vehicle_locations("tram")  # type 2

# Generic POST /api/action/<name>
rows = client.call(
    "get_ztm_lista_linii_na_przystanku",
    {"busstopId": "1001", "busstopNr": "01"},
)
```

Responses are normalized whether the portal returns a bare list, a `{ "result": ... }`
wrapper, or legacy-style `{ "values": [ {"key": ..., "value": ...} ] }` rows.

## CLI

```bash
dane-um lines-at-stop 1001 01
dane-um departures 1001 01 523
dane-um vehicle-locations bus
dane-um vehicle-locations 2
```

`--json` prints the records as JSON. Every command ends with attribution and
the current time in `Europe/Warsaw`.

### Specimen only: Piaski 03

Piaski pole 03 (`busstopId=6045`, `busstopNr=03`) is a documentation example,
not a default in the library:

```bash
dane-um lines-at-stop 6045 03
dane-um departures 6045 03 157
```

## Supported actions

| Action | JSON body |
| --- | --- |
| `get_ztm_lista_linii_na_przystanku` | `{"busstopId", "busstopNr"}` |
| `get_ztm_odjazdy_linii_z_przystanku` | `{"busstopId", "busstopNr", "line"}` |
| `get_ztm_lokalizacja_pojazdow` | `{"type": 1}` buses / `{"type": 2}` trams |

## Attribution

Źródło: Miasto Stołeczne Warszawa / Urząd m.st. Warszawy — https://dane.um.warszawa.pl

Times are shown in Europe/Warsaw.

## License

MIT
