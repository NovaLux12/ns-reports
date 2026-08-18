#!/usr/bin/env python3
"""Unit tests for ns-reports v0.2.0 (stdlib only, no network).

Run with: python3 -m unittest test_ns_reports.py -v
"""

import datetime as dt
import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def _import_ns_reports():
    """Load ns-reports.py: hyphenated filenames can't be imported by name."""
    spec = importlib.util.spec_from_file_location(
        "ns_reports", os.path.join(_HERE, "ns-reports.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ns_reports"] = mod
    spec.loader.exec_module(mod)
    return mod


_import_ns_reports()

from ns_reports import (  # noqa: E402
    basal_total,
    bolus_total,
    build_report,
    cv,
    daily_breakdown,
    gmi,
    treatment_units,
)


def _ms(y: int, m: int, d: int, h: int = 12) -> int:
    """Epoch ms for a UTC timestamp (Nightscout `date` field format)."""
    return int(dt.datetime(y, m, d, h, tzinfo=dt.timezone.utc).timestamp() * 1000)


class TreatmentTotalsTest(unittest.TestCase):
    """Regression: ns-log-insulin writes eventType Insulin/Temp Basal with `insulin`."""

    def test_bolus_basal_from_insulin_field(self):
        treatments = [
            {"eventType": "Insulin", "insulin": 4.5},
            {"eventType": "Insulin", "insulin": 2.0},
            {"eventType": "Temp Basal", "insulin": 15.0},
            {"eventType": "Temp Basal", "insulin": 15.0},
        ]
        self.assertAlmostEqual(bolus_total(treatments), 6.5)
        self.assertAlmostEqual(basal_total(treatments), 30.0)

    def test_no_double_counting(self):
        treatments = [
            {"eventType": "Insulin", "insulin": 4.5},          # bolus only
            {"eventType": "Temp Basal", "insulin": 15.0},      # basal only
            {"eventType": "Carb Correction", "insulin": 50.0},  # ignored by both
            {"eventType": "Note", "amount": 99.0},              # ignored by both
        ]
        self.assertAlmostEqual(bolus_total(treatments), 4.5)
        self.assertAlmostEqual(basal_total(treatments), 15.0)

    def test_amount_fallback_legacy_bolus(self):
        treatments = [
            {"eventType": "Bolus", "amount": 3.0},   # legacy bolus
            {"eventType": "Basal", "amount": 10.0},  # legacy basal
        ]
        self.assertAlmostEqual(bolus_total(treatments), 3.0)
        self.assertAlmostEqual(basal_total(treatments), 10.0)

    def test_insulin_takes_precedence_over_amount(self):
        treatments = [{"eventType": "Temp Basal", "insulin": 17.5, "amount": 99.0}]
        self.assertAlmostEqual(basal_total(treatments), 17.5)

    def test_treatment_units_edge_cases(self):
        self.assertAlmostEqual(treatment_units({"insulin": "4.5"}), 4.5)  # string dose
        self.assertAlmostEqual(treatment_units({"amount": 2}), 2.0)        # int amount
        self.assertEqual(treatment_units({"insulin": None, "amount": None}), 0.0)
        self.assertEqual(treatment_units({"insulin": "abc"}), 0.0)         # junk


class GmCvTest(unittest.TestCase):
    def test_gmi_known_inputs(self):
        # ADA 2018 worked example: mean 154 mg/dL -> GMI ~7.0%
        self.assertAlmostEqual(gmi(154.0), 7.0)
        self.assertAlmostEqual(gmi(108.0), 5.9)  # 3.31 + 2.58336
        self.assertAlmostEqual(gmi(126.0), 6.3)  # 3.31 + 3.01392

    def test_cv_math(self):
        self.assertAlmostEqual(cv(5.0, 1.0), 20.0)
        self.assertAlmostEqual(cv(8.0, 4.0), 50.0)
        self.assertEqual(cv(0.0, 0.0), 0.0)  # guard against div-by-zero


class DailyBreakdownTest(unittest.TestCase):
    def test_buckets_by_utc_day(self):
        entries = [
            {"date": _ms(2026, 8, 11, 6), "sgv": 72},    # 4.0 mmol, in range
            {"date": _ms(2026, 8, 11, 9), "sgv": 178},   # 9.89 mmol, in range
            {"date": _ms(2026, 8, 11, 12), "sgv": 181},  # 10.06 mmol, high
            {"date": _ms(2026, 8, 12, 8), "sgv": 70},    # 3.89 mmol, low
            {"date": None, "sgv": 100},                  # no date -> skipped
            {"date": _ms(2026, 8, 12, 10), "sgv": None},  # no sgv -> skipped
        ]
        rows = daily_breakdown(entries, days=7)
        self.assertEqual([r["date"] for r in rows], ["2026-08-11", "2026-08-12"])

        d1, d2 = rows
        self.assertEqual(d1["readings"], 3)
        self.assertAlmostEqual(d1["avg_bg_mmol"], 8.0)  # (4.0 + 9.8889 + 10.0556) / 3
        self.assertEqual(d1["tir_percent"], 67)          # 2 of 3 in range
        self.assertEqual(d1["lows"], 0)
        self.assertEqual(d1["highs"], 1)

        self.assertEqual(d2["readings"], 1)
        self.assertAlmostEqual(d2["avg_bg_mmol"], 3.9)
        self.assertEqual(d2["tir_percent"], 0)
        self.assertEqual(d2["lows"], 1)
        self.assertEqual(d2["highs"], 0)


class BuildReportTest(unittest.TestCase):
    def test_json_key_set_and_values(self):
        now = dt.datetime(2026, 8, 18, 12, 0, tzinfo=dt.timezone.utc)
        entries = [
            {"date": _ms(2026, 8, 11, 6), "sgv": 90},   # 5.0 mmol, in range
            {"date": _ms(2026, 8, 11, 7), "sgv": 200},  # 11.1 mmol, high
        ]
        treatments = [
            {"eventType": "Insulin", "insulin": 4.0},
            {"eventType": "Temp Basal", "insulin": 50.0},
        ]
        r = build_report(entries, treatments, days=7, now=now)

        self.assertEqual(
            set(r.keys()),
            {"window_days", "start_date", "end_date", "readings", "avg_bg_mmol",
             "std_dev_mmol", "gmi_percent", "cv_percent", "time_in_range_percent",
             "lows", "highs", "basal_units", "bolus_units", "daily"},
        )
        self.assertEqual(r["window_days"], 7)
        self.assertEqual(r["start_date"], "2026-08-11")
        self.assertEqual(r["end_date"], "2026-08-18")
        self.assertEqual(r["readings"], 2)
        self.assertEqual(r["basal_units"], 50.0)
        self.assertEqual(r["bolus_units"], 4.0)
        self.assertEqual(r["time_in_range_percent"], 50)
        self.assertEqual(r["lows"], 0)
        self.assertEqual(r["highs"], 1)
        self.assertEqual(len(r["daily"]), 1)
        self.assertEqual(r["daily"][0]["date"], "2026-08-11")


if __name__ == "__main__":
    unittest.main()