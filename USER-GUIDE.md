# User guide

This guide is for people who want to **use** `ns-reports` to turn their
Nightscout history into a weekly report they can read, save, or feed
into another tool. It assumes you can type a command into a terminal; it
does not assume you are a programmer. To **read or modify** the code,
start with [README.md](./README.md).

> **Not a medical device.** Research and educational tooling only. It
> does not diagnose, recommend insulin doses, or substitute for clinical
> judgement. See [SECURITY.md](./SECURITY.md).

## What this does

`ns-reports` is a single Python script. Given the URL of a Nightscout
instance it downloads the last *N* days of CGM readings (**entries**) and
insulin **treatments**, then prints a one-screen summary: average
glucose, GMI, time in range, variability, hypo / hyper counts, total
basal and bolus, and a per-day table. With `--json` it prints the same
numbers as a single JSON object instead. It runs once and exits — nothing
to leave running, and nothing to configure beyond one URL and one path to
your Nightscout `.env` file. It does not need to run on the same machine
as Nightscout; any computer that can reach the URL works.

## Is this for me?

You need all of these:

- **A Nightscout instance** with history in it — self-hosted, hosted by
  a provider, or a friend's instance you have read access to. If you
  don't have one, [nightscout.info](https://www.nightscout.info/) has
  setup instructions.
- **That instance's API secret** — the long random string set when the
  site was created. You need the value itself, not just browser access.
- **Python 3.9 or newer** (`python3 --version` to check), **`git`**, and
  read access to the data — the script only ever reads.

The packaging metadata declares `requires-python = ">=3.9"`, so 3.9 is
the floor the package claims. The automated test suite, however, only
runs on **3.11, 3.12 and 3.13** (see `.github/workflows/ci.yml`), so
those three are the versions actually exercised on every commit. The code
uses nothing newer than 3.9 features, so 3.9 and 3.10 should work — but
if you have a choice, use 3.11 or newer. Standard library only: nothing
else to install, no build step.

## Install

There is no package on PyPI: `pip install ns-reports` does not work,
because nothing is published there. The supported path is clone and run:

```bash
git clone https://github.com/NovaLux12/ns-reports.git
cd ns-reports
python3 ns-reports.py --help
```

The repo does carry a `pyproject.toml`, so if you would rather have an
`ns-reports` command on your `PATH` you can install from the clone you
already have — the README shows `pipx install git+…` and `pip install .`
as the two options. Both build from the source you downloaded; neither
contacts PyPI.

## Pointing it at your Nightscout

Pass the instance address with `--url`, or export `NS_URL`. If you give
neither it defaults to `http://127.0.0.1:1337`, the address a Nightscout
running on the same machine listens on. A trailing slash is stripped for
you.

The API secret comes from a `.env`-style file whose path you put in
`NS_ENV`. The script looks for a line starting with `API_SECRET=`, strips
whitespace, and sends the **SHA-1 hash** of the value in the `API-SECRET`
header — which is what the Nightscout API expects. It reads that one line
and nothing else from the file. Create it outside the repo so you can't
commit it by accident:

```bash
echo 'API_SECRET=your-nightscout-api-secret' > "$HOME/.nightscout.env"
chmod 600 "$HOME/.nightscout.env"
export NS_ENV="$HOME/.nightscout.env"
```

`NS_ENV` is not optional. The script has no unauthenticated mode: if the
variable is unset it stops with `NS_ENV must point to your Nightscout
.env file`.

## Running it

```bash
python3 ns-reports.py                          # last 7 days, text
python3 ns-reports.py --days 14                # last fortnight
python3 ns-reports.py --days 7 --json          # one JSON object
python3 ns-reports.py --url https://ns.example.com --days 30
```

| Flag | Default | What it does |
|---|---|---|
| `--url` | `NS_URL`, else `http://127.0.0.1:1337` | Base URL of the instance |
| `--days` | `7` | Lookback window, in days |
| `--json` | off | Emit a single JSON object instead of text |

Each run makes two requests — entries and treatments — with a 30-second
timeout each, asking for up to 10 000 records per request. There is no
retry logic: a request that fails fails the run.

## Reading the report

A text run prints a block like this (these are the numbers from the
sample output in [README.md](./README.md); yours will differ):

```
Nightscout report: 2026-08-11 → today (7 days)
  Readings: 2009
  Average:  8.7 mmol/L
  GMI: 7.2%
  Std dev:  3.2 mmol/L
  CV: 36%
  Time in range: 65%
  Lows (<3.9): 96
  Highs (>10): 610
  Total basal: 50.0 U
  Total bolus: 120.5 U
```

