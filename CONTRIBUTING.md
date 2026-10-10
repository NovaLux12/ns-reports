# Contributing to ns-reports

ns-reports is part of [Loopwise Health](https://loopwise.uk) — it reads Nightscout
data and produces weekly Nightscout reports. **Python standard library only: no runtime
dependencies, and please keep it that way.** That constraint is the point of the
project: it has to keep working on whatever Python a T1D's own machine has, for
years, with nobody maintaining it.

## Before you start

Read [README.md](./README.md) first — it is short and explains what the tool
does and, more importantly, what it refuses to do.

If your change is a **new dependency**, stop and open an issue first. Adding one
changes the install story for every user and is a decision, not a detail.

## Workflow

1. Open an issue first for anything non-trivial (typo fixes don't need one).
2. Fork, create a branch.
3. Make the change.
4. Run the tests: `python -m pytest -q` — this is exactly what CI runs.
5. Open a PR against `main`.
6. Wait for review.

CI runs the shared Python workflow on **3.11, 3.12 and 3.13**. Note the gap:
`pyproject.toml` declares `requires-python = ">=3.9"`, but no CI job exercises
3.9 or 3.10. If you touch anything version-sensitive, say which versions you
tested in the PR description.

## Ground rules

These are not negotiable:

- **No new dependencies.** See above.
- **Tests for behaviour changes.** Bug fix? Add a regression test. Refactor with
  no behaviour change? Don't open the PR.
- **No scope creep.** A bug fix and a feature are two PRs.
- **Medical claims are out of scope.** This tool *displays* data that a person
  then acts on. It must never dose, suggest, or adjust insulin — see the
  disclaimer section of the README. PRs that add advice get declined, not
  discussed.
- **No real credentials, tokens or patient data** in code, tests, fixtures or
  example output. Redact even "obviously fake" ones that look real.
- **Keep PRs small.** Large changes get extra review scrutiny.

## Reporting bugs

Open an issue with: what you ran, what you expected, what happened, and your
Python version. If it involves **patient or credential data, do not paste it** —
use the private channel in [SECURITY.md](./SECURITY.md) instead.

## Security vulnerabilities

Not an issue. See [SECURITY.md](./SECURITY.md).

## Code of Conduct

[CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md). In short: be decent. Reports go to
the maintainer and are handled privately.
