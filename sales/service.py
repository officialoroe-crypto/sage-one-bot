from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session as DBSession

from sales.models import SalesActivity, SalesLead
from web.reader import WebReader


class SalesEngine:
    """Bounded sales intelligence pipeline.

    Discovery is represented by the supplied business. Audit is read-only.
    Scoring and outreach preparation are deterministic and transparent.
    Outreach is always approval-gated and never sent by this engine.
    """

    def __init__(self, reader: WebReader | None = None):
        self.reader = reader or WebReader(timeout=12, max_chars=30000)

    @staticmethod
    def _score_page(content: str, title: str | None) -> dict[str, Any]:
        text = f"{title or ''} {content}".lower()
        checks = {
            "website_presence": 15,
            "clear_cta": 15 if any(x in text for x in ("contact", "call us", "whatsapp", "quote", "get started")) else 0,
            "branding": 15 if any(x in text for x in ("about", "our story", "brand", "quality")) else 0,
            "content": 15 if any(x in text for x in ("blog", "news", "gallery", "video", "project", "portfolio")) else 0,
            "trust": 15 if any(x in text for x in ("review", "testimonial", "trusted", "years", "experience")) else 0,
        }
        if content:
            checks["website_presence"] = 15
        return checks

    def audit_business(self, business_name: str, website: str | None, instagram: str | None, notes: str | None) -> dict[str, Any]:
        page = None
        website_valid = bool(website and urlparse(website).scheme in {"http", "https"} and urlparse(website).netloc)
        if website_valid:
            page = self.reader.read(website)

        content = (page or {}).get("content", "") if page else ""
        title = (page or {}).get("title") if page else None
        checks = self._score_page(content, title)
        if not website_valid:
            checks["website_presence"] = 0

        if instagram:
            checks["social_presence"] = 10
        else:
            checks["social_presence"] = 0

        score = max(0, min(100, sum(checks.values())))
        tier = "hot" if score < 45 else "warm" if score < 70 else "nurture"
        gaps = [key for key, value in checks.items() if value == 0]

        draft = (
            f"Hi {business_name}, I checked your online presence and found a few quick opportunities "
            f"to improve visibility and customer conversion. The biggest gaps I found are: "
            f"{', '.join(gaps[:4]) or 'no major gaps detected'}. "
            "I can show you a short improvement plan if you're interested."
        )
        return {
            "success": True,
            "workflow": ["discovery", "audit", "score", "lead", "intelligence", "outreach_draft", "approval", "history", "customer"],
            "lead": {
                "business_name": business_name.strip(),
                "website": website,
                "instagram": instagram,
                "score": score,
                "tier": tier,
                "gaps": gaps,
                "audit": checks,
                "source": page.get("final_url") if page else website,
                "notes": notes,
            },
            "intelligence": {
                "opportunity": "Improve digital presence and conversion where gaps were detected.",
                "priority": "high" if score < 45 else "medium",
            },
            "outreach": {
                "channel": "whatsapp_draft",
                "requires_approval": True,
                "sent": False,
                "draft": draft,
            },
        }

    def run_from_task(self, description: str, task_id: str, owner_key: str | None, project_id: str | None, profile_id: str | None) -> dict[str, Any]:
        try:
            payload = json.loads(description)
        except json.JSONDecodeError as exc:
            raise ValueError("Sales task payload is invalid JSON.") from exc
        business_name = str(payload.get("business_name") or "").strip()
        if not business_name:
            raise ValueError("Sales task requires business_name.")
        result = self.audit_business(
            business_name=business_name,
            website=payload.get("website"),
            instagram=payload.get("instagram"),
            notes=payload.get("notes"),
        )
        if owner_key:
            result["lead_id"] = self.persist_lead(owner_key, profile_id, project_id, task_id, result)
        return result

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _load(value: str | None, fallback: Any) -> Any:
        if not value:
            return fallback
        try:
            return json.loads(value)
        except Exception:
            return fallback

    def persist_lead(self, owner_key: str, profile_id: str | None, project_id: str | None, task_id: str, result: dict[str, Any], db: DBSession | None = None) -> str:
        from database.connection import SessionLocal
        own_session = db is None
        session = db or SessionLocal()
        try:
            data = result["lead"]
            lead = SalesLead(
                id=str(uuid.uuid4()), owner_key=owner_key, profile_id=profile_id,
                project_id=project_id, task_id=task_id,
                business_name=data["business_name"], website=data.get("website"),
                instagram=data.get("instagram"), score=int(data["score"]),
                tier=data["tier"], status="outreach_pending",
                audit_json=json.dumps(data, ensure_ascii=False),
                intelligence_json=json.dumps(result["intelligence"], ensure_ascii=False),
                outreach_json=json.dumps(result["outreach"], ensure_ascii=False),
                created_at=self._now(), updated_at=self._now(),
            )
            session.add(lead)
            session.add(SalesActivity(
                id=str(uuid.uuid4()), lead_id=lead.id, owner_key=owner_key,
                event_type="discovered_audited_scored", status="completed",
                payload_json=json.dumps({"score": lead.score, "tier": lead.tier, "task_id": task_id}),
                created_at=self._now(),
            ))
            session.commit()
            return lead.id
        finally:
            if own_session:
                session.close()

    def approve_outreach(self, db: DBSession, lead: SalesLead, owner_key: str) -> SalesLead:
        if lead.owner_key != owner_key:
            raise ValueError("Sales lead is not owned by the authenticated owner.")
        if lead.status in {"outreach_approved", "customer"}:
            return lead
        outreach = self._load(lead.outreach_json, {})
        if not outreach.get("draft"):
            raise ValueError("No outreach draft is available for approval.")
        outreach["approved"] = True
        outreach["requires_approval"] = False
        lead.outreach_json = json.dumps(outreach, ensure_ascii=False)
        lead.status = "outreach_approved"
        lead.updated_at = self._now()
        db.add(SalesActivity(
            id=str(uuid.uuid4()), lead_id=lead.id, owner_key=owner_key,
            event_type="outreach_approved", status="approved",
            payload_json=json.dumps({"channel": outreach.get("channel"), "sent": False}),
            created_at=self._now(),
        ))
        db.commit()
        db.refresh(lead)
        return lead

    def convert_customer(self, db: DBSession, lead: SalesLead, owner_key: str) -> SalesLead:
        if lead.owner_key != owner_key:
            raise ValueError("Sales lead is not owned by the authenticated owner.")
        if lead.status == "customer":
            return lead
        if lead.status != "outreach_approved":
            raise ValueError("Approve the outreach draft before converting this lead to a customer.")
        lead.status = "customer"
        lead.updated_at = self._now()
        db.add(SalesActivity(
            id=str(uuid.uuid4()), lead_id=lead.id, owner_key=owner_key,
            event_type="customer_converted", status="completed",
            payload_json=json.dumps({"business_name": lead.business_name}),
            created_at=self._now(),
        ))
        db.commit()
        db.refresh(lead)
        return lead



sales_engine = SalesEngine()
