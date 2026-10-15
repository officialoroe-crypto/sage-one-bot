from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.connection import get_db
from identity.auth import authenticate_request, get_or_create_authenticated_profile
from learning.models import LessonProgress

router = APIRouter(prefix="/learning", tags=["learning"])


# This initial catalog is free, text-first, and designed around practical digital
# skills. Completion is stored per authenticated profile; course content is not
# represented as a paid certificate or an externally accredited qualification.
_PATHS: tuple[dict[str, Any], ...] = (
    {
        "id": "digital-foundations",
        "title": "Digital Foundations",
        "subtitle": "Build safer, more confident everyday digital skills.",
        "level": "Beginner",
        "estimated_minutes": 30,
        "lessons": (
            {
                "id": "digital-files-and-documents",
                "title": "Files, folders and documents",
                "minutes": 8,
                "objective": "Organize your work so it is easy to find and share.",
                "content": (
                    "Create one folder for each project. Use descriptive names and dates "
                    "for important files. Keep an editable copy and a separate backup. "
                    "Before sharing a document, check that it contains only the information "
                    "the recipient needs."
                ),
                "exercise": "Create a project folder and name one document clearly.",
            },
            {
                "id": "digital-online-safety",
                "title": "Online safety and privacy",
                "minutes": 10,
                "objective": "Recognize common risks before you click or share.",
                "content": (
                    "Use unique passwords and a password manager when available. Never send "
                    "one-time codes to someone who contacts you unexpectedly. Verify a link "
                    "by checking the real domain, and pause before uploading identity, bank, "
                    "or private family information to an unfamiliar service."
                ),
                "exercise": "List two details you should verify before opening a login link.",
            },
            {
                "id": "digital-information-checks",
                "title": "Check information before sharing",
                "minutes": 12,
                "objective": "Separate a claim from the evidence that supports it.",
                "content": (
                    "Find the original source, check its publication date, and compare important "
                    "claims with an independent reliable source. A confident tone, screenshot, "
                    "or high number of shares does not by itself prove that a claim is accurate."
                ),
                "exercise": "Choose one online claim and identify its original source and date.",
            },
        ),
    },
    {
        "id": "freelancing-starter",
        "title": "Freelancing Starter",
        "subtitle": "Turn a useful skill into a clear, honest service offer.",
        "level": "Beginner",
        "estimated_minutes": 35,
        "lessons": (
            {
                "id": "freelance-choose-a-service",
                "title": "Choose one service",
                "minutes": 10,
                "objective": "Describe a service that solves a specific customer problem.",
                "content": (
                    "Start with one service you can demonstrate, such as document formatting, "
                    "basic design, translation, video captions, tutoring, or data cleanup. Define "
                    "the customer, what you will deliver, how long it will take, and what is outside "
                    "the scope. Do not promise skills or results you cannot verify."
                ),
                "exercise": "Write a one-sentence service offer and name one deliverable.",
            },
            {
                "id": "freelance-build-a-sample",
                "title": "Build a small portfolio sample",
                "minutes": 12,
                "objective": "Show evidence of your skill without exposing private client data.",
                "content": (
                    "Make a small original example that resembles the work you want to do. Label "
                    "it as a sample, explain your role, and use fictional or permission-cleared data. "
                    "A few specific examples are more useful than a long list of unsupported claims."
                ),
                "exercise": "Create a sample project outline with a goal, deliverable and deadline.",
            },
            {
                "id": "freelance-avoid-scams",
                "title": "Client communication and scam checks",
                "minutes": 13,
                "objective": "Agree on scope, milestones and payment terms before starting.",
                "content": (
                    "Keep the scope and deadlines in writing. Verify the client and the platform. "
                    "Be cautious of requests to pay an upfront fee to unlock a job, forward money, "
                    "share passwords, or do substantial unpaid work as a condition for a promise "
                    "of future employment. Confirm payment arrangements independently."
                ),
                "exercise": "Write three questions you would ask before accepting a project.",
            },
        ),
    },
    {
        "id": "ai-productivity",
        "title": "AI Productivity with SAGE",
        "subtitle": "Give clearer instructions and verify the result.",
        "level": "Beginner",
        "estimated_minutes": 25,
        "lessons": (
            {
                "id": "ai-write-a-clear-request",
                "title": "Write a clear request",
                "minutes": 8,
                "objective": "Give an AI the goal, context, constraints and desired format.",
                "content": (
                    "State what you are trying to achieve, provide only the context needed, "
                    "mention limits such as length or deadline, and specify the output format. "
                    "For a large task, ask for a short plan before asking for the full result."
                ),
                "exercise": "Rewrite a vague request to include a goal, constraints and output format.",
            },
            {
                "id": "ai-verify-the-output",
                "title": "Verify AI-generated output",
                "minutes": 9,
                "objective": "Check important facts instead of treating a fluent answer as proof.",
                "content": (
                    "Review calculations, dates, citations, code changes and factual claims. "
                    "Ask for the assumptions when something is unclear, then independently verify "
                    "high-impact claims. Use a test or a small example to check whether a proposed "
                    "procedure works in your situation."
                ),
                "exercise": "Pick one claim in an AI response and decide how you would verify it.",
            },
            {
                "id": "ai-protect-private-data",
                "title": "Protect private information",
                "minutes": 8,
                "objective": "Avoid disclosing secrets that are not needed for a task.",
                "content": (
                    "Do not paste passwords, one-time codes, private keys, full bank credentials, "
                    "or another person's sensitive details into a prompt. Replace real names and "
                    "identifiers with fictional examples when possible, and confirm permissions "
                    "before asking a tool to send, publish, or change account data."
                ),
                "exercise": "Rewrite a sample prompt so it contains no unnecessary personal data.",
            },
        ),
    },
)


