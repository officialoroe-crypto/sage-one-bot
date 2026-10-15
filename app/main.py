from __future__ import annotations

import json
import os
from pathlib import Path
import uuid
from typing import Any, Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.core import sage
from agentic.engine import action_engine
from agentic.models import ActionRequest
from brain.router import router
from database.connection import SessionLocal, Base, engine
from database import repository
from database.models import DeveloperProposal
from sales.models import SalesActivity, SalesLead

from missions.engine import mission_engine
from missions.planner import planner
from execution.engine import execution_engine
from execution.trace import execution_trace

from permissions.engine import permissions
from tools.registry import registry
from agents.manager import agents
from tasks.engine import tasks
from notifications.service import list_notifications, mark_read, mark_all_read
from missions.api import router as mission_api_router
from identity.api import router as identity_api_router
from world_intelligence.api import router as world_api_router
from economy.api import router as economy_api_router
from workflows.api import router as workflow_api_router
from opportunities.api import router as opportunities_api_router
from learning.api import router as learning_api_router
from app.worker_service import worker_service
from config.settings import settings
from identity.auth import authenticate_request, get_or_create_authenticated_profile
from workflows.repository import repository as workflow_repository
from dev_agent.agent import DevelopmentAgent
from app.security import (
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    validate_production_config,
)


# ============================================================
# APP
# ============================================================

# ============================================================
# API ACCESS BOUNDARY
# ============================================================

_PUBLIC_PATHS = {
    "/",
    "/health",
    "/worker/health",
    "/identity/config",
    "/identity/dev-login",
    "/identity/google",
    "/identity/onboarding/options",
}


def _require_api_access(request: Request) -> None:
    """Protect the main API while preserving explicit local Developer Mode.

    Developer Mode is a documented localhost-only development boundary. Outside
    that mode, main application routes require a verified identity token.
    Identity and economy routers keep their own endpoint-specific dependencies.
    """
    path = request.url.path
    if request.method == "OPTIONS" or path in _PUBLIC_PATHS:
        return
    if path.startswith("/identity/") or path.startswith("/economy/"):
        return
    if settings.DEVELOPER_MODE:
        client_host = request.client.host if request.client else None
        if client_host in {"127.0.0.1", "::1", "localhost"}:
            return
    authenticate_request(request)


def _require_owner(claims: dict[str, Any] = Depends(authenticate_request)) -> dict[str, Any]:
    """Require the authenticated SAGE owner for global control-plane mutations."""
    if not claims.get("owner_mode", False):
        raise HTTPException(status_code=403, detail="SAGE Owner Authority is required.")
    return claims


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    worker_service.start()
    try:
        yield
    finally:
        worker_service.stop()


# Interactive docs and the OpenAPI schema map the whole API for an attacker, and
# FastAPI serves them outside the auth dependency, so they are off in production.
app = FastAPI(
    dependencies=[Depends(_require_api_access)],
    title="SAGE ONE",
    version="6.0.0",
    description="SAGE ONE personal AI execution core",
    lifespan=_lifespan,
    debug=False,
    docs_url=None if settings.IS_PRODUCTION else "/docs",
    redoc_url=None if settings.IS_PRODUCTION else "/redoc",
    openapi_url=None if settings.IS_PRODUCTION else "/openapi.json",
)


@app.exception_handler(Exception)
async def _unhandled_error(_request: Request, exc: Exception):
    """Never leak stack traces or internals to clients."""
    import logging
    from fastapi.responses import JSONResponse
    logging.getLogger("sage.error").exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


def _cors_origins() -> list[str]:
    configured = os.getenv("SAGE_CORS_ORIGINS", "")
    if configured.strip():
        return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:7357",
        "http://127.0.0.1:7357",
        "https://officialoroe-crypto.github.io",
    ]


_startup_problems = validate_production_config(_cors_origins())
if _startup_problems:
    # Refuse to boot an insecure production deployment rather than run it.
    raise RuntimeError("Unsafe production configuration: " + " ".join(_startup_problems))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)
# Added after CORS so they wrap it (last added = outermost): limits and headers
# apply to every response, including CORS preflights and error responses.
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.MAX_BODY_BYTES)
app.add_middleware(
    RateLimitMiddleware,
    per_minute=settings.RATE_LIMIT_PER_MINUTE,
    auth_per_minute=settings.AUTH_RATE_LIMIT_PER_MINUTE,
    trust_proxy=settings.TRUST_PROXY_HEADERS,
)
app.add_middleware(SecurityHeadersMiddleware, hsts=settings.IS_PRODUCTION)

# Ensure newly introduced durable tables exist when the API starts.
Base.metadata.create_all(bind=engine)

# Mission progress/history/control endpoints are kept in their own router so
# the mobile API surface can evolve without bloating this application module.
app.include_router(mission_api_router)
app.include_router(identity_api_router)
app.include_router(world_api_router)
app.include_router(economy_api_router)
app.include_router(workflow_api_router)
app.include_router(opportunities_api_router)
app.include_router(learning_api_router)


