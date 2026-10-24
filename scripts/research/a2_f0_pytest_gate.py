"""Pytest plugin that gates the scratch-Kedro controls behind an opt-in.

Load it with ``-p a2_f0_pytest_gate`` and put ``scripts/research`` on
``PYTHONPATH``. The controlled runner ``a2_f0_scratch_kedro_env.py`` does
both.

The plugin registers the ``kedro_scratch`` marker. Without
``A2_F0_KEDRO_OPT_IN=1`` it deselects every marked test. Pytest reports the
count as ``deselected``. A deselected test is not a pass and not a skip. With
the opt-in, the plugin changes nothing. The tests then FAIL when the scratch
interpreter is missing.

The plugin never imports Kedro.
"""

from __future__ import annotations

import os
from typing import Any

MARKER = "kedro_scratch"
OPT_IN_NAME = "A2_F0_KEDRO_OPT_IN"


def opted_in() -> bool:
    """Return ``True`` when the environment explicitly opts in."""
    return os.environ.get(OPT_IN_NAME) == "1"


def pytest_configure(config: Any) -> None:
    """Register the ``kedro_scratch`` marker."""
    config.addinivalue_line(
        "markers",
        f"{MARKER}: needs the scratch Kedro interpreter; opt in with {OPT_IN_NAME}=1",
    )


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Deselect marked tests unless the opt-in variable is ``1``."""
    if opted_in():
        return
    chosen = [item for item in items if MARKER not in item.keywords]
    dropped = [item for item in items if MARKER in item.keywords]
    if not dropped:
        return
    config.hook.pytest_deselected(items=dropped)
    items[:] = chosen
