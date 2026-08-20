"""Backend application package.

The API imports ``forecasting`` — the feature module it shares with the
notebook — which lives one directory *above* ``backend/``. The Docker image
puts both on ``PYTHONPATH``; a bare ``uvicorn app.main:app`` run from
``backend/`` does not, and fails with ``No module named 'forecasting'``.

Rather than make every run command carry that knowledge (and there is no
portable way to spell ``PYTHONPATH=.. uvicorn ...`` in PowerShell), the
package puts the repository root on ``sys.path`` itself. The API then starts
from any working directory, with or without the environment variable.
"""

from __future__ import annotations

import sys
from importlib.util import find_spec
from pathlib import Path


def _ensure_forecasting_importable() -> None:
    """Add the repository root to ``sys.path`` if ``forecasting`` is not already there."""
    if find_spec("forecasting") is not None:
        return  # Docker, or PYTHONPATH already set - nothing to do.
    repo_root = Path(__file__).resolve().parents[2]
    if (repo_root / "forecasting" / "__init__.py").exists():
        sys.path.insert(0, str(repo_root))


_ensure_forecasting_importable()
