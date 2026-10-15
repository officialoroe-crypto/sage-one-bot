"""HTTP surface for mission controls, progress, and durable history."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from missions.engine import mission_engine
from missions.history import append_event, list_events
from missions.intelligence import mission_intelligence


router = APIRouter(prefix="/missions", tags=["missions"])


def _require_mission(mission_id: str) -> dict:
    mission = mission_engine.get_mission(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


def _progress(mission_id: str) -> dict:
    mission = _require_mission(mission_id)
    tasks = mission_engine.get_tasks(mission_id)
    total = len(tasks)
    completed = sum(
        1
        for task in tasks
        if task.get("status") == "completed"
        and task.get("verification_status") == "verified"
    )
    running = sum(1 for task in tasks if task.get("status") == "running")
    failed = sum(1 for task in tasks if task.get("status") == "failed")
    pending = sum(1 for task in tasks if task.get("status") == "pending")

    percent = round((completed / total) * 100, 2) if total else 0.0

    return {
        "mission_id": mission_id,
        "status": mission["status"],
        "progress_percent": percent,
        "total_tasks": total,
        "completed_tasks": completed,
        "running_tasks": running,
        "pending_tasks": pending,
        "failed_tasks": failed,
        "current_task_id": mission.get("current_task_id"),
    }


def _record_control_event(
    mission_id: str,
    *,
    event_type: str,
    status: str,
    message: str,
    metadata: dict | None = None,
) -> dict:
    """Record a mission control action without making history persistence fatal."""
    progress = _progress(mission_id)
    try:
        return append_event(
            mission_id=mission_id,
            event={
                "event_type": event_type,
                "status": status,
                "message": message,
                "wave": 0,
                "task_ids": [],
                "progress_percent": progress["progress_percent"],
                "metadata": metadata or {"source": "mission_api"},
            },
        )
    except Exception:
        # Mission control has already succeeded; history is observability.
        return {}


@router.get("/{mission_id}/progress")
def mission_progress(mission_id: str):
    return {"success": True, "progress": _progress(mission_id)}


@router.get("/{mission_id}/events")
def mission_events(
    mission_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
):
    _require_mission(mission_id)
    return {
        "success": True,
        "mission_id": mission_id,
        "events": list_events(mission_id, limit=limit),
    }


@router.post("/{mission_id}/pause")
def pause_mission(mission_id: str):
    _require_mission(mission_id)
    try:
        mission = mission_intelligence.set_status(mission_id, "paused")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _record_control_event(
        mission_id,
        event_type="mission_paused",
        status="paused",
        message="Mission paused by user.",
    )
    return {"success": True, "action": "pause", "mission": mission}


@router.post("/{mission_id}/resume")
def resume_mission(mission_id: str):
    _require_mission(mission_id)
    try:
        mission = mission_intelligence.set_status(mission_id, "resumed")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _record_control_event(
        mission_id,
        event_type="mission_resumed",
        status="executing",
        message="Mission resumed by user.",
    )
    return {"success": True, "action": "resume", "mission": mission}


@router.post("/{mission_id}/cancel")
def cancel_mission(mission_id: str):
    _require_mission(mission_id)
    try:
        mission = mission_intelligence.set_status(mission_id, "cancelled")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _record_control_event(
        mission_id,
        event_type="mission_cancelled",
        status="cancelled",
        message="Mission cancelled by user.",
    )
    return {"success": True, "action": "cancel", "mission": mission}
