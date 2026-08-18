#!/usr/bin/env python3
"""Weekly Nightscout report generator (v0.2.0).

Fetches last 7 days of BG entries + treatments, then prints a compact
text report: average BG, GMI, time-in-range, standard deviation, CV,
total basal, total bolus, top-10 hypo/hyper events, and a per-day
breakdown.  A --json flag switches to a single JSON object.

Nightscout stores SGV in mg/dL by default. This script converts to mmol/L
(÷18) for display and range checks.

Treatment totals match the schema written by the household logging scripts
(ns-log-insulin): bolus entries use eventType "Insulin" / "Bolus" and basal
entries use "Temp Basal" / "Basal", with the dose in the `insulin` field
(falling back to legacy `amount`).  An entry is either bolus or basal,
never both.

Usage:
    python3 ns-reports.py [--url http://127.0.0.1:1337] [--days 7] [--json]
    NS_ENV=/path/to/nightscout.env python3 ns-reports.py

Reads NS_URL from env (default http://127.0.0.1:1337) and NS_ENV for
the Nightscout .env path (e.g. /path/to/nightscout.env).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import statistics
import sys
import urllib.error
import urllib.request

__version__ = "0.2.0"

MGDL_TO_MMOL = 18.0

# ns-log-insulin writes bolus doses as eventType "Insulin" and Tresiba
# basal as eventType "Temp Basal" (no duration/absolute fields).
BOLUS_TYPES = ("Insulin", "Bolus")
BASAL_TYPES = ("Temp Basal", "Basal")


# ---------------------------------------------------------------------------
# Pure helpers (network-free, unit-testable)
# ---------------------------------------------------------------------------

def treatment_units(t: dict) -> float:
    """Dose units from one treatment: `insulin` field, falling back to `amount`."""
    raw = t.get("insulin")
    if raw is None:
        raw = t.get("amount", 0)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def bolus_total(treatments: list[dict]) -> float:
    """Sum of bolus doses (eventType Insulin|Bolus) using the insulin field."""
    return sum(treatment_units(t) for t in treatments if t.get("eventType") in BOLUS_TYPES)


def basal_total(treatments: list[dict]) -> float:
    """Sum of basal doses (eventType Temp Basal|Basal) using the insulin field."""
    return sum(treatment_units(t) for t in treatments if t.get("eventType") in BASAL_TYPES)


def gmi(mean_mgdl: float) -> float:
    """Glucose Management Indicator (ADA 2018): 3.31 + 0.02392 * mean_mgdl, 1 dp."""
    return round(3.31 + 0.02392 * mean_mgdl, 1)


def cv(mean: float, std: float) -> float:
    """Coefficient of variation: std / mean * 100 (0.0 when mean is 0)."""
    if mean == 0:
        return 0.0
    return std / mean * 100.0


def mmol(bg_mgdl: float) -> float:
    return bg_mgdl / MGDL_TO_MMOL


def in_range(bg_mmol: float) -> bool:
    return 3.9 <= bg_mmol <= 10.0


def daily_breakdown(entries: list[dict], days: int) -> list[dict]:
    """Bucket SGV entries by UTC calendar day.

    Returns one row per day that has >=1 reading, sorted ascending:
    date, readings, avg_bg_mmol, tir_percent, lows (<3.9), highs (>10).
    """
    by_day: dict[dt.date, list[dict]] = {}
    for e in entries:
        sgv = e.get("sgv")
        ms = e.get("date")
        if sgv is None or ms is None:
            continue
        day = dt.datetime.fromtimestamp(ms / 1000.0, tz=dt.timezone.utc).date()
        by_day.setdefault(day, []).append(sgv)

    rows: list[dict] = []
    for day in sorted(by_day):
        vals = [mmol(s) for s in by_day[day]]
        tir = sum(1 for b in vals if in_range(b)) / len(vals) * 100
        rows.append({
            "date": day.isoformat(),
            "readings": len(vals),
            "avg_bg_mmol": round(statistics.mean(vals), 1),
            "tir_percent": round(tir),
            "lows": sum(1 for b in vals if b < 3.9),
            "highs": sum(1 for b in vals if b > 10.0),
        })
    return rows


def build_report(entries: list[dict], treatments: list[dict],
                 days: int, now: dt.datetime | None = None) -> dict:
    """Aggregate everything into the report dict (exact --json key set)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    start = (now - dt.timedelta(days=days)).date()

    bgs_mmol = [mmol(e["sgv"]) for e in entries if e.get("sgv") is not None]
    if bgs_mmol:
        avg = statistics.mean(bgs_mmol)
        std = statistics.pstdev(bgs_mmol)
        tir = sum(1 for b in bgs_mmol if in_range(b)) / len(bgs_mmol) * 100
    else:
        avg = std = tir = 0.0

    return {
        "window_days": days,
        "start_date": start.isoformat(),
        "end_date": now.date().isoformat(),
        "readings": len(bgs_mmol),
        "avg_bg_mmol": round(avg, 1),
        "std_dev_mmol": round(std, 1),
        "gmi_percent": gmi(avg * MGDL_TO_MMOL),
        "cv_percent": round(cv(avg, std)),
        "time_in_range_percent": round(tir),
        "lows": sum(1 for b in bgs_mmol if b < 3.9),
        "highs": sum(1 for b in bgs_mmol if b > 10.0),
        "basal_units": float(round(basal_total(treatments), 1)),
        "bolus_units": float(round(bolus_total(treatments), 1)),
        "daily": daily_breakdown(entries, days),
    }


