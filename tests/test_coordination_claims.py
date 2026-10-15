from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib.util

import pytest


MODULE = Path("coordination/claims.py")
spec = importlib.util.spec_from_file_location("sage_coordination_claims", MODULE)
claims = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(claims)


def test_overlap_is_conservative():
    assert claims.overlaps("execution", "execution/engine.py")
    assert claims.overlaps("execution/engine.py", "execution")
    assert not claims.overlaps("memory", "execution")


def test_overlap_rejects_active_claim():
    active = [{
        "id": "one",
        "status": "in_progress",
        "scope": ["execution/engine.py"],
    }]
    with pytest.raises(SystemExit):
        claims.assert_no_overlap(active, ["execution"])


def test_stale_claim_is_detected():
    old = (
        datetime.now(timezone.utc) - timedelta(hours=25)
    ).replace(microsecond=0).isoformat()
    assert claims.stale({"updated_at": old})


def test_fresh_claim_is_not_stale():
    fresh = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    assert not claims.stale({"updated_at": fresh})


def test_parse_empty_claims():
    assert claims.parse_claims(
        "version: 1\nupdated_at: 2026-10-01T00:00:00+00:00\nclaims: []\n"
    ) == []
