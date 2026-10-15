from app.worker import SageWorker


def test_research_agent_uses_research_pipeline(monkeypatch):
    captured = {}

    def synthesize(**kwargs):
        captured.update(kwargs)
        return {
            'success': True,
            'question': kwargs['question'],
            'claim_count': 2,
        }

    def fail_orchestrator(*args, **kwargs):
        raise AssertionError('research tasks must not use the generic orchestrator path')

    monkeypatch.setattr(
        'app.worker.research_synthesis_engine.synthesize',
        synthesize,
    )
    monkeypatch.setattr(
        'app.worker.orchestrator.execute_goal',
        fail_orchestrator,
    )

    worker = SageWorker(worker_id='test-worker')
    result = worker._execute_task_payload({
        'id': 'research-task-1',
        'description': 'Research: latest battery technology',
        'agent': 'research',
        'session_id': 'session-1',
        'priority': 3,
    })

    assert result['success'] is True
    assert result['claim_count'] == 2
    assert captured == {
        'question': 'latest battery technology',
    }


def test_non_research_agent_uses_parallel_mission_execution_path(monkeypatch):
    captured = {}

    def plan(**kwargs):
        captured['plan'] = kwargs
        return {'mission': {'id': 'mission-general-1'}}

    def execute_mission(**kwargs):
        captured['execution'] = kwargs
        return {'success': True, 'status': 'completed'}

    monkeypatch.setattr('app.worker.planner.plan', plan)
    monkeypatch.setattr(
        'app.worker.parallel_mission_executor.execute_mission',
        execute_mission,
    )

    worker = SageWorker(worker_id='test-worker')
    result = worker._execute_task_payload({
        'id': 'general-task-1',
        'description': 'Plan my next action',
        'agent': 'general',
        'session_id': 'session-1',
        'priority': 4,
    })

    assert result['success'] is True
    assert result['mission_id'] == 'mission-general-1'
    assert captured['plan'] == {
        'goal': 'Plan my next action',
        'session_id': 'session-1',
        'priority': 4,
    }
    assert captured['execution'] == {
        'mission_id': 'mission-general-1',
        'max_steps': 20,
    }
