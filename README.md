# ns-reports

[![CI](https://github.com/NovaLux12/ns-reports/actions/workflows/ci.yml/badge.svg)](https://github.com/NovaLux12/ns-reports/actions/workflows/ci.yml) [![Release](https://github.com/NovaLux12/ns-reports/actions/workflows/release.yml/badge.svg)](https://github.com/NovaLux12/ns-reports/actions/workflows/release.yml) [![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/) [![Python 3.11-3.13](https://img.shields.io/badge/tested-3.11%E2%80%933.13-green)](https://github.com/NovaLux12/ns-reports/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Weekly Nightscout report generator (v0.2.0). Fetches last 7 days of BG entries + treatments, then prints a compact text report. Zero dependencies — Python stdlib only.

## Install

```bash
# clone and run directly (no install)
git clone https://github.com/NovaLux12/ns-reports.git
cd ns-reports
python3 ns-reports.py --help

# isolated CLI via pipx
pipx install git+https://github.com/NovaLux12/ns-reports.git
ns-reports --help

# pip in a venv
pip install .
```

Requires Python 3.9+ (tested on 3.11–3.13). No third-party deps.

## Usage

```bash
python3 ns-reports.py [--url http://127.0.0.1:1337] [--days 7] [--json]
ns-reports --days 7 --json > report.json
python3 ns-reports.py --url https://your-ns.example.com --days 14
```

Reads `NS_URL` from env (default `http://127.0.0.1:1337`) and `NS_ENV` for the path to your Nightscout `.env` file (e.g. `~/.nightscout.env` containing `API_SECRET`).

```
$ python3 ns-reports.py --help
usage: ns_reports.py [-h] [--url URL] [--days DAYS] [--json]
  --url URL    Nightscout base URL (default: NS_URL env or http://127.0.0.1:1337)
  --days DAYS  Lookback window (default: 7)
  --json       Emit a single JSON object instead of text
```

`--json` prints a single JSON object instead of text:

```json
{
  "window_days": 7,
  "start_date": "2026-08-11",
  "end_date": "2026-08-18",
  "readings": 2009,
  "avg_bg_mmol": 8.7,
  "std_dev_mmol": 3.2,
  "gmi_percent": 7.2,
  "cv_percent": 36,
  "time_in_range_percent": 65,
  "lows": 96,
  "highs": 610,
  "basal_units": 50.0,
  "bolus_units": 120.5,
  "daily": [
    {"date": "2026-08-11", "readings": 287, "avg_bg_mmol": 8.1, "tir_percent": 62, "lows": 12, "highs": 84}
  ]
}
```

## Output

- Average BG, GMI (ADA 2018), standard deviation, CV%
- Time in range (3.9–10.0 mmol/L)
- Hypo/hyper counts and extremes
- Total basal and bolus (from treatments)
- Daily breakdown (per UTC day: readings, avg, TIR%, lows, highs)

Treatment totals use the schema written by the household logging scripts
(`ns-log-insulin`): bolus entries are `eventType` `Insulin`/`Bolus` and basal
entries are `Temp Basal`/`Basal`, with the dose in the `insulin` field
(falling back to legacy `amount`). Entries are never double-counted.

## Development

```bash
python -m pytest -q
python3 -m unittest test_ns_reports.py -v
python -m py_compile ns_reports.py
pip install build && python -m build
```

Stdlib only — `pytest` and `build` are the only dev extras (CI installs `pytest`).

## License

MIT — see [LICENSE](LICENSE).
