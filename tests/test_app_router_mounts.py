from app.main import app
from identity.api import router as identity_router
from world_intelligence.api import router as world_router
from economy.api import router as economy_router
from opportunities.api import router as opportunities_router
from learning.api import router as learning_router


def _paths() -> set[str]:
    # FastAPI 0.141+ stores included routers as internal wrapper objects.
    # OpenAPI exposes the actual mounted endpoint paths consistently.
    return set(app.openapi().get("paths", {}))


def test_identity_and_world_router_definitions_exist():
    identity_paths = {route.path for route in identity_router.routes}
    world_paths = {route.path for route in world_router.routes}

    assert "/identity/google" in identity_paths
    assert "/identity/me" in identity_paths
    assert "/identity/me" in identity_paths
    assert "/identity/memory" in identity_paths
    assert "/identity/onboarding" in identity_paths
    assert "/identity/phone/send" in identity_paths
    assert "/identity/phone/verify" in identity_paths
    assert "/economy/owner/status" in {route.path for route in economy_router.routes}
    assert "/economy/me" in {route.path for route in economy_router.routes}
    assert "/economy/payment/status" in {route.path for route in economy_router.routes}
    assert "/world/status" in world_paths
    assert "/world/knowledge" in world_paths
    assert "/world/due" in world_paths
    assert "/world/refresh" in world_paths
    opportunity_paths = {route.path for route in opportunities_router.routes}
    assert "/jobs" in opportunity_paths
    assert "/jobs/mine" in opportunity_paths
    assert "/jobs/applications/mine" in opportunity_paths
    assert "/jobs/{job_id}/applications" in opportunity_paths
    assert "/marketplace/listings" in opportunity_paths
    assert "/marketplace/listings/mine" in opportunity_paths
    assert "/marketplace/inquiries/mine" in opportunity_paths
    learning_paths = {route.path for route in learning_router.routes}
    assert "/learning/paths" in learning_paths
    assert "/learning/lessons/{lesson_id}/complete" in learning_paths


def test_identity_and_world_routers_are_mounted_on_app():
    paths = _paths()

    assert "/identity/google" in paths
    assert "/identity/me" in paths
    assert "/identity/memory" in paths
    assert "/identity/onboarding" in paths
    assert "/identity/phone/send" in paths
    assert "/identity/phone/verify" in paths
    assert "/economy/owner/status" in paths
    assert "/economy/me" in paths
    assert "/economy/payment/status" in paths
    assert "/world/status" in paths
    assert "/world/knowledge" in paths
    assert "/world/due" in paths
    assert "/world/refresh" in paths
    assert "/jobs" in paths
    assert "/jobs/mine" in paths
    assert "/jobs/applications/mine" in paths
    assert "/jobs/{job_id}/applications" in paths
    assert "/marketplace/listings" in paths
    assert "/marketplace/listings/mine" in paths
    assert "/marketplace/inquiries/mine" in paths
    assert "/learning/paths" in paths
    assert "/learning/lessons/{lesson_id}/complete" in paths


def test_app_keeps_mission_routes_separate_from_identity_and_world():
    paths = _paths()
    assert "/missions/identity/google" not in paths
    assert "/missions/world/status" not in paths
