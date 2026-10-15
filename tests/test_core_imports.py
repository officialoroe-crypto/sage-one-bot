def test_core_imports():
    from database.connection import engine
    from database.models import Task
    from tasks.engine import tasks
    from execution.engine import execution_engine
    assert engine is not None
    assert Task is not None
    assert tasks is not None
    assert execution_engine is not None
