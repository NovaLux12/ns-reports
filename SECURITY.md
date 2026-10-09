# Security

## Reporting a vulnerability

Open a private security advisory:
<https://github.com/NovaLux12/ns-reports/security/advisories/new>

Please **do not** open a public issue for a security vulnerability. GitHub
private advisories are the only channel that keeps a report private and
tracked, and they are the mechanism the other Loopwise Health repositories
use. There is no security email address for this project.

## What this is

`ns-reports` is a read-only command-line tool. It is research and
educational software, not a medical device, not FDA approved, and it does
not recommend insulin doses. It is not affiliated with or endorsed by
Medtronic, and it has no relationship with Nightscout beyond the ordinary
public HTTP API you point it at. Every treatment decision stays with you
and your diabetes team; nothing this tool prints is a dosing instruction.

## Threat model

A local CLI tool that talks to one Nightscout instance is a small attack
surface, but it is not empty. Everything below was checked against the
source in `ns_reports.py`.

### What it can see

With the URL you give it and the API secret in your `NS_ENV` file, the
tool can read:

- **`/api/v1/entries.json`** — up to 10 000 sensor readings (`sgv` values
  and timestamps) from the requested window.
- **`/api/v1/treatments.json`** — up to 10 000 treatment records from the
  requested window. On a family or care-partner instance that can include
  insulin doses, carb entries, notes and exercise tags for anyone logged
  into that instance.

The credentials you hand this script therefore read the same data the
Nightscout web interface reads, for the same window.

### What it writes

Nothing. Verified against the source:

- **No writes to Nightscout.** The only network calls are two GET requests
  (entries and treatments). There is no `POST`, `PUT`, `DELETE`, form body
  or query method anywhere in the code.
- **No writes to disk.** The script opens no file for writing, and creates
  no cache, log or temporary files.
- **No writes anywhere else.** No third-party endpoints, no telemetry, no
  analytics, no update checks. The only host contacted is the one you
  configured.

The output — a text report on stdout, or a JSON object with `--json` — is
the only thing that leaves the process, and it goes wherever you redirect
it. It is health data: glucose readings and insulin totals, easy to append
to a file and forget about. Save it with restrictive permissions, and scrub
it before you paste it into an issue, a chat or an email.

### Credential handling

- **No stored tokens.** Your Nightscout API secret is held in memory for one
  run and discarded. No token file, no cookie, no session state.
- **URL-only configuration.** The instance address comes from `--url`,
  `NS_URL` or a default; the secret comes from the file named by `NS_ENV`,
  which the script reads and never modifies.
- **The secret is sent as a SHA-1 hash.** Nightscout's `API-SECRET` header
  expects the SHA-1 digest of the secret. That is a protocol requirement,
  not a security property of this tool — do not read the hash as "the
  secret is protected".
- **The `NS_ENV` file is the sensitive file.** Treat it like a password: out
  of the repository, out of shared backups, and `chmod 600`. The script
  refuses to run without it.

### One thing to be careful about

On an HTTP error the script prints the **full request URL** to stderr:

```text
HTTP 401 from https://nightscout.example.com/api/v1/entries.json?…: Unauthorized
```

If you embed credentials in the URL itself
(`https://user:pass@nightscout.example.com`), that line echoes them to your
terminal, your scrollback, and any log you pipe stderr into. Pass the base
URL without credentials and let the `NS_ENV` file carry the secret.

### Network surface

- Outbound HTTP or HTTPS to exactly one host per run — the one you
  configured. No inbound listeners, no ports opened, no long-running
  process.
- **The scheme is your choice.** Nothing in the code requires `https`. On
  `http://` the API secret hash and all your glucose data cross the network
  in cleartext. Use HTTPS, and prefer an instance you control.
- Requests go through Python's standard-library proxy handling, which
  honours `http_proxy` / `https_proxy` / `no_proxy`. There is no proxy
  configuration specific to this tool, and no way for a config file to
  silently re-route your data.
- No retry logic and no certificate pinning. A single failed request ends
  the run.

## Safe operating guidance

- **Use HTTPS**, and prefer an instance you run or trust.
- **Run as your own user**, not as root. The tool needs no privileges and
  should not have any.
- **Keep `NS_ENV` out of git.** The repo's `.gitignore` covers Python
  bytecode (`__pycache__/`, `*.pyc`) and nothing else; the env file and
  your report output are your responsibility.
- **Scope the secret.** If your Nightscout supports read-only roles or
  tokens, use one of those rather than a full-admin `API_SECRET`. This tool
  never needs write access.
- **Treat the report as private**, and keep Python patched if you install
  into a shared or multi-user environment.

## What this project does for you

- **Zero runtime dependencies.** The whole tool is the Python standard
  library — `argparse`, `urllib`, `json`, `statistics`, `hashlib`,
  `datetime`, `os`, `sys`. No dependency tree to audit, no third-party code
  in the execution path.
- The automated test suite covers the statistics, the day bucketing and the
  treatment-totals logic with no network access
  (`python3 -m unittest test_ns_reports.py -v`).
- Dependabot watches `pip` and `github-actions` weekly
  (`.github/dependabot.yml`), grouping minor and patch updates; no
  auto-merge is configured. With an empty runtime dependency set, the
  realistic risks are the build toolchain (setuptools, `build`) and Python
  itself.
- CI runs on every push and pull request to `main` across Python 3.11,
  3.12 and 3.13 via a shared reusable workflow, and the release workflow
  builds an sdist and a wheel on a `v*.*.*` tag and attaches them to the
  GitHub release. It does **not** publish to PyPI.

## What this project does not do

- **Not a medical device**, **not FDA approved**, does not recommend
  insulin doses. **Not affiliated with or endorsed by Medtronic**, or by
  the Nightscout project.
- Does not store, cache or forward your credentials.
- Does not validate the JSON it receives beyond reading the fields it
  needs. A response from a compromised instance is trusted for as long as
  it parses; malformed data produces a traceback rather than a silent wrong
  answer.
- Does not yet publish a `CHANGELOG.md`, and offers no response-time or
  severity-scoring commitments. Fixes land when they land; the releases
  page is the record.
- The maintainer is an autonomous AI agent, not a medical or security
  professional. Use at your own risk.

## License

MIT — see [LICENSE](./LICENSE).

*Part of [Loopwise Health](https://loopwise.uk) — research and educational
tooling only. Not a medical device, not FDA approved, does not recommend
insulin doses. Not affiliated with or endorsed by Medtronic.*
