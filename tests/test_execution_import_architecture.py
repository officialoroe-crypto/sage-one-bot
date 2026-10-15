"""Regression tests for the brain/execution package dependency boundary."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_import_script(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_brain_router_can_import_execution_resource_without_cycle():
    result = _run_import_script(
        "import brain.router; import execution.resource; import execution.policy"
    )

    assert result.returncode == 0, result.stderr


def test_execution_policy_can_import_before_brain_router():
    result = _run_import_script(
        "import execution.policy; import brain.router; import execution.resource"
    )

    assert result.returncode == 0, result.stderr


def test_public_execution_exports_remain_available_after_lazy_loading():
    result = _run_import_script(
        "from execution import ResourceGuard, TaskClass, resource_guard, classify_task; "
        "assert ResourceGuard and TaskClass and resource_guard and classify_task"
    )

    assert result.returncode == 0, result.stderr
