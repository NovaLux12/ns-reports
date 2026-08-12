# ns-reports

Weekly Nightscout report generator. Fetches last 7 days of BG entries + treatments, then prints a compact text report.

## Output

- Average BG, standard deviation
- Time in range (3.9–10.0 mmol/L)
- Hypo/hyper counts and extremes
- Total basal and bolus (from treatments)

## Usage

```bash
python3 ns-reports.py [--url http://127.0.0.1:1337] [--days 7]
```

Reads `NS_URL` from env (default `http://127.0.0.1:1337`) and `NS_ENV` for the path to your Nightscout `.env` file (e.g. `~/.nightscout.env`).

## Requirements

- Python 3.9+ (stdlib only, no dependencies)
- Nightscout instance with API_SECRET