# ============================================================
# REQUEST MODELS
# ============================================================

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    session_id: Optional[str] = None
    goal: Optional[str] = None
    task: Optional[str] = None
    project: Optional[str] = None
    context: Optional[dict[str, Any]] = None


class ExecuteRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=20000)
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    max_steps: int = Field(default=20, ge=1, le=100)


class AutomationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=20000)
    schedule_type: str = Field(default="once", max_length=50)
    run_at: Optional[datetime] = None
    interval_seconds: Optional[int] = Field(default=None, ge=60)
    session_id: Optional[str] = None
    agent: str = "general"
    max_runs: Optional[int] = Field(default=None, ge=1)


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    memory_type: str = Field(default="general", max_length=100)
    importance: int = Field(default=5, ge=1, le=10)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "user"


class PermissionRequest(BaseModel):
    permission: str = Field(min_length=1, max_length=200)
    allowed: bool


class MissionCreateRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=20000)
    priority: int = Field(default=3, ge=1, le=5)
    session_id: Optional[str] = None


class MissionPlanRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=20000)
    session_id: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)


class MissionExecuteRequest(BaseModel):
    max_steps: int = Field(default=20, ge=1, le=100)


class TaskStatusRequest(BaseModel):
    result: Optional[str] = None
    error: Optional[str] = None


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    priority: int = Field(default=3, ge=1, le=5)
    agent: str = Field(default="general", min_length=1, max_length=100)
    session_id: Optional[str] = None
    parent_task_id: Optional[str] = None


class CommandRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)


class DeveloperPreviewRequest(BaseModel):
    task: str = Field(min_length=1, max_length=20000)
    workspace: Optional[str] = None


class DeveloperApplyRequest(BaseModel):
    proposal_id: str = Field(min_length=1, max_length=100)
    approved: bool = False


class SalesRunRequest(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    website: Optional[str] = Field(default=None, max_length=2000)
    instagram: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=5000)
    project_id: Optional[str] = None
    session_id: Optional[str] = None


class SalesFollowUpRequest(BaseModel):
    note: str = Field(min_length=1, max_length=5000)
    status: str = Field(default="planned", min_length=1, max_length=50)


class PremiumTaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    work_key: str = Field(min_length=1, max_length=80)
    priority: int = Field(default=3, ge=1, le=5)
    agent: str = Field(default="general", min_length=1, max_length=100)
    session_id: Optional[str] = None


# ============================================================
# SERIALIZATION HELPERS
# ============================================================

