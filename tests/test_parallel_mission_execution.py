import threading
import time

import execution.parallel as parallel_module
from execution.parallel import ParallelMissionExecutor


class FakeMissionEngine:
    def __init__(self):
        self.wave = 0
        self.tasks = {
            'a': {'id': 'a', 'status': 'pending', 'verification_status': 'pending'},
            'b': {'id': 'b', 'status': 'pending', 'verification_status': 'pending'},
            'c': {'id': 'c', 'status': 'pending', 'verification_status': 'pending'},
        }

    def refresh_mission_status(self, mission_id):
        if all(
            task['status'] == 'completed'
            and task['verification_status'] == 'verified'
            for task in self.tasks.values()
        ):
            status = 'completed'
        elif any(task['status'] == 'running' for task in self.tasks.values()):
            status = 'executing'
        else:
            status = 'executing'
        return {'id': mission_id, 'status': status}

    def get_ready_tasks(self, mission_id):
        if self.wave == 0:
            return [self.tasks['a'], self.tasks['c']]
        if self.wave == 1:
            return [self.tasks['b']]
        return []

    def get_tasks(self, mission_id):
        return list(self.tasks.values())


class FakeExecutionEngine:
    active = 0
    peak = 0
    lock = threading.Lock()
    calls = []
    mission_engine = None

    def __init__(self):
        pass

    def execute_task(self, task_id):
        with self.lock:
            type(self).active += 1
            type(self).peak = max(type(self).peak, type(self).active)
            type(self).calls.append(task_id)

        time.sleep(0.03)

        with self.lock:
            type(self).active -= 1

        self.mission_engine.tasks[task_id]['status'] = 'completed'
        self.mission_engine.tasks[task_id]['verification_status'] = 'verified'
        return {'success': True, 'task_id': task_id, 'status': 'verified'}


def test_parallel_executor_runs_independent_tasks_concurrently_and_dependencies_in_next_wave(monkeypatch):
    fake_mission = FakeMissionEngine()
    FakeExecutionEngine.active = 0
    FakeExecutionEngine.peak = 0
    FakeExecutionEngine.calls = []
    FakeExecutionEngine.mission_engine = fake_mission

    monkeypatch.setattr(parallel_module, 'mission_engine', fake_mission)

    executor = ParallelMissionExecutor(
        max_parallel=2,
        engine_factory=FakeExecutionEngine,
    )

    original_get_ready = fake_mission.get_ready_tasks

    def get_ready_with_wave(mission_id):
        ready = original_get_ready(mission_id)
        fake_mission.wave += 1
        return ready

    monkeypatch.setattr(fake_mission, 'get_ready_tasks', get_ready_with_wave)

    result = executor.execute_mission('mission-1', max_steps=5)

    assert result['success'] is True
    assert result['status'] == 'completed'
    assert result['waves'] == 2
    assert result['summary']['verified_tasks'] == 3
    assert result['summary']['progress_percent'] == 100.0
    assert FakeExecutionEngine.peak == 2
    assert set(FakeExecutionEngine.calls[:2]) == {'a', 'c'}
    assert FakeExecutionEngine.calls[2] == 'b'


def test_parallel_executor_respects_max_parallel(monkeypatch):
    fake_mission = FakeMissionEngine()
    FakeExecutionEngine.active = 0
    FakeExecutionEngine.peak = 0
    FakeExecutionEngine.calls = []
    FakeExecutionEngine.mission_engine = fake_mission

    monkeypatch.setattr(parallel_module, 'mission_engine', fake_mission)

    executor = ParallelMissionExecutor(
        max_parallel=1,
        engine_factory=FakeExecutionEngine,
    )

    fake_mission.wave = 1
    result = executor.execute_mission('mission-1', max_steps=1)

    assert result['success'] is False
    assert result['status'] == 'max_steps_reached'
    assert FakeExecutionEngine.peak == 1
    assert len(FakeExecutionEngine.calls) == 1
