#!/usr/bin/env python3
"""Hyphenated CLI entry point — thin shim over the canonical ns_reports module.

The canonical implementation lives in ns_reports.py (the importable module and
the ``ns-reports`` console-script target). This file exists so
``python ns-reports.py`` keeps working. It loads the canonical module by path —
a plain ``from ns_reports import ...`` would self-import when this file itself
is loaded under the ``ns_reports`` name (as test_ns_reports.py does) — and
re-exports its public API. Do not add logic here; edit ns_reports.py instead.
"""

import importlib.util as _importlib_util
import os as _os

_HERE = _os.path.dirname(_os.path.abspath(__file__))


def _load_canonical():
    spec = _importlib_util.spec_from_file_location(
        "_ns_reports_canonical", _os.path.join(_HERE, "ns_reports.py")
    )
    module = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_canonical = _load_canonical()
globals().update(
    {name: getattr(_canonical, name) for name in dir(_canonical) if not name.startswith("_")}
)
__version__ = _canonical.__version__

if __name__ == "__main__":
    raise SystemExit(_canonical.main())
