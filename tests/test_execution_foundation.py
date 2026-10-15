from __future__ import annotations

import time

import pytest

from execution.mode import ConnectivityState, ExecutionMode, mode_router
from execution.resource import ResourceGuard, ResourceSnapshot
from execution.scheduler import ExecutionScheduler


def test_online_offline_mode_router():
    assert mode_router.select(ConnectivityState(online=True)) is ExecutionMode.ONLINE
    assert mode_router.select(ConnectivityState(online=False)) is ExecutionMode.OFFLINE


def test_resource_guard_thresholds():
    guard = ResourceGuard(soft_cpu_percent=50, hard_cpu_percent=70, sample_interval=0)
    low = ResourceSnapshot(20, None, 4, time.time())
    soft = ResourceSnapshot(55, None, 4, time.time())
    hard = ResourceSnapshot(75, None, 4, time.time())

    assert guard.allows(low)
    assert not guard.should_throttle(low)
    assert guard.should_throttle(soft)
    assert not guard.should_block(soft)
    assert not guard.allows(hard)
    assert guard.should_block(hard)


def test_scheduler_runs_work():
    guard = ResourceGuard(sample_interval=0)
    scheduler = ExecutionScheduler(max_workers=1, guard=guard)
    try:
        task_id = scheduler.submit(lambda: "done")
        deadline = time.time() + 2
        while time.time() < deadline:
            status = scheduler.status(task_id)
            if status["status"] == "completed":
                assert status["result"] == "done"
                return
            time.sleep(0.01)
        pytest.fail("scheduled task did not complete")
    finally:
        scheduler.shutdown()


def test_scheduler_blocks_at_hard_cpu_limit():
    guard = ResourceGuard(soft_cpu_percent=50, hard_cpu_percent=70, sample_interval=0)
    scheduler = ExecutionScheduler(max_workers=1, guard=guard)
    try:
        hard = ResourceSnapshot(90, None, 4, time.time())
        scheduler.guard.snapshot = lambda: hard
        with pytest.raises(RuntimeError, match="CPU protection"):
            scheduler.submit(lambda: None)
    finally:
        scheduler.shutdown()
