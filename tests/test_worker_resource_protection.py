from app.worker import SageWorker


def test_durable_worker_does_not_block_cloud_work_on_busy_host():
    worker = SageWorker(worker_id="test-worker")

    allowed, protection = worker._local_execution_allowed()

    assert allowed is True
    assert protection is None
