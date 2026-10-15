"""Authenticated identity and onboarding API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from config.settings import settings
from identity.auth import authenticate_request, create_developer_session, get_or_create_authenticated_profile
from identity.memory import add_memory, delete_memory, list_memory, update_memory
from identity.memory_learning import learn_memory_candidates
from identity.onboarding import capability_catalog, validate_capabilities
from identity.otp import OTPRateLimited, otp_manager
from identity.profile import SessionLocal, UserProfile, mark_phone_verified, upsert_profile

router = APIRouter(prefix="/identity", tags=["identity"])

class DeveloperLoginRequest(BaseModel):
    label: str = Field(default="local-owner", max_length=100)

class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1, max_length=10000)

class PhoneRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=30)

class OTPVerifyRequest(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

class OnboardingRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=5, max_length=30)
    address: str = Field(min_length=1, max_length=1000)
    age: int = Field(ge=1, le=120)
    basic_info: dict[str, Any] = Field(default_factory=dict)
    help_intent: str = Field(min_length=1, max_length=2000)
    capabilities: list[str] = Field(default_factory=list, max_length=20)
    memory_consent: bool = False

class MemoryCreateRequest(BaseModel):
    memory_type: str
    content: str = Field(min_length=1, max_length=5000)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="user", min_length=1, max_length=100)
    confirmed: bool = False

class MemoryLearningCandidate(BaseModel):
    memory_type: str
    content: str = Field(min_length=1, max_length=5000)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)


class MemoryLearningRequest(BaseModel):
    candidates: list[MemoryLearningCandidate] = Field(default_factory=list, max_length=20)


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=5, max_length=30)
    address: str | None = Field(default=None, min_length=1, max_length=1000)
    age: int | None = Field(default=None, ge=1, le=120)
    basic_info: dict[str, Any] | None = None
    help_intent: str | None = Field(default=None, min_length=1, max_length=2000)
    capabilities: list[str] | None = Field(default=None, max_length=20)
    memory_consent: bool | None = None


class MemoryUpdateRequest(BaseModel):
    memory_type: str | None = None
    content: str | None = Field(default=None, min_length=1, max_length=5000)
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: str | None = Field(default=None, min_length=1, max_length=100)
    confirmed: bool | None = None

def _profile_from_claims(claims: dict[str, Any]) -> dict[str, Any]:
    return get_or_create_authenticated_profile(claims)


def _requires_phone_verification(claims: dict[str, Any], profile: dict[str, Any]) -> bool:
    """External identities require verified phone; private owner mode does not."""
    return not bool(claims.get("owner_mode")) and not bool(profile.get("phone_verified"))

@router.post("/dev-login")
def developer_login(request: Request, payload: DeveloperLoginRequest):
    if not settings.DEVELOPER_MODE:
        raise HTTPException(status_code=404, detail="Developer mode is disabled.")
    if not request.client or request.client.host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="Developer login is localhost-only.")
    token, claims = create_developer_session(payload.label)
    profile = get_or_create_authenticated_profile(claims)
    return {"success": True, "developer_mode": True, "owner_mode": True, "token": token, "profile": profile}

@router.get("/config")
def identity_config():
    if not settings.GOOGLE_CLIENT_ID and not settings.DEVELOPER_MODE:
        raise HTTPException(status_code=503, detail="Google authentication is not configured and Developer Mode is disabled.")
    return {"success": True, "google_client_id": settings.GOOGLE_CLIENT_ID, "developer_mode": settings.DEVELOPER_MODE, "owner_mode_available": settings.DEVELOPER_MODE or bool(settings.OWNER_AUTH_SUBJECT)}

@router.post("/google")
def google_login(request: GoogleLoginRequest):
    from identity.auth import verify_google_id_token
    claims = verify_google_id_token(request.id_token)
    profile = _profile_from_claims(claims)
    return {"success": True, "identity": {"provider": "google", "subject": claims["auth_subject"], "email": claims.get("email"), "email_verified": claims.get("email_verified", False), "owner_mode": claims.get("owner_mode", False)}, "profile": profile, "onboarding_required": not profile["onboarding_completed"]}

@router.get("/me")
def get_me(claims: dict[str, Any] = Depends(authenticate_request)):
    return {"success": True, "profile": _profile_from_claims(claims), "owner_mode": claims.get("owner_mode", False), "developer_mode": claims.get("developer_mode", False), "developer_label": claims.get("developer_label")}

@router.patch("/me")
def update_me(request: ProfileUpdateRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    if request.capabilities is not None:
        capabilities = validate_capabilities(request.capabilities)
    else:
        capabilities = None
    try:
        profile = upsert_profile(
            auth_provider=claims["auth_provider"],
            auth_subject=claims["auth_subject"],
            name=request.name,
            phone=request.phone,
            address=request.address,
            age=request.age,
            basic_info=request.basic_info,
            help_intent=request.help_intent,
            capabilities=capabilities,
            memory_consent=request.memory_consent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "profile": profile}


@router.get("/onboarding/options")
def onboarding_options():
    return {"success": True, **capability_catalog()}

@router.post("/onboarding")
def complete_onboarding(request: OnboardingRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    profile = _profile_from_claims(claims)
    capabilities = validate_capabilities(request.capabilities)
    private_owner = bool(claims.get("owner_mode"))
    if _requires_phone_verification(claims, profile):
        raise HTTPException(status_code=409, detail="Phone verification is required before onboarding can be completed.")
    if not private_owner and profile["phone"] != request.phone:
        raise HTTPException(status_code=409, detail="The verified phone number must match onboarding.")
    updated = upsert_profile(auth_provider=claims["auth_provider"], auth_subject=claims["auth_subject"], email=claims.get("email"), name=request.name, phone=request.phone or None, address=request.address, age=request.age, basic_info=request.basic_info, help_intent=request.help_intent, capabilities=capabilities, memory_consent=request.memory_consent)
    if request.memory_consent:
        add_memory(profile_id=updated["id"], memory_type="preference", content=f"SAGE onboarding capabilities: {', '.join(capabilities) if capabilities else 'none selected'}", importance=0.7, confidence=1.0, source="onboarding", confirmed=True)
    with SessionLocal() as db:
        row = db.query(UserProfile).filter(UserProfile.auth_provider == claims["auth_provider"], UserProfile.auth_subject == claims["auth_subject"]).first()
        if row is None:
            raise HTTPException(status_code=500, detail="Authenticated profile disappeared during onboarding.")
        row.onboarding_completed = 1
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
    return {"success": True, "onboarding_completed": True, "profile": _profile_from_claims(claims)}

@router.post("/phone/send")
def send_phone_otp(request: PhoneRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    try:
        challenge = otp_manager.create_challenge(owner_key, request.phone)
    except OTPRateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    upsert_profile(auth_provider=claims["auth_provider"], auth_subject=claims["auth_subject"], phone=request.phone)
    return {"success": True, "challenge_id": challenge.challenge_id, "expires_at": challenge.expires_at, "delivery": "sms_provider" if otp_manager.provider is not None else "not_configured"}

@router.post("/phone/verify")
def verify_phone_otp(request: OTPVerifyRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    challenge_phone = otp_manager.challenge_phone(owner_key, request.challenge_id)
    profile = _profile_from_claims(claims)
    if challenge_phone is None or challenge_phone != profile["phone"]:
        raise HTTPException(status_code=400, detail="Invalid or expired verification challenge.")
    if not otp_manager.verify(owner_key, request.challenge_id, request.code):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")
    updated = mark_phone_verified(claims["auth_provider"], claims["auth_subject"])
    return {"success": True, "phone_verified": True, "profile": updated}

@router.get("/memory")
def get_profile_memory(claims: dict[str, Any] = Depends(authenticate_request)):
    profile = _profile_from_claims(claims)
    return {"success": True, "memories": list_memory(profile["id"])}

@router.get("/memory/review")
def get_profile_memory_review(claims: dict[str, Any] = Depends(authenticate_request)):
    """List only unconfirmed memories created by consent-gated automatic learning."""
    profile = _profile_from_claims(claims)
    candidates = list_memory(profile["id"], limit=1000)
    pending = [
        memory for memory in candidates
        if memory.get("source") == "auto_learning" and not memory.get("confirmed", False)
    ]
    return {"success": True, "memories": pending, "count": len(pending)}


@router.post("/memory")
def create_profile_memory(request: MemoryCreateRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    profile = _profile_from_claims(claims)
    return {"success": True, "memory": add_memory(profile_id=profile["id"], memory_type=request.memory_type, content=request.content, importance=request.importance, confidence=request.confidence, source=request.source, confirmed=request.confirmed)}

@router.post("/memory/learn")
def learn_profile_memory(request: MemoryLearningRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    profile = _profile_from_claims(claims)
    return learn_memory_candidates(
        profile_id=profile["id"],
        memory_consent=bool(profile["memory_consent"]),
        candidates=[candidate.model_dump() for candidate in request.candidates],
    )


@router.patch("/memory/{memory_id}")
def edit_profile_memory(memory_id: str, request: MemoryUpdateRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    profile = _profile_from_claims(claims)
    updated = update_memory(memory_id, profile["id"], **request.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"success": True, "memory": updated}

@router.delete("/memory/{memory_id}")
def remove_profile_memory(memory_id: str, claims: dict[str, Any] = Depends(authenticate_request)):
    profile = _profile_from_claims(claims)
    if not delete_memory(memory_id, profile["id"]):
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"success": True, "deleted": True}