| Metric | What it means |
|---|---|
| `Readings` | Sensor values in the window. Every number below comes from these, so this is your sanity check that data arrived. |
| `Average` | Mean glucose in mmol/L, one decimal place. |
| `GMI` | Glucose Management Indicator: `3.31 + 0.02392 × mean(mg/dL)`, the ADA 2018 formula. An estimate of HbA1c derived from your average glucose, not a lab result. |
| `Std dev` | Population standard deviation of the readings, in mmol/L. Some other tools average per-day standard deviations instead, which gives a different number. |
| `CV` | Coefficient of variation: std dev ÷ mean × 100, as a whole percent. The same variability idea, but relative to your average, so it compares across people and weeks. |
| `Time in range` | Percentage of readings between 3.9 and 10.0 mmol/L inclusive. The daily table uses the same range, bucketed by **UTC** day, oldest first; days with no data are absent rather than shown as zeros. |
| `Lows` / `Highs` | Counts of readings below 3.9 and above 10.0 mmol/L — **readings, not episodes**, so one long hypo that produced six readings counts six times. Both thresholds are fixed; there is no flag to change them. |
| `Total basal` / `Total bolus` | Insulin units summed from the treatments endpoint — see below. |

Below the totals sit the five lowest and five highest readings in the
window, in mmol/L.

`--json` prints exactly the same numbers as one JSON object on one line,
with keys `window_days`, `start_date`, `end_date`, `readings`,
`avg_bg_mmol`, `std_dev_mmol`, `gmi_percent`, `cv_percent`,
`time_in_range_percent`, `lows`, `highs`, `basal_units`, `bolus_units`
and `daily` (an array of `date`, `readings`, `avg_bg_mmol`, `tir_percent`,
`lows`, `highs`), which pipes neatly into `jq`:

```bash
python3 ns-reports.py --json | jq '{avg: .avg_bg_mmol, tir: .time_in_range_percent}'
```

Basal and bolus are summed from treatments, not read from your pump.
Matched event types are `Insulin` / `Bolus` for bolus and
`Temp Basal` / `Basal` for basal, with the dose read from the `insulin`
field, falling back to the legacy `amount` field. Notes, carb corrections
and meals are ignored, and no entry is counted in both totals. If no
basal entries appear in the window the report says
`Total basal: 0.0 U (no basal entries in window)` rather than a silent
zero.

## Troubleshooting

- **`NS_ENV must point to your Nightscout .env file`** — the variable is
  unset or empty.
- **`API_SECRET not found in <path>`** — the check is
  `line.startswith("API_SECRET=")`, so `export API_SECRET=…`,
  `API_SECRET = …` with spaces, or an indented or commented line will not
  match. The line must start at column zero with exactly `API_SECRET=`.
- **`HTTP 401`** — the secret is wrong, or doesn't match what Nightscout
  was configured with. The script sends the SHA-1 hash of the value in
  the file, not the value itself.
- **`HTTP 404`, or `No entries found.`** — almost always a wrong base URL: a
  missing path segment, or the site root when your instance lives under a
  sub-path. `No entries found.` specifically means the request succeeded but
  returned nothing — an empty window or the wrong instance. Open
  `/api/v1/entries.json?count=1` in a browser and confirm it returns JSON,
  then try `--days 30`.
- **Basal and bolus both `0.0 U`** — the treatments query filters on
  `created_at`, not the `date` epoch field, because the household logging
  scripts that write these records never set `date`. Treatments written by
  anything that only sets `date` match nothing. Verified against a live
  instance on 2026-08-18.
- **A `URLError` traceback** — the script handles HTTP error responses
  (`HTTP <code> from <url>`, exit 1) but not transport failures. A refused
  connection, DNS failure or 30-second timeout surfaces as an uncaught
  exception. Retry, or check the URL and your network.
- **The numbers look too low** — check `Readings` first. Gaps where your
  uploader was offline are not filled in, so averages describe only the
  hours actually recorded.

## FAQ

**Does it change anything in my Nightscout?** No — two GET requests,
nothing else. There is no code path that writes.

**Can I run it on a schedule?** A cron job or systemd timer works. Set
`NS_ENV` in the job's environment; it is not read from any config file:

```cron
0 8 * * 1 NS_ENV=$HOME/.nightscout.env NS_URL=https://ns.example.com \
  python3 /home/you/ns-reports/ns-reports.py --json >> /home/you/reports.jsonl
```

**Why is everything in mmol/L?** Nightscout stores mg/dL; the script
divides by 18 for display and range checks. There is no unit flag.

**Is GMI the same as my HbA1c?** It is an estimate from average glucose
using the ADA 2018 formula, not a blood test. The two will not always
agree.

## Disclaimer

Research and educational purposes only. **Not a medical device**, **not
FDA approved**, does not recommend insulin doses. **Not affiliated with or
endorsed by Medtronic**, and no relationship with your Nightscout
instance beyond the read requests you ask it to make. Every treatment
decision stays with you and your diabetes team.

## License

MIT — see [LICENSE](./LICENSE). Part of
[Loopwise Health](https://loopwise.uk) — research and educational tooling
only.
