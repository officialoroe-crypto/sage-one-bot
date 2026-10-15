from execution.policy import TaskClass, classify_task, local_execution_allowed
from execution.resource import ResourceBand, ResourceGuard, ResourceSnapshot


def snapshot(cpu: float) -> ResourceSnapshot:
    return ResourceSnapshot(
        cpu_percent=cpu,
        memory_percent=50.0,
        cpu_count=4,
        timestamp=0.0,
    )


def test_task_classification_separates_heavy_work():
    assert classify_task("deep research on competitors") is TaskClass.HEAVY
    assert classify_task("search the web for one fact") is TaskClass.MEDIUM
    assert classify_task("say hello") is TaskClass.LIGHT


def test_local_policy_keeps_heavy_work_off_busy_cpu():
    assert local_execution_allowed(TaskClass.HEAVY, 49.9)
    assert not local_execution_allowed(TaskClass.HEAVY, 50.0)
    assert not local_execution_allowed(TaskClass.LIGHT, 70.0)


def test_resource_bands_match_protection_thresholds():
    assert snapshot(39.9).band is ResourceBand.SAFE
    assert snapshot(40.0).band is ResourceBand.BUSY
    assert snapshot(70.0).band is ResourceBand.HEAVY
    assert snapshot(85.0).band is ResourceBand.CRITICAL


def test_guard_blocks_at_hard_ceiling_and_pauses_at_critical():
    guard = ResourceGuard(soft_cpu_percent=50, hard_cpu_percent=70, critical_cpu_percent=85)
    assert not guard.should_block(snapshot(69.9))
    assert guard.should_block(snapshot(70.0))
    assert not guard.should_pause(snapshot(84.9))
    assert guard.should_pause(snapshot(85.0))
