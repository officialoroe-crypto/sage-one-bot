from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from world_intelligence.engine import DEFAULT_TOPICS, world_intelligence
from tasks.engine import tasks
from permissions.engine import permissions
from identity.auth import authenticate_request


router = APIRouter(prefix="/world", tags=["world-intelligence"])


class WorldRefreshRequest(BaseModel):
    topics: list[str] = Field(default_factory=list, max_length=6)


class UpgradeProposalRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=10000)
    benefit: str = Field(min_length=1, max_length=10000)
    evidence: list[str] = Field(default_factory=list, max_length=50)


@router.get("/status")
def world_status():
    return world_intelligence.status()


@router.get("/knowledge")
def world_knowledge(limit: int = 20):
    return {"success": True, "knowledge": world_intelligence.list_knowledge(limit)}


@router.get("/due")
def world_due():
    return {"success": True, "topics": world_intelligence.due()}


@router.post("/refresh")
def world_refresh(
    request: WorldRefreshRequest,
    claims: dict = Depends(authenticate_request),
):
    """Queue a durable bounded world refresh instead of doing AI work in HTTP."""
    if not claims.get("owner_mode", False):
        raise HTTPException(status_code=403, detail="SAGE Owner Authority is required.")
    try:
        decision = permissions.check("world.learn", risk="low", owner_authorized=True)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        topics = request.topics or None
        selected = list(topics or DEFAULT_TOPICS)[:world_intelligence.MAX_TOPICS_PER_REFRESH]
        description = "Refresh SAGE World Intelligence: " + " | ".join(selected)

        existing = tasks.list()
        for item in existing:
            if (
                item.get("agent") == "world"
                and item.get("status") in {"pending", "running"}
                and item.get("description") == description
            ):
                return {
                    "success": True,
                    "status": "already_queued",
                    "task": item,
                    "topics": selected,
                }

        task = tasks.create(
            title="World Intelligence Refresh",
            description=description,
            priority=4,
            agent="world",
        )
        return {
            "success": True,
            "status": "queued",
            "task": task,
            "topics": selected,
        }
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/upgrade-proposals")
def create_upgrade_proposal(
    request: UpgradeProposalRequest,
    claims: dict = Depends(authenticate_request),
):
    if not claims.get("owner_mode", False):
        raise HTTPException(status_code=403, detail="SAGE Owner Authority is required.")
    try:
        return world_intelligence.propose_upgrade(
            title=request.title,
            reason=request.reason,
            benefit=request.benefit,
            evidence=request.evidence,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/upgrade-proposals")
def list_upgrade_proposals(limit: int = 20):
    return {
        "success": True,
        "proposals": world_intelligence.list_upgrade_proposals(limit),
    }