def _profile_id(claims: dict[str, Any]) -> str:
    profile = get_or_create_authenticated_profile(claims)
    profile_id = str(profile.get("id") or "").strip()
    if not profile_id:
        raise HTTPException(status_code=401, detail="Authenticated profile could not be loaded.")
    return profile_id


def _catalog_index() -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    return {
        lesson["id"]: (path, lesson)
        for path in _PATHS
        for lesson in path["lessons"]
    }


def _completed_ids(db: Session, profile_id: str) -> set[str]:
    rows = (
        db.query(LessonProgress.lesson_id)
        .filter(LessonProgress.profile_id == profile_id)
        .all()
    )
    return {row[0] for row in rows}


def _completed_at(db: Session, profile_id: str, lesson_id: str) -> datetime | None:
    row = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.profile_id == profile_id,
            LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    return row.completed_at if row else None


@router.get("/paths")
def list_learning_paths(
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id = _profile_id(claims)
    completed = _completed_ids(db, profile_id)
    paths: list[dict[str, Any]] = []
    for path in _PATHS:
        lessons: list[dict[str, Any]] = []
        for lesson in path["lessons"]:
            item = dict(lesson)
            item["is_completed"] = lesson["id"] in completed
            completed_at = _completed_at(db, profile_id, lesson["id"])
            item["completed_at"] = completed_at.isoformat() if completed_at else None
            lessons.append(item)
        completed_count = sum(1 for lesson in lessons if lesson["is_completed"])
        paths.append({
            "id": path["id"],
            "title": path["title"],
            "subtitle": path["subtitle"],
            "level": path["level"],
            "estimated_minutes": path["estimated_minutes"],
            "lessons": lessons,
            "completed_lessons": completed_count,
            "total_lessons": len(lessons),
            "progress_ratio": completed_count / len(lessons) if lessons else 0.0,
            "is_completed": bool(lessons) and completed_count == len(lessons),
        })
    return {"success": True, "paths": paths}


@router.post("/lessons/{lesson_id}/complete")
def complete_learning_lesson(
    lesson_id: str,
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id = _profile_id(claims)
    catalog = _catalog_index()
    entry = catalog.get(lesson_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Learning lesson not found.")
    _, lesson = entry
    existing = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.profile_id == profile_id,
            LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    if existing is None:
        progress = LessonProgress(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            lesson_id=lesson_id,
        )
        db.add(progress)
        try:
            db.commit()
        except IntegrityError:
            # A simultaneous completion request is still an idempotent success.
            db.rollback()
            existing = (
                db.query(LessonProgress)
                .filter(
                    LessonProgress.profile_id == profile_id,
                    LessonProgress.lesson_id == lesson_id,
                )
                .first()
            )
            if existing is None:
                raise
        else:
            db.refresh(progress)
            existing = progress
    return {
        "success": True,
        "lesson": {
            "id": lesson["id"],
            "title": lesson["title"],
            "is_completed": True,
            "completed_at": existing.completed_at.isoformat() if existing else None,
        },
        "message": "Lesson marked complete.",
    }
