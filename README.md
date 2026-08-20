# ns-reports

[![CI](https://github.com/NovaLux12/ns-reports/actions/workflows/ci.yml/badge.svg)](https://github.com/NovaLux12/ns-reports/actions/workflows/ci.yml) [![Release](https://github.com/NovaLux12/ns-reports/actions/workflows/release.yml/badge.svg)](https://github.com/NovaLux12/ns-reports/actions/workflows/release.yml)

Weekly Nightscout report generator (v0.2.0). Fetches last 7 days of BG entries + treatments, then prints a compact text report.

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

## Usage

```bash
python3 ns-reports.py [--url http://127.0.0.1:1337] [--days 7] [--json]
```

Reads `NS_URL` from env (default `http://127.0.0.1:1337`) and `NS_ENV` for the path to your Nightscout `.env` file (e.g. `~/.nightscout.env`).

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

## Tests

```bash
python -m pytest -q
# or stdlib only:
python3 -m unittest test_ns_reports.py -v
```

## Requirements

- Python 3.9+ (stdlib only, no dependencies)
- Nightscout instance with API_SECRET