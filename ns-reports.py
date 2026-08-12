#!/usr/bin/env python3
"""Weekly Nightscout report generator.

Fetches last 7 days of BG entries + treatments, then prints a compact
text report: average BG, time-in-range, standard deviation, total basal,
total bolus, and top-10 hypo/hyper events.

Nightscout stores SGV in mg/dL by default. This script converts to mmol/L
(÷18) for display and range checks.

Usage:
    python3 ns-reports.py [--url http://127.0.0.1:1337] [--days 7]
    NS_ENV=/home/jack/nightscout/.env python3 ns-reports.py

Reads NS_URL from env (default http://127.0.0.1:1337) and NS_ENV for
the Nightscout .env path (default /home/jack/nightscout/.env).
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

MGDL_TO_MMOL = 18.0


def _env_path() -> str:
    return os.environ.get("NS_ENV", "/home/jack/nightscout/.env")


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
    since = int((dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).timestamp() * 1000)
    return ns_get(base, "/api/v1/treatments.json", f"?find[date][$gte]={since}&count=10000") or []


def mmol(bg_mgdl: float) -> float:
    return bg_mgdl / MGDL_TO_MMOL


def in_range(bg_mmol: float) -> bool:
    return 3.9 <= bg_mmol <= 10.0


def fmt_bg(bg_mmol: float) -> str:
    return f"{bg_mmol:.1f} mmol/L"


def main() -> int:
    p = argparse.ArgumentParser(description="Weekly Nightscout report")
    p.add_argument("--url", help="Nightscout base URL (default: NS_URL env or http://127.0.0.1:1337)")
    p.add_argument("--days", type=int, default=7, help="Lookback window (default: 7)")
    args = p.parse_args()

    base = (args.url or os.environ.get("NS_URL") or "http://127.0.0.1:1337").rstrip("/")

    entries = fetch_entries(base, args.days)
    treatments = fetch_treatments(base, args.days)

    if not entries:
        print("No entries found.")
        return 0

    bgs_mmol = [mmol(e["sgv"]) for e in entries if e.get("sgv") is not None]
    if not bgs_mmol:
        print("No SGV values found.")
        return 0

    avg = statistics.mean(bgs_mmol)
    std = statistics.pstdev(bgs_mmol)
    tir = sum(1 for b in bgs_mmol if in_range(b)) / len(bgs_mmol) * 100

    lows = [b for b in bgs_mmol if b < 3.9]
    highs = [b for b in bgs_mmol if b > 10.0]

    basal = sum(t.get("amount", 0) for t in treatments if t.get("eventType") == "Temp Basal")
    bolus = sum(t.get("amount", 0) for t in treatments if t.get("eventType") == "Bolus")

    start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    print(f"Nightscout report: {start.date()} → today ({args.days} days)")
    print(f"  Readings: {len(bgs_mmol)}")
    print(f"  Average:  {fmt_bg(avg)}")
    print(f"  Std dev:  {std:.1f} mmol/L")
    print(f"  Time in range: {tir:.0f}%")
    print(f"  Lows (<3.9): {len(lows)}")
    print(f"  Highs (>10): {len(highs)}")
    print(f"  Total basal: {basal:.1f} U")
    print(f"  Total bolus: {bolus:.1f} U")

    if lows:
        print(f"\n  Lowest 5 readings:")
        for b in sorted(lows)[:5]:
            print(f"    {fmt_bg(b)}")
    if highs:
        print(f"\n  Highest 5 readings:")
        for b in sorted(highs, reverse=True)[:5]:
            print(f"    {fmt_bg(b)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