def _serialize(value: Any) -> Any:
    """
    Convert common SAGE/SQLAlchemy/Pydantic objects into JSON-safe data.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): _serialize(item)
            for key, item in value.items()
            if key != "_sa_instance_state"
        }

    if isinstance(value, (list, tuple, set)):
        return [_serialize(item) for item in value]

    if hasattr(value, "model_dump"):
        try:
            return _serialize(value.model_dump())
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        try:
            return {
                str(key): _serialize(item)
                for key, item in value.__dict__.items()
                if key != "_sa_instance_state"
            }
        except Exception:
            pass

    return str(value)


def _context_to_string(context: Optional[dict[str, Any]]) -> str:
    if not context:
        return ""

    try:
        return json.dumps(context, ensure_ascii=False)
    except Exception:
        return str(context)


# ============================================================
# SALES ENGINE
# ============================================================

@app.post("/sales/run")
def run_sales_audit(
    request: SalesRunRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):
    profile = get_or_create_authenticated_profile(claims)
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    if request.project_id:
        with SessionLocal() as db:
            if workflow_repository.get_project(db, profile["id"], request.project_id) is None:
                raise HTTPException(status_code=404, detail="Project not found.")
    payload = {
        "business_name": request.business_name.strip(),
        "website": request.website.strip() if request.website else None,
        "instagram": request.instagram.strip() if request.instagram else None,
        "notes": request.notes.strip() if request.notes else None,
    }
    task = tasks.create(
        title=f"Sales audit: {request.business_name.strip()[:100]}",
        description=json.dumps(payload, ensure_ascii=False),
        priority=3, agent="sales", session_id=request.session_id,
        owner_key=owner_key, profile_id=profile["id"], project_id=request.project_id,
    )
    return {
        "success": True,
        "status": "queued",
        "task": _serialize(task),
        "workflow": "discover_audit_score_lead_intelligence_outreach_approval_history_customer",
    }


@app.get("/sales/leads")
def list_sales_leads(
    status: Optional[str] = None,
    claims: dict[str, Any] = Depends(_require_owner),
):
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    with SessionLocal() as db:
        query = db.query(SalesLead).filter(SalesLead.owner_key == owner_key)
        if status:
            query = query.filter(SalesLead.status == status)
        leads = query.order_by(SalesLead.created_at.desc()).all()
        return {"success": True, "leads": [_serialize(lead) for lead in leads]}


@app.get("/sales/leads/{lead_id}")
def get_sales_lead(lead_id: str, claims: dict[str, Any] = Depends(_require_owner)):
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    with SessionLocal() as db:
        lead = db.query(SalesLead).filter(
            SalesLead.id == lead_id, SalesLead.owner_key == owner_key
        ).first()
        if lead is None:
            raise HTTPException(status_code=404, detail="Sales lead not found.")
        return {"success": True, "lead": _serialize(lead)}


@app.get("/sales/leads/{lead_id}/history")
def get_sales_lead_history(lead_id: str, claims: dict[str, Any] = Depends(_require_owner)):
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    with SessionLocal() as db:
        lead = db.query(SalesLead).filter(
            SalesLead.id == lead_id, SalesLead.owner_key == owner_key
        ).first()
        if lead is None:
            raise HTTPException(status_code=404, detail="Sales lead not found.")
        rows = db.query(SalesActivity).filter(
            SalesActivity.lead_id == lead_id,
            SalesActivity.owner_key == owner_key,
        ).order_by(SalesActivity.created_at.asc()).all()
        return {
            "success": True,
            "lead_id": lead_id,
            "history": [_serialize(row) for row in rows],
        }


@app.post("/sales/leads/{lead_id}/approve-outreach")
def approve_sales_outreach(lead_id: str, claims: dict[str, Any] = Depends(_require_owner)):
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    with SessionLocal() as db:
        lead = db.query(SalesLead).filter(
            SalesLead.id == lead_id, SalesLead.owner_key == owner_key
        ).first()
        if lead is None:
            raise HTTPException(status_code=404, detail="Sales lead not found.")
        try:
            from sales.service import sales_engine
            lead = sales_engine.approve_outreach(db, lead, owner_key)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"success": True, "approved": True, "sent": False, "lead": _serialize(lead)}


@app.post("/sales/leads/{lead_id}/convert-customer")
def convert_sales_customer(lead_id: str, claims: dict[str, Any] = Depends(_require_owner)):
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    with SessionLocal() as db:
        lead = db.query(SalesLead).filter(
            SalesLead.id == lead_id, SalesLead.owner_key == owner_key
        ).first()
        if lead is None:
            raise HTTPException(status_code=404, detail="Sales lead not found.")
        try:
            from sales.service import sales_engine
            lead = sales_engine.convert_customer(db, lead, owner_key)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"success": True, "customer": True, "lead": _serialize(lead)}


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "name": "SAGE ONE",
        "version": "6.0.0",
        "status": "online",
        "architecture": "mission_planner_execution_verification_trace",
        "execution": "enabled",
        "trace": "enabled",
    }


@app.get("/worker/health")
def worker_health():
    """Return liveness-only worker state; never expose task output publicly."""
    health = worker_service.health()
    return {
        "success": True,
        "worker": {
            "enabled": health["enabled"],
            "running": health["running"],
        },
    }


@app.get("/worker/health/details")
def worker_health_details():
    """Authenticated diagnostic worker state for the SAGE UI/developer console."""
    return {"success": True, "worker": worker_service.health()}


@app.get("/orchestrator")
def orchestrator_status():
    return {
        "name": "SAGE ONE",
        "status": "online",
        "components": {
            "brain": True,
            "memory": True,
            "missions": True,
            "tasks": True,
            "execution": True,
            "verification": True,
            "permissions": True,
            "tools": True,
            "agents": True,
            "trace": True,
        },
    }


# ============================================================
# SESSION
# ============================================================

@app.post("/session")
def create_session(claims: dict[str, Any] = Depends(_require_owner)):
    db = SessionLocal()

    try:
        profile = get_or_create_authenticated_profile(claims)
        owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
        session_id = repository.create_session(db, profile_id=profile["id"], owner_key=owner_key)

        session = repository.get_session(db, session_id, owner_key=owner_key)

        if session is not None:
            return {
                "success": True,
                "session": _serialize(session),
            }

        return {
            "success": True,
            "session": {
                "id": str(session_id),
            },
        }

    finally:
        db.close()


@app.get("/session/{session_id}")
def get_session(session_id: str, claims: dict[str, Any] = Depends(_require_owner)):
    db = SessionLocal()

    try:
        owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
        session = repository.get_session(db, session_id, owner_key=owner_key)

        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found",
            )

        return {
            "success": True,
            "session": _serialize(session),
        }

    finally:
        db.close()


@app.get("/session/{session_id}/messages")
def get_session_messages(
    session_id: str,
    limit: int = 50,
    _claims: dict[str, Any] = Depends(_require_owner),
):
    with SessionLocal() as db:
        owner_key = f"{_claims['auth_provider']}:{_claims['auth_subject']}"
        session = repository.get_session(db, session_id, owner_key=owner_key)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        messages = repository.get_messages(db, session_id, limit=max(1, min(limit, 100)))
        messages.reverse()
        return {
            "success": True,
            "session_id": session_id,
            "messages": _serialize(messages),
        }


# ============================================================
# CHAT
# ============================================================

@app.post("/chat")
def chat(
    request: ChatRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):
    try:
        context_parts = []

        if request.goal:
            context_parts.append(f"Current goal: {request.goal}")

        if request.task:
            context_parts.append(f"Current task: {request.task}")

        if request.project:
            context_parts.append(f"Current project: {request.project}")

        extra_context = _context_to_string(request.context)

        if extra_context:
            context_parts.append(f"Additional context: {extra_context}")

        context = "\n".join(context_parts)

        owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
        profile = get_or_create_authenticated_profile(claims)
        session_id = request.session_id

        if not session_id:
            with SessionLocal() as db:
                session_id = repository.create_session(
                    db,
                    profile_id=profile["id"],
                    owner_key=owner_key,
                )
        else:
            with SessionLocal() as db:
                if repository.get_session(db, session_id, owner_key=owner_key) is None:
                    raise HTTPException(status_code=404, detail="Session not found.")

        result = sage.handle(
            user_message=request.message,
            session_id=session_id,
            context=context,
            owner_authorized=bool(claims.get("owner_mode", False)),
        )

        return {
            "success": True,
            "session_id": session_id,
            "response": _serialize(result),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# DIRECT EXECUTION
# ============================================================

@app.post("/execute")
def execute(
    request: ExecuteRequest,
    _claims: dict[str, Any] = Depends(_require_owner),
):
    """
    High-level synchronous execution endpoint.

    Use /execute/background for durable work that must survive the
    HTTP request and be processed by the dedicated worker.
    """

    try:
        plan_result = planner.plan(
            goal=request.goal,
            session_id=request.session_id,
            priority=3,
        )

        plan_result = _serialize(plan_result)

        mission_id = None

        if isinstance(plan_result, dict):
            mission = plan_result.get("mission")

            if isinstance(mission, dict):
                mission_id = mission.get("id")

            if mission_id is None:
                mission_id = plan_result.get("mission_id")

        if mission_id is None:
            raise RuntimeError(
                "Planner completed but did not return a mission ID."
            )

        execution_result = execution_engine.execute_mission(
            mission_id=mission_id,
            max_steps=request.max_steps,
            owner_authorized=True,
        )

        return {
            "success": True,
            "mission_id": mission_id,
            "plan": plan_result,
            "result": _serialize(execution_result),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@app.post("/execute/background")
def execute_background(
    request: ExecuteRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):
    """Queue goal execution as a durable task for the background worker.

    The HTTP process does not perform the AI work. The task is persisted
    first, then the dedicated worker claims it, executes the goal, and stores
    the final result or failure on the task record.
    """

    agent_name = agents.choose(request.goal)
    if not agents.exists(agent_name):
        agent_name = "general"

    profile = get_or_create_authenticated_profile(claims)
    project_id = request.project_id
    if project_id:
        with SessionLocal() as db:
            if workflow_repository.get_project(db, profile["id"], project_id) is None:
                raise HTTPException(status_code=404, detail="Project not found.")

    task = tasks.create(
        title=request.goal.strip()[:120],
        description=request.goal.strip(),
        priority=3,
        agent=agent_name,
        session_id=request.session_id,
        owner_key=f"{claims['auth_provider']}:{claims['auth_subject']}",
        profile_id=profile["id"],
        project_id=project_id,
    )

    return {
        "success": True,
        "status": "queued",
        "message": "Execution queued for the durable background worker.",
        "task": task,
    }


# ============================================================
# UNIFIED COMMAND EXECUTION
# ============================================================

@app.post("/command")
def command(
    request: CommandRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):
    """Queue a user command into the same durable execution path used by SAGE."""
    profile = get_or_create_authenticated_profile(claims)
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    project_id = request.project_id
    if project_id:
        with SessionLocal() as db:
            if workflow_repository.get_project(db, profile["id"], project_id) is None:
                raise HTTPException(status_code=404, detail="Project not found.")

    session_id = request.session_id
    if not session_id:
        with SessionLocal() as db:
            session_id = repository.create_session(
                db,
                profile_id=profile["id"],
                owner_key=owner_key,
            )
    else:
        with SessionLocal() as db:
            if repository.get_session(db, session_id, owner_key=owner_key) is None:
                raise HTTPException(status_code=404, detail="Session not found.")

    with SessionLocal() as db:
        repository.add_message(db, session_id, "user", request.message)

    agent_name = agents.choose(request.message)
    if not agents.exists(agent_name):
        agent_name = "general"

    task = tasks.create(
        title=request.message.strip()[:120],
        description=request.message.strip(),
        priority=request.priority,
        agent=agent_name,
        session_id=session_id,
        owner_key=f"{claims['auth_provider']}:{claims['auth_subject']}",
        profile_id=profile["id"],
        project_id=project_id,
    )
    return {
        "success": True,
        "status": "queued",
        "session_id": session_id,
        "task": task,
    }




@app.post("/sales/leads/{lead_id}/follow-up")
def add_sales_follow_up(
    lead_id: str,
    request: SalesFollowUpRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):
    """Record a human follow-up without sending anything externally."""
    owner_key = _developer_owner_key(claims)
    with SessionLocal() as db:
        lead = db.query(SalesLead).filter(
            SalesLead.id == lead_id,
            SalesLead.owner_key == owner_key,
        ).first()
        if lead is None:
            raise HTTPException(status_code=404, detail="Sales lead not found.")
        if lead.status == "customer":
            raise HTTPException(status_code=409, detail="Customer lead is already converted.")
        activity = SalesActivity(
            id=str(uuid.uuid4()), lead_id=lead.id, owner_key=owner_key,
            event_type="follow_up", status=request.status.strip() or "planned",
            payload_json=json.dumps({"note": request.note.strip()}, ensure_ascii=False),
            created_at=datetime.now(timezone.utc),
        )
        db.add(activity)
        lead.updated_at = datetime.now(timezone.utc)
        db.commit(); db.refresh(activity)
        return {"success": True, "activity": _serialize(activity)}


# ============================================================
# OWNER DEVELOPER MODE
# ============================================================

def _developer_workspace(requested: Optional[str]) -> Path:
    configured = requested or os.getenv("SAGE_WORKSPACE")
    workspace = Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parent.parent
    if not workspace.exists() or not workspace.is_dir():
        raise HTTPException(status_code=400, detail="Developer workspace does not exist.")
    return workspace


def _developer_owner_key(claims: dict[str, Any]) -> str:
    return f"{claims['auth_provider']}:{claims['auth_subject']}"


@app.post("/developer/preview")
def developer_preview(
    request: DeveloperPreviewRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):
    """Inspect and plan a code change without writing files, durably."""
    if not settings.DEVELOPER_MODE:
        raise HTTPException(status_code=403, detail="Developer Mode is disabled.")
    workspace = _developer_workspace(request.workspace)
    result = DevelopmentAgent(str(workspace), apply_changes=False).plan(request.task)
    proposal_id = str(uuid.uuid4())
    with SessionLocal() as db:
        proposal = DeveloperProposal(
            id=proposal_id,
            owner_key=_developer_owner_key(claims),
            task=request.task,
            workspace=str(workspace),
            preview_json=json.dumps(result, default=str),
            status="preview",
        )
        db.add(proposal)
        db.commit()
    return {
        "success": True,
        "proposal_id": proposal_id,
        "status": "preview",
        "requires_approval": True,
        "proposal": result,
    }


@app.get("/developer/proposals/{proposal_id}")
def developer_proposal(
    proposal_id: str,
    claims: dict[str, Any] = Depends(_require_owner),
):
    """Read one owner-scoped Developer Mode proposal across restarts."""
    with SessionLocal() as db:
        proposal = db.query(DeveloperProposal).filter(
            DeveloperProposal.id == proposal_id,
            DeveloperProposal.owner_key == _developer_owner_key(claims),
        ).first()
        if proposal is None:
            raise HTTPException(status_code=404, detail="Developer proposal not found.")
        return {
            "success": True,
            "proposal_id": proposal.id,
            "status": proposal.status,
            "requires_approval": proposal.status == "preview",
            "proposal": json.loads(proposal.preview_json),
            "result": json.loads(proposal.result_json) if proposal.result_json else None,
        }


@app.post("/developer/apply")
def developer_apply(
    request: DeveloperApplyRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):
    """Apply exactly one owner-scoped preview after explicit approval."""
    if not settings.DEVELOPER_MODE:
        raise HTTPException(status_code=403, detail="Developer Mode is disabled.")
    if not request.approved:
        raise HTTPException(status_code=400, detail="Explicit approval is required.")

    owner_key = _developer_owner_key(claims)
    with SessionLocal() as db:
        proposal = db.query(DeveloperProposal).filter(
            DeveloperProposal.id == request.proposal_id,
            DeveloperProposal.owner_key == owner_key,
        ).first()
        if proposal is None:
            raise HTTPException(status_code=404, detail="Developer proposal not found.")
        if proposal.status != "preview":
            raise HTTPException(status_code=409, detail="Developer proposal is no longer applicable.")
        workspace = proposal.workspace
        task = proposal.task

    result = DevelopmentAgent(workspace, apply_changes=True).apply(task)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        proposal = db.query(DeveloperProposal).filter(
            DeveloperProposal.id == request.proposal_id,
            DeveloperProposal.owner_key == owner_key,
        ).first()
        if proposal is None:
            raise HTTPException(status_code=404, detail="Developer proposal disappeared.")
        proposal.approved_at = now
        proposal.applied_at = now
        proposal.result_json = json.dumps(result, default=str)
        proposal.status = "applied" if result.get("success") else "failed"
        db.commit()

    return {
        "success": bool(result.get("success")),
        "proposal_id": request.proposal_id,
        "status": "applied" if result.get("success") else "failed",
        "result": result,
    }


# ============================================================
# DURABLE AUTOMATION
# ============================================================

@app.post("/automation")
def create_automation(
    request: AutomationCreateRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):
    from automation.service import automation

    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    return {
        "success": True,
        "automation": automation.create(
            owner_key=owner_key,
            name=request.name,
            goal=request.goal,
            schedule_type=request.schedule_type,
            run_at=request.run_at,
            interval_seconds=request.interval_seconds,
            session_id=request.session_id,
            agent=request.agent,
            max_runs=request.max_runs,
        ),
    }


@app.get("/automation")
def list_automations(
    claims: dict[str, Any] = Depends(_require_owner),
):
    from automation.service import automation

    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    return {
        "success": True,
        "automations": automation.list(owner_key=owner_key),
    }


@app.delete("/automation/{automation_id}")
def disable_automation(
    automation_id: str,
    claims: dict[str, Any] = Depends(_require_owner),
):
    from automation.service import automation

    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    result = automation.disable(
        owner_key=owner_key,
        automation_id=automation_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Automation not found.")
    return {"success": True, "automation": result}


# ============================================================
# MEMORY
# ============================================================

@app.get("/memory")
def get_memory(_claims: dict[str, Any] = Depends(_require_owner)):
    db = SessionLocal()
    owner_key = f"{_claims['auth_provider']}:{_claims['auth_subject']}"
    profile = get_or_create_authenticated_profile(_claims)

    try:
        memories = repository.get_memories(db, owner_key=owner_key, profile_id=profile["id"])

        return {
            "success": True,
            "memories": _serialize(memories),
        }

    finally:
        db.close()


@app.post("/memory")
def add_memory(
    request: MemoryRequest,
    _claims: dict[str, Any] = Depends(_require_owner),
):
    db = SessionLocal()
    owner_key = f"{_claims['auth_provider']}:{_claims['auth_subject']}"
    profile = get_or_create_authenticated_profile(_claims)

    try:
        memory = repository.add_memory(
            db,
            content=request.content,
            memory_type=request.memory_type,
            importance=request.importance,
            confidence=request.confidence,
            source=request.source,
            owner_key=owner_key,
            profile_id=profile["id"],
        )

        return {
            "success": True,
            "memory": _serialize(memory),
        }

    finally:
        db.close()


# ============================================================
# BRAIN
# ============================================================

@app.get("/brain/health")
def brain_health():
    return _serialize(router.health())


@app.get("/brain/routing")
def brain_routing(description: str):
    """Explain which provider strategy SAGE would use for a task."""
    try:
        return {
            "success": True,
            "routing": _serialize(router.routing(description)),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# TOOLS
# ============================================================

@app.get("/tools")
def list_tools():
    return {
        "success": True,
        "tools": _serialize(registry.list()),
    }


@app.get("/tools/schemas")
def tool_schemas():
    return {
        "success": True,
        "schemas": _serialize(registry.schemas()),
    }


@app.post("/tools/execute")
def execute_tool(
    tool_name: str,
    arguments: Optional[str] = None,
    _claims: dict[str, Any] = Depends(_require_owner),
):
    try:
        parsed_arguments: dict[str, Any] = {}

        if arguments:
            decoded = json.loads(arguments)
            if not isinstance(decoded, dict):
                raise ValueError("Tool arguments must be a JSON object.")
            parsed_arguments = decoded

        result = action_engine.execute(
            ActionRequest(
                tool_name=tool_name,
                arguments=parsed_arguments,
                owner_authorized=True,
                verify=True,
                source="api_tools_execute",
                owner_key=f"{_claims['auth_provider']}:{_claims['auth_subject']}",
            )
        ).to_dict()

        if result.get("success") is True:
            return {
                "success": True,
                "tool": tool_name,
                "result": _serialize(result.get("result")),
            }

        return {
            "success": False,
            "tool": tool_name,
            "error": result.get("error", "Tool execution failed."),
        }

    except Exception:
        import logging
        logging.getLogger("sage.error").exception("tool execution failed")
        return {
            "success": False,
            "tool": tool_name,
            "error": "Tool execution failed.",
        }

# ============================================================
# PERMISSIONS
# ============================================================

@app.get("/permissions")
def get_permissions(_claims: dict[str, Any] = Depends(_require_owner)):
    return {
        "success": True,
        "permissions": _serialize(
            permissions.get_permissions()
        ),
    }


@app.post("/permissions")
def set_permission(
    request: PermissionRequest,
    _claims: dict[str, Any] = Depends(_require_owner),
):
    permissions.set_permission(
        request.permission,
        request.allowed,
    )

    return {
        "success": True,
        "permission": request.permission,
        "allowed": request.allowed,
    }


# ============================================================
# AUDIT
# ============================================================

@app.get("/audit")
def audit(_claims: dict[str, Any] = Depends(_require_owner)):
    db = SessionLocal()

    try:
        owner_key = f"{_claims['auth_provider']}:{_claims['auth_subject']}"
        actions = repository.get_actions(db, owner_key=owner_key)

        return {
            "success": True,
            "actions": _serialize(actions),
        }

    finally:
        db.close()


@app.get("/audit/legacy")
def audit_legacy(_claims: dict[str, Any] = Depends(_require_owner)):
    return {
        "success": True,
        "audit": _serialize(permissions.audit()),
    }


# ============================================================
# TASKS
# ============================================================

@app.post("/tasks")
def create_background_task(
    request: TaskCreateRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):
    profile = get_or_create_authenticated_profile(claims)
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    task = tasks.create(
        title=request.title,
        description=request.description,
        priority=request.priority,
        agent=request.agent,
        session_id=request.session_id,
        parent_task_id=request.parent_task_id,
        owner_key=owner_key,
        profile_id=profile["id"],
    )
    return {
        "success": True,
        "status": "queued",
        "task": task,
    }


@app.post("/tasks/premium")
def create_premium_background_task(
    request: PremiumTaskCreateRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):
    """Queue owner-authorized premium work; pricing comes only from the Spark catalog."""
    from economy.costs import cost_for

    try:
        cost_for(request.work_key)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    task = tasks.create(
        title=request.title,
        description=request.description,
        priority=request.priority,
        agent=request.agent,
        session_id=request.session_id,
        owner_key=owner_key,
        premium_work_key=request.work_key,
    )
    return {"success": True, "status": "queued", "task": task}


@app.get("/tasks")
def get_tasks(
    status: Optional[str] = None,
    claims: dict[str, Any] = Depends(_require_owner),
):
    if status is not None and status not in tasks.VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid task status")

    return {
        "success": True,
        "tasks": tasks.list(status=status),
    }


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "success": True,
        "task": task,
    }


@app.post("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: str,
    claims: dict[str, Any] = Depends(_require_owner),
):
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    task = tasks.cancel(task_id, owner_key=owner_key)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "success": True,
        "task": task,
    }




def _owned_mission_id(mission_id: str, claims: dict[str, Any]) -> str:
    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    mission = mission_engine.get_mission(mission_id, owner_key=owner_key)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission_id

# ============================================================
# MISSIONS
# ============================================================

@app.post("/missions")
def create_mission(request: MissionCreateRequest, claims: dict[str, Any] = Depends(_require_owner)):

    mission = mission_engine.create_mission(
        goal=request.goal,
        priority=request.priority,
        session_id=request.session_id,
        owner_key=f"{claims['auth_provider']}:{claims['auth_subject']}",
    )

    return {
        "success": True,
        "mission": _serialize(mission),
    }


@app.get("/missions/{mission_id}")
def get_mission(mission_id: str, claims: dict[str, Any] = Depends(_require_owner)):

    mission = mission_engine.get_mission(mission_id, owner_key=f"{claims['auth_provider']}:{claims['auth_subject']}")

    if not mission:
        raise HTTPException(
            status_code=404,
            detail="Mission not found",
        )

    return {
        "success": True,
        "mission": _serialize(mission),
    }


@app.post("/missions/plan")
def plan_mission(request: MissionPlanRequest):

    try:
        result = planner.plan(
            goal=request.goal,
            session_id=request.session_id,
            priority=request.priority,
        )

        return {
            "success": True,
            "plan": _serialize(result),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@app.get("/missions/{mission_id}/tasks")
def mission_tasks(mission_id: str, claims: dict[str, Any] = Depends(_require_owner)):

    _owned_mission_id(mission_id, claims)
    return {
        "success": True,
        "tasks": _serialize(
            mission_engine.get_tasks(mission_id)
        ),
    }


@app.get("/missions/{mission_id}/ready")
def mission_ready_tasks(mission_id: str, claims: dict[str, Any] = Depends(_require_owner)):

    _owned_mission_id(mission_id, claims)
    return {
        "success": True,
        "tasks": _serialize(
            mission_engine.get_ready_tasks(mission_id)
        ),
    }


@app.post("/missions/{mission_id}/tasks")
def create_mission_task(
    mission_id: str,
    title: str,
    description: str,
    agent: str = "general",
    priority: int = 3,
    claims: dict[str, Any] = Depends(_require_owner),
):

    _owned_mission_id(mission_id, claims)
    task = mission_engine.create_task(
        mission_id=mission_id,
        title=title,
        description=description,
        agent=agent,
        priority=priority,
    )

    return {
        "success": True,
        "task": _serialize(task),
    }


# ============================================================
# MISSION TASK OPERATIONS
# ============================================================

@app.post("/missions/tasks/{task_id}/start")
def start_task(task_id: str,
    claims: dict[str, Any] = Depends(_require_owner),
):

    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    task = tasks.get(task_id, owner_key=owner_key)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "success": True,
        "task": _serialize(
            mission_engine.start_task(task_id)
        ),
    }


@app.post("/missions/tasks/{task_id}/complete")
def complete_task(
    task_id: str,
    request: TaskStatusRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):

    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    task = tasks.get(task_id, owner_key=owner_key)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "success": True,
        "task": _serialize(
            mission_engine.complete_task(
                task_id,
                result=request.result,
            )
        ),
    }


@app.post("/missions/tasks/{task_id}/fail")
def fail_task(
    task_id: str,
    request: TaskStatusRequest,
    claims: dict[str, Any] = Depends(_require_owner),
):

    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    task = tasks.get(task_id, owner_key=owner_key)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    error = request.error or "Task failed."

    return {
        "success": True,
        "task": _serialize(
            mission_engine.fail_task(
                task_id,
                error=error,
            )
        ),
    }


@app.post("/missions/tasks/{task_id}/verify")
def verify_task(task_id: str,
    claims: dict[str, Any] = Depends(_require_owner),
):

    owner_key = f"{claims['auth_provider']}:{claims['auth_subject']}"
    task = tasks.get(task_id, owner_key=owner_key)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    """
    Manual verification endpoint.

    The execution engine normally performs verification itself.
    This endpoint explicitly marks the task as passed using the
    mission engine's verification API.
    """

    result = mission_engine.verify_task(
        task_id,
        passed=True,
        evidence="Manually verified through SAGE ONE API.",
    )

    return {
        "success": True,
        "task": _serialize(result),
    }


# ============================================================
# MISSION REFRESH
# ============================================================

@app.post("/missions/{mission_id}/refresh")
def refresh_mission(mission_id: str, claims: dict[str, Any] = Depends(_require_owner)):

    _owned_mission_id(mission_id, claims)
    return {
        "success": True,
        "mission": _serialize(
            mission_engine.refresh_mission_status(
                mission_id
            )
        ),
    }


# ============================================================
# MISSION EXECUTION
# ============================================================

@app.post("/missions/{mission_id}/execute")
def execute_mission(
    mission_id: str,
    request: MissionExecuteRequest,
    _claims: dict[str, Any] = Depends(_require_owner),
):

    _owned_mission_id(mission_id, _claims)
    try:
        result = execution_engine.execute_mission(
            mission_id=mission_id,
            max_steps=request.max_steps,
        )

        return _serialize(result)

    except Exception as exc:
        return {
            "success": False,
            "status": "failed",
            "mission_id": mission_id,
            "error": str(exc),
        }


@app.post("/missions/{mission_id}/execute-next")
def execute_next_task(
    mission_id: str,
    _claims: dict[str, Any] = Depends(_require_owner),
):

    _owned_mission_id(mission_id, _claims)
    try:
        result = execution_engine.execute_next(
            mission_id,
            owner_authorized=True,
        )

        return _serialize(result)

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@app.post("/missions/tasks/{task_id}/execute")
def execute_single_task(
    task_id: str,
    _claims: dict[str, Any] = Depends(_require_owner),
):

    try:
        result = execution_engine.execute_task(
            task_id,
            owner_authorized=True,
        )

        return _serialize(result)

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# EXECUTION TRACE
# ============================================================

@app.get("/missions/{mission_id}/trace")
def get_mission_trace(
    mission_id: str,
    _claims: dict[str, Any] = Depends(_require_owner),
):

    _owned_mission_id(mission_id, _claims)

    return _serialize(
        execution_trace.get_mission_trace(
            mission_id
        )
    )


@app.get("/missions/{mission_id}/result")
def get_mission_result(
    mission_id: str,
    _claims: dict[str, Any] = Depends(_require_owner),
):

    _owned_mission_id(mission_id, _claims)

    return _serialize(
        execution_trace.get_mission_result(
            mission_id
        )
    )


@app.get("/missions/{mission_id}/trace/summary")
def get_trace_summary(
    mission_id: str,
    _claims: dict[str, Any] = Depends(_require_owner),
):

    _owned_mission_id(mission_id, _claims)

    trace = execution_trace.get_mission_trace(
        mission_id
    )

    if not trace.get("success"):
        return trace

    return {
        "success": True,
        "mission_id": mission_id,
        "summary": _serialize(
            trace.get("summary")
        ),
    }


# ============================================================
# NOTIFICATIONS
# ============================================================

@app.get("/notifications")
def get_notifications(
    claims: dict[str, Any] = Depends(_require_owner),
    session_id: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
):
    return {
        "success": True,
        "notifications": list_notifications(
            session_id=session_id,
            unread_only=unread_only,
            limit=limit,
            owner_key=f"{claims['auth_provider']}:{claims['auth_subject']}",
        ),
    }


@app.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, _claims: dict[str, Any] = Depends(_require_owner)):
    owner_key = f"{_claims['auth_provider']}:{_claims['auth_subject']}"
    notification = mark_read(notification_id, owner_key=owner_key)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True, "notification": notification}


@app.post("/notifications/read-all")
def read_all_notifications(session_id: Optional[str] = None, _claims: dict[str, Any] = Depends(_require_owner)):
    owner_key = f"{_claims['auth_provider']}:{_claims['auth_subject']}"
    return {
        "success": True,
        "marked_read": mark_all_read(session_id=session_id, owner_key=owner_key),
    }


# ============================================================
# AGENTS
# ============================================================

@app.get("/agents")
def list_agents():

    try:
        return {
            "success": True,
            "agents": _serialize(
                agents.list()
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@app.get("/agents/{agent_name}")
def get_agent(agent_name: str):

    try:
        agent = agents.get(agent_name)

        if not agent:
            raise HTTPException(
                status_code=404,
                detail="Agent not found",
            )

        return {
            "success": True,
            "agent": _serialize(agent),
        }

    except HTTPException:
        raise

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "success": True,
        "service": "SAGE ONE",
        "version": "6.0.0",
        "status": "healthy",
    }
