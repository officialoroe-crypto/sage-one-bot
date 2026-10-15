from verification.outcome import OutcomeVerifier


def test_required_contains_criterion_passes_from_evidence():
    result = OutcomeVerifier().verify(
        criteria=[{
            "id": "c1",
            "description": "response contains READY",
            "criterion_type": "contains",
            "expected_value": "READY",
            "required": True,
        }],
        result={"success": True},
        evidence=[{"success": True, "result": "System is READY."}],
    )
    assert result.passed is True
    assert result.status == "passed"


def test_required_contains_criterion_fails_without_proof():
    result = OutcomeVerifier().verify(
        criteria=[{
            "id": "c1",
            "description": "response contains READY",
            "criterion_type": "contains",
            "expected_value": "READY",
            "required": True,
        }],
        result={"success": True},
        evidence=[{"success": True, "result": "System is NOT ready."}],
    )
    assert result.passed is False
    assert result.status == "failed"


def test_semantic_criterion_is_deferred_not_assumed():
    result = OutcomeVerifier().verify(
        criteria=[{
            "id": "c1",
            "description": "goal was achieved",
            "criterion_type": "semantic",
            "required": True,
        }],
        result={"success": True},
        evidence=[],
    )
    assert result.passed is False
    assert "requires semantic/manual verification" in result.evidence


def test_optional_criteria_do_not_block():
    result = OutcomeVerifier().verify(
        criteria=[{
            "id": "c1",
            "description": "optional check",
            "criterion_type": "contains",
            "expected_value": "missing",
            "required": False,
        }],
        result=None,
        evidence=[],
    )
    assert result.passed is True
    assert result.status == "no_explicit_criteria"
