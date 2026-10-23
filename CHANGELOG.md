# Changelog

All notable changes to `ns-reports` are documented here. The project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for the
**package** version. The `version` string inside the report's own
docstring tracks the package version.

## Unreleased

`main` is ahead of the `v0.2.0` tag. These changes are on `main` but not
in any release yet — see the note under "Releases" below.

### Packaging

- **First packaging.** `pyproject.toml` (setuptools backend, `requires-python
  = ">=3.9"`), `MANIFEST.in`, and an importable `ns_reports` module with a
  `ns-reports` console script. `ns-reports.py` (hyphenated) is now a thin
  shim over `ns_reports.py`, so both filenames work and there is one
  canonical implementation. This landed **after** the `v0.2.0` tag, so
  `v0.2.0` was a script-only release — see below.
- Not published to PyPI. The project is installed from git
  (`pipx install git+https://github.com/NovaLux12/ns-reports.git`).

### Fixed

- **`daily_breakdown` ignored its `days` window.** It bucketed whatever
  entries it was handed, so out-of-window days leaked into the report while
  `start_date` / `end_date` still claimed the requested window. It now
  filters buckets to `[start, end]`, with the window computed the same way
  `build_report` computes it.

### CI and docs

- CI moved to the shared `NovaLux12/.github` reusable workflow, then to a
  Python 3.11–3.13 matrix matching the README's claim.
- The declared `requires-python = ">=3.9"` floor is now actually tested
  (3.9 and 3.10 added) rather than claimed.
- `USER-GUIDE.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
  and `.github/CODEOWNERS` added.
- README install/usage/dev sections polished; Loopwise Health banner and
  footer added.

## v0.2.0 — 2026-08-18

First tagged release. `ns-reports` fetches the last 7 days of BG entries
and treatments from a Nightscout instance and prints a compact text
report. Python 3.9+, standard library only, no dependencies.

This release predates the packaging work, so it ships as a script:
`python3 ns-reports.py`. There is no `pyproject.toml` and no importable
module in this tag.

### Added

- **The report.** Average BG, GMI (ADA 2018), standard deviation, CV%,
  time in range (3.9–10.0 mmol/L), hypo/hyper counts and extremes, total
  basal and bolus from treatments, and a per-UTC-day breakdown (readings,
  average, TIR%, lows, highs).
- **`--json` output.** A single JSON object instead of the text report.
- **CLI.** `--url` (defaults to `NS_URL`, then `http://127.0.0.1:1337`),
  `--days` (default 7) and `--json`.
- **Tests.** `test_ns_reports.py`, runnable with
  `python3 -m unittest test_ns_reports.py -v`.

### Fixed

- **Insulin and basal totals were read from the wrong schema.** Now read
  the `ns-log-insulin` shape: bolus entries are `eventType` `Insulin` /
  `Bolus`, basal entries are `Temp Basal` / `Basal`, and the dose is the
  `insulin` field (falling back to legacy `amount`). An entry is counted
  as either bolus or basal, never both.
- **Treatment lookups matched nothing.** `ns-log-insulin` only ever sets
  `created_at`, never the `date` epoch field, so `find[date][]` returned
  nothing and totals always read 0.0 U. Treatments are now queried by
  `created_at`.
- **A hardcoded home path was removed.** `NS_ENV` must now point at the
  Nightscout `.env` file explicitly — no `/home/<user>` path is baked in.

### Changed

- The `main/build_report/daily_breakdown` complexity was reduced by
  extracting helpers (`_bg_stats`, `_bucket_sgv_entries`,
  `_daily_rows_from_buckets`, `_extract_bgs`, `_render_extremes`,
  `_render_text_report`).

## Releases

GitHub releases are cut from `v`-prefixed tags (`v0.2.0`, …) by
[`.github/workflows/release.yml`](.github/workflows/release.yml), which
builds an sdist and a wheel and attaches them.

**`v0.2.0` has no binary assets.** The tag was pushed on 2026-08-18, two
days *before* the release workflow was added (2026-08-20), so the workflow
never ran for it — and the tagged tree has no `pyproject.toml`, so it could
not have been packaged anyway. The release was therefore created directly
from the tag, with these notes as its body.
