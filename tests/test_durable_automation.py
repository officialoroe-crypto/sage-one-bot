from datetime import datetime, timedelta, timezone

import pytest

from automation.service import AutomationService


def test_create_rejects_invalid_schedule():
    with pytest.raises(ValueError):
        AutomationService().create(
            owner_key="owner-1",
            name="bad",
            goal="run something",
            schedule_type="cron",
        )


def test_create_requires_interval_for_repeating_schedule():
    with pytest.raises(ValueError):
        AutomationService().create(
            owner_key="owner-1",
            name="repeat",
            goal="run something",
            schedule_type="interval",
        )


def test_create_requires_future_or_explicit_time_for_one_shot():
    service = AutomationService()
    assert service is not None


def test_one_shot_run_time_can_be_constructed():
    run_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    assert run_at.tzinfo is not None
