"""Authenticated SAGE Spark, Evolution and Owner controls API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config.settings import settings
from database.connection import SessionLocal
from economy.achievements import record_verified_achievement
from economy.costs import cost_catalog
from economy.currency import cash_out_quote, currency_info
from economy.owner import owner_audit, reset_evolution, reset_spark, set_evolution, set_spark
from economy.service import (
    EVOLUTION_TIERS, evolution_simulation, get_evolution, get_wallet, grant_sparks, premium_transaction,
    refund_premium_sparks, reserve_premium_work, settle_premium_sparks, snapshot, spend_sparks,
)
from economy.spend_ladder import ladder_description, spend_limit
from identity.auth import authenticate_request

router = APIRouter(prefix="/economy", tags=["economy"])


class SparkAmountRequest(BaseModel):
    amount: int = Field(gt=0, le=1_000_000_000)
    reason: str = Field(min_length=1, max_length=200)
    reference: str | None = Field(default=None, max_length=200)


class VerifiedAchievementRequest(BaseModel):
    amount: int = Field(gt=0, le=1_000_000_000)
    reason: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=100)
    source_id: str = Field(min_length=1, max_length=200)
    evidence: dict = Field(min_length=1)


class PremiumTransactionRequest(BaseModel):
    operation_key: str = Field(min_length=1, max_length=200)
    work_key: str = Field(min_length=1, max_length=100)
    metadata: dict = Field(default_factory=dict)


class PremiumTransactionActionRequest(BaseModel):
    operation_key: str = Field(min_length=1, max_length=200)
    reason: str = Field(default="Premium operation failed", min_length=1, max_length=200)


class OwnerSparkRequest(BaseModel):
    amount: int = Field(ge=0, le=2_147_483_647)
    reason: str = Field(min_length=1, max_length=200)


class OwnerEvolutionRequest(BaseModel):
    lifetime_achievement: int = Field(ge=0, le=2_147_483_647)
    tier: str = Field(min_length=1, max_length=100)
    stage: str = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=1, max_length=200)


class OwnerResetRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=200)


class OwnerEvolutionSimulationRequest(BaseModel):
    target_achievement: int = Field(ge=0, le=2_147_483_647)
    duration_ms: int = Field(default=3000, ge=500, le=30_000)


def _owner(claims: dict) -> str:
    return f"{claims['auth_provider']}:{claims['auth_subject']}"



def _serialize_premium(transaction):
    return {
        "id": transaction.id,
        "operation_key": transaction.operation_key,
        "work_key": transaction.work_key,
        "amount": transaction.amount,
        "status": transaction.status,
        "spend_ledger_id": transaction.spend_ledger_id,
        "refund_ledger_id": transaction.refund_ledger_id,
        "created_at": transaction.created_at.isoformat(),
        "settled_at": transaction.settled_at.isoformat() if transaction.settled_at else None,
        "refunded_at": transaction.refunded_at.isoformat() if transaction.refunded_at else None,
    }

def _require_owner(claims: dict) -> str:
    if not claims.get("owner_mode", False):
        raise HTTPException(status_code=403, detail="SAGE Owner Authority is required.")
    return _owner(claims)


@router.get("/me")
def economy_me(claims: dict = Depends(authenticate_request)):
    with SessionLocal() as db:
        return {"success": True, **snapshot(db, _owner(claims))}


@router.get("/payment/status")
def payment_status(claims: dict = Depends(authenticate_request)):
    """Expose provider readiness without pretending a payment provider is configured."""
    _owner(claims)
    configured = bool(settings.PAYMENT_PROVIDER and settings.PAYMENT_SECRET_KEY)
    return {
        "success": True,
        "configured": configured,
        "provider": settings.PAYMENT_PROVIDER or None,
        "mode": "live" if configured else "not_configured",
        "can_create_payment": False,
        "message": (
            "Payment provider credentials are configured."
            if configured
            else "Payment provider is not configured; no payment action is available."
        ),
    }


@router.get("/currency")
def economy_currency(claims: dict = Depends(authenticate_request)):
    """The locked Spark/NPR rule plus whether real-rupee payout is possible."""
    _owner(claims)
    return {"success": True, "currency": currency_info()}


@router.get("/cash-out/quote")
def economy_cash_out_quote(spark: int, claims: dict = Depends(authenticate_request)):
    """Quote only. This never moves money."""
    _owner(claims)
    if spark < 0 or spark > 1_000_000_000:
        raise HTTPException(status_code=422, detail="Spark amount is out of range")
    return {"success": True, "quote": cash_out_quote(spark)}


@router.get("/spend-limit")
def economy_spend_limit(claims: dict = Depends(authenticate_request)):
    """How much SAGE may propose to spend. The owner still approves every spend."""
    owner_key = _owner(claims)
    with SessionLocal() as db:
        wallet = get_wallet(db, owner_key)
        limit = spend_limit(wallet.balance, wallet.lifetime_earned)
    return {"success": True, "spend_limit": limit.to_dict(), "ladder": ladder_description()}


@router.get("/costs")
def economy_costs(claims: dict = Depends(authenticate_request)):
    _owner(claims)
    return {"success": True, "costs": cost_catalog()}


@router.post("/spark/grant")
def spark_grant(request: SparkAmountRequest, claims: dict = Depends(authenticate_request)):
    # Issuance is an internal economy mutation, so it is never self-service.
    owner = _require_owner(claims)
    with SessionLocal() as db:
        entry = grant_sparks(db, owner, request.amount, request.reason, request.reference)
        return {
            "success": True,
            "entry": {"id": entry.id, "delta": entry.delta, "balance_after": entry.balance_after},
        }


@router.post("/spark/spend")
def spark_spend(request: SparkAmountRequest, claims: dict = Depends(authenticate_request)):
    try:
        with SessionLocal() as db:
            entry = spend_sparks(
                db,
                _owner(claims),
                request.amount,
                request.reason,
                request.reference,
            )
            return {
                "success": True,
                "entry": {"id": entry.id, "delta": entry.delta, "balance_after": entry.balance_after},
            }
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _record_verified(request: VerifiedAchievementRequest, claims: dict):
    with SessionLocal() as db:
        event, created = record_verified_achievement(
            db,
            _owner(claims),
            request.amount,
            request.reason,
            request.source_type,
            request.source_id,
            request.evidence,
        )
        profile = get_evolution(db, _owner(claims))
        return {
            "success": True,
            "created": created,
            "event": {
                "id": event.id,
                "source_type": event.source_type,
                "source_id": event.source_id,
                "amount": event.amount,
                "verification_status": event.verification_status,
                "created_at": event.created_at.isoformat(),
            },
            "evolution": {
                "lifetime_achievement": profile.lifetime_achievement,
                "tier": profile.tier,
                "stage": profile.stage,
            },
        }


@router.post("/evolution/achievement")
def evolution_achievement(
    request: VerifiedAchievementRequest,
    claims: dict = Depends(authenticate_request),
):
    # This compatibility/test route is owner-only. Real users must receive
    # Evolution through the internal verified-result settlement pipeline.
    _require_owner(claims)
    try:
        return _record_verified(request, claims)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/evolution/verified-achievement")
def verified_evolution_achievement(
    request: VerifiedAchievementRequest,
    claims: dict = Depends(authenticate_request),
):
    # This endpoint is a controlled development/testing hook, not a public
    # self-award API. Production settlement should be invoked internally.
    _require_owner(claims)
    try:
        return _record_verified(request, claims)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/evolution/tiers")
def evolution_tiers(claims: dict = Depends(authenticate_request)):
    """Return the canonical Evolution rank ladder and achievement thresholds."""
    _owner(claims)
    return {
        "success": True,
        "tiers": [
            {"tier": tier, "threshold": threshold, "order": index + 1}
            for index, (threshold, tier) in enumerate(EVOLUTION_TIERS)
        ],
    }


@router.get("/evolution")
def evolution_me(claims: dict = Depends(authenticate_request)):
    with SessionLocal() as db:
        profile = get_evolution(db, _owner(claims))
        return {
            "success": True,
            "lifetime_achievement": profile.lifetime_achievement,
            "tier": profile.tier,
            "stage": profile.stage,
        }



@router.post("/owner/premium/reserve")
def owner_premium_reserve(
    request: PremiumTransactionRequest,
    claims: dict = Depends(authenticate_request),
):
    owner = _require_owner(claims)
    with SessionLocal() as db:
        transaction = reserve_premium_work(
            db, owner, request.operation_key, request.work_key, request.metadata
        )
        return {"success": True, "transaction": _serialize_premium(transaction)}


@router.post("/owner/premium/settle")
def owner_premium_settle(
    request: PremiumTransactionActionRequest,
    claims: dict = Depends(authenticate_request),
):
    owner = _require_owner(claims)
    with SessionLocal() as db:
        transaction = settle_premium_sparks(db, owner, request.operation_key)
        return {"success": True, "transaction": _serialize_premium(transaction)}


@router.post("/owner/premium/refund")
def owner_premium_refund(
    request: PremiumTransactionActionRequest,
    claims: dict = Depends(authenticate_request),
):
    owner = _require_owner(claims)
    with SessionLocal() as db:
        transaction = refund_premium_sparks(db, owner, request.operation_key, request.reason)
        return {"success": True, "transaction": _serialize_premium(transaction)}


@router.get("/owner/premium/{operation_key}")
def owner_premium_get(
    operation_key: str,
    claims: dict = Depends(authenticate_request),
):
    owner = _require_owner(claims)
    with SessionLocal() as db:
        transaction = premium_transaction(db, owner, operation_key)
        if transaction is None:
            raise HTTPException(status_code=404, detail="Premium operation not found")
        return {"success": True, "transaction": _serialize_premium(transaction)}


@router.get("/owner/status")
def owner_status(claims: dict = Depends(authenticate_request)):
    owner = _require_owner(claims)
    return {
        "success": True,
        "owner_mode": True,
        "god_mode": bool(settings.DEVELOPER_MODE and claims.get("developer_mode")),
        "scope": "internal_sage_development",
        "external_authority": False,
        "owner_key": owner,
    }


@router.get("/owner/audit")
def owner_audit_log(limit: int = 100, claims: dict = Depends(authenticate_request)):
    owner = _require_owner(claims)
    with SessionLocal() as db:
        return {"success": True, "events": owner_audit(db, owner, limit)}


@router.post("/owner/spark/set")
def owner_spark_set(request: OwnerSparkRequest, claims: dict = Depends(authenticate_request)):
    owner = _require_owner(claims)
    with SessionLocal() as db:
        wallet = set_spark(db, owner, request.amount, request.reason)
        return {
            "success": True,
            "spark": {
                "balance": wallet.balance,
                "lifetime_earned": wallet.lifetime_earned,
                "lifetime_spent": wallet.lifetime_spent,
            },
        }


@router.post("/owner/spark/reset")
def owner_spark_reset(request: OwnerResetRequest, claims: dict = Depends(authenticate_request)):
    owner = _require_owner(claims)
    with SessionLocal() as db:
        wallet = reset_spark(db, owner, request.reason)
        return {
            "success": True,
            "spark": {
                "balance": wallet.balance,
                "lifetime_earned": wallet.lifetime_earned,
                "lifetime_spent": wallet.lifetime_spent,
            },
        }


@router.post("/owner/evolution/set")
def owner_evolution_set(request: OwnerEvolutionRequest, claims: dict = Depends(authenticate_request)):
    owner = _require_owner(claims)
    with SessionLocal() as db:
        profile = set_evolution(
            db,
            owner,
            request.lifetime_achievement,
            request.tier,
            request.stage,
            request.reason,
        )
        return {
            "success": True,
            "evolution": {
                "lifetime_achievement": profile.lifetime_achievement,
                "tier": profile.tier,
                "stage": profile.stage,
            },
        }


@router.post("/owner/evolution/simulate")
def owner_evolution_simulate(
    request: OwnerEvolutionSimulationRequest,
    claims: dict = Depends(authenticate_request),
):
    owner = _require_owner(claims)
    with SessionLocal() as db:
        return {
            "success": True,
            **evolution_simulation(db, owner, request.target_achievement, request.duration_ms),
        }


@router.post("/owner/evolution/reset")
def owner_evolution_reset(request: OwnerResetRequest, claims: dict = Depends(authenticate_request)):
    owner = _require_owner(claims)
    with SessionLocal() as db:
        profile = reset_evolution(db, owner, request.reason)
        return {
            "success": True,
            "evolution": {
                "lifetime_achievement": profile.lifetime_achievement,
                "tier": profile.tier,
                "stage": profile.stage,
            },
        }