def render_daily_table(rows: list[dict]) -> list[str]:
    """Fixed-width text table for the daily breakdown section."""
    widths = (11, 10, 7, 7, 6)

    def fmt_row(cells) -> str:
        return "".join(str(c).ljust(w) for c, w in zip(cells, widths)) + str(cells[-1])

    lines = [fmt_row(["Day", "Readings", "Avg", "TIR%", "Lows", "Highs"])]
    for r in rows:
        lines.append(fmt_row([
            r["date"],
            r["readings"],
            f"{r['avg_bg_mmol']:.1f}",
            f"{r['tir_percent']}%",
            r["lows"],
            r["highs"],
        ]))
    return lines


# ---------------------------------------------------------------------------
# Network layer
# ---------------------------------------------------------------------------

def _env_path() -> str:
    path = os.environ.get("NS_ENV")
    if not path:
        raise RuntimeError("NS_ENV must point to your Nightscout .env file")
    return path


def api_hash() -> str:
    path = _env_path()
    with open(path) as f:
        for line in f:
            if line.startswith("API_SECRET="):
                secret = line.split("=", 1)[1].strip()
                return hashlib.sha1(secret.encode()).hexdigest()
    raise RuntimeError("API_SECRET not found in " + path)


def ns_get(base: str, path: str, params: str = "") -> list[dict]:
    url = f"{base}{path}{params}"
    req = urllib.request.Request(url, headers={"API-SECRET": api_hash()})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} from {url}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def fetch_entries(base: str, days: int) -> list[dict]:
    since = int((dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).timestamp() * 1000)
    return ns_get(base, "/api/v1/entries.json", f"?find[date][$gte]={since}&count=10000") or []


def fetch_treatments(base: str, days: int) -> list[dict]:
    # The household logging scripts (ns-log-insulin / ns-log-meal) never set
    # the `date` epoch field — only `created_at` (ISO-8601 UTC). Querying
    # find[date] silently matches nothing and every total reads 0.0 U, so
    # filter on created_at instead. Verified 2026-08-18 against live NS.
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return ns_get(base, "/api/v1/treatments.json", f"?find[created_at][$gte]={since_iso}&count=10000") or []


def fmt_bg(bg_mmol: float) -> str:
    return f"{bg_mmol:.1f} mmol/L"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Weekly Nightscout report")
    p.add_argument("--url", help="Nightscout base URL (default: NS_URL env or http://127.0.0.1:1337)")
    p.add_argument("--days", type=int, default=7, help="Lookback window (default: 7)")
    p.add_argument("--json", action="store_true", help="Emit a single JSON object instead of text")
    args = p.parse_args()

    base = (args.url or os.environ.get("NS_URL") or "http://127.0.0.1:1337").rstrip("/")

    entries = fetch_entries(base, args.days)
    treatments = fetch_treatments(base, args.days)

    report = build_report(entries, treatments, args.days)

    if args.json:
        print(json.dumps(report))
        return 0

    if not entries:
        print("No entries found.")
        return 0

    bgs_mmol = [mmol(e["sgv"]) for e in entries if e.get("sgv") is not None]
    if not bgs_mmol:
        print("No SGV values found.")
        return 0

    lows = sorted(b for b in bgs_mmol if b < 3.9)
    highs = sorted((b for b in bgs_mmol if b > 10.0), reverse=True)

    basal_note = ""
    if not any(t.get("eventType") in BASAL_TYPES for t in treatments):
        basal_note = " (no basal entries in window)"

    print(f"Nightscout report: {report['start_date']} → today ({args.days} days)")
    print(f"  Readings: {report['readings']}")
    print(f"  Average:  {report['avg_bg_mmol']:.1f} mmol/L")
    print(f"  GMI: {report['gmi_percent']}%")
    print(f"  Std dev:  {report['std_dev_mmol']:.1f} mmol/L")
    print(f"  CV: {report['cv_percent']}%")
    print(f"  Time in range: {report['time_in_range_percent']}%")
    print(f"  Lows (<3.9): {report['lows']}")
    print(f"  Highs (>10): {report['highs']}")
    print(f"  Total basal: {report['basal_units']:.1f} U{basal_note}")
    print(f"  Total bolus: {report['bolus_units']:.1f} U")

    if lows:
        print(f"\n  Lowest 5 readings:")
        for b in lows[:5]:
            print(f"    {fmt_bg(b)}")
    if highs:
        print(f"\n  Highest 5 readings:")
        for b in highs[:5]:
            print(f"    {fmt_bg(b)}")

    print("\nDaily breakdown")
    for line in render_daily_table(report["daily"]):
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())