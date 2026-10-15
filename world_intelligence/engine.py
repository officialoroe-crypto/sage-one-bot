from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from permissions.engine import permissions
from database.connection import SessionLocal
from world_intelligence.models import UpgradeProposal, WorldKnowledge, WorldSignal
from world_intelligence.source_policy import world_source_policy


DEFAULT_TOPICS = (
    "important world events and current affairs",
    "technology and artificial intelligence developments",
    "business and industry trends",
    "content creation and social media trends",
    "new software tools and useful APIs",
    "education and learning resources",
)


class WorldIntelligenceEngine:
    """Controlled public-world learning for SAGE ONE.

    This subsystem learns from public information only. Learning is source
    traceable, bounded, and permission checked. It may propose SAGE upgrades,
    but it never modifies code, permissions, accounts, or security policy.
    """

    VERSION = "1.0"
    REFRESH_INTERVAL_HOURS = 12
    MAX_TOPICS_PER_REFRESH = 6

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    @staticmethod
    def _permission(name: str) -> None:
        decision = permissions.check(name, risk="low", owner_authorized=True)
        if not decision.allowed:
            raise PermissionError(decision.reason)

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex}"

    def observe(self, topic: str, *, max_queries: int = 3, max_results_per_query: int = 4) -> dict:
        """Observe current public information without inventing knowledge."""
        self._permission("world.observe")

        topic = str(topic).strip()
        if not topic:
            raise ValueError("World intelligence topic cannot be empty.")

        from research.engine import research_engine

        result = research_engine.research(
            question=topic,
            max_queries=max(1, min(int(max_queries), 5)),
            max_results_per_query=max(1, min(int(max_results_per_query), 5)),
        )

        sources = result.get("sources", []) if isinstance(result, dict) else []
        sources, rejected_sources = world_source_policy.select(
            [source for source in sources if isinstance(source, dict)],
            limit=20,
        )
        readable = [
            source for source in sources
            if isinstance(source, dict) and source.get("read_success")
        ]

        now = self._now()
        signal_ids: list[str] = []

        with SessionLocal() as db:
            for source in sources[:20]:
                if not isinstance(source, dict):
                    continue
                title = str(source.get("title") or topic).strip()
                description = str(source.get("snippet") or "").strip()
                url = str(source.get("final_url") or source.get("url") or "").strip()
                if not url:
                    continue
                signal = WorldSignal(
                    id=self._id("ws"),
                    category="observation",
                    title=title[:500],
                    description=description[:5000],
                    source_urls=json.dumps([url], ensure_ascii=False),
                    confidence="source_observed",
                    observed_at=now,
                )
                db.add(signal)
                signal_ids.append(signal.id)
            db.commit()

        return {
            "success": bool(result.get("success")) if isinstance(result, dict) else False,
            "topic": topic,
            "source_count": len(sources),
            "readable_count": len(readable),
            "signal_count": len(signal_ids),
            "signal_ids": signal_ids,
            "accepted_source_count": len(sources),
            "rejected_sources": rejected_sources,
            "observed_at": now.isoformat(),
            "errors": result.get("errors", []) if isinstance(result, dict) else ["Invalid research result."],
        }

    def learn(self, topic: str, *, max_queries: int = 3, max_results_per_query: int = 4) -> dict:
        """Turn verified public research into durable world knowledge."""
        self._permission("world.learn")

        topic = str(topic).strip()
        if not topic:
            raise ValueError("World intelligence topic cannot be empty.")

        from research.synthesis import research_synthesis_engine

        report = research_synthesis_engine.synthesize(
            question=topic,
            max_queries=max(1, min(int(max_queries), 5)),
            max_results_per_query=max(1, min(int(max_results_per_query), 5)),
        )

        if not isinstance(report, dict) or not report.get("success"):
            return {
                "success": False,
                "topic": topic,
                "error": report.get("error", "World knowledge synthesis failed.") if isinstance(report, dict) else "Invalid synthesis result.",
            }

        sources = report.get("sources") or []
        allowed_sources, rejected_sources = world_source_policy.select(
            [source for source in sources if isinstance(source, dict)],
            limit=20,
        )
        if not allowed_sources:
            return {
                "success": False,
                "topic": topic,
                "error": "World source policy rejected all candidate sources.",
                "rejected_sources": rejected_sources,
            }

        report = {
            **report,
            "sources": allowed_sources,
            "source_policy_rejections": rejected_sources,
        }
        report_json = json.dumps(report, ensure_ascii=False, default=str)
        summary = str(report.get("summary") or "").strip()
        claims = report.get("claims") or []
        confidence = "verified" if claims and not rejected_sources else "source_backed"
        now = self._now()

        with SessionLocal() as db:
            row = WorldKnowledge(
                id=self._id("wk"),
                topic=topic[:1000],
                title=topic[:500],
                summary=summary[:20000],
                knowledge_json=report_json,
                source_count=len(sources) if isinstance(sources, list) else 0,
                confidence=confidence,
                learned_at=now,
                refreshed_at=now,
            )
            db.add(row)
            db.commit()
            knowledge_id = row.id

        return {
            "success": True,
            "knowledge_id": knowledge_id,
            "topic": topic,
            "summary": summary,
            "source_count": len(sources) if isinstance(sources, list) else 0,
            "claim_count": len(claims) if isinstance(claims, list) else 0,
            "confidence": confidence,
            "learned_at": now.isoformat(),
        }

    def refresh(self, topics: list[str] | None = None) -> dict:
        """Refresh a bounded set of world topics.

        This method is scheduler-ready: a future background scheduler can call
        it periodically. It does not start an unbounded background loop inside
        the API process.
        """
        selected = list(topics or DEFAULT_TOPICS)[: self.MAX_TOPICS_PER_REFRESH]
        results = []
        for topic in selected:
            try:
                results.append(self.learn(topic))
            except Exception as exc:
                results.append({"success": False, "topic": topic, "error": str(exc)})

        return {
            "success": all(item.get("success") for item in results) if results else False,
            "topics": selected,
            "results": results,
            "refreshed_at": self._now().isoformat(),
        }

    def due(self, *, hours: int | None = None) -> list[str]:
        """Return default topics whose stored knowledge is stale or absent."""
        self._permission("world.read")
        cutoff = self._now() - timedelta(hours=hours or self.REFRESH_INTERVAL_HOURS)
        due_topics: list[str] = []

        with SessionLocal() as db:
            for topic in DEFAULT_TOPICS:
                row = (
                    db.query(WorldKnowledge)
                    .filter(WorldKnowledge.topic == topic)
                    .order_by(WorldKnowledge.refreshed_at.desc())
                    .first()
                )
                if row is None or row.refreshed_at < cutoff:
                    due_topics.append(topic)

        return due_topics

    def list_knowledge(self, limit: int = 20) -> list[dict]:
        self._permission("world.read")
        with SessionLocal() as db:
            rows = (
                db.query(WorldKnowledge)
                .order_by(WorldKnowledge.refreshed_at.desc())
                .limit(max(1, min(int(limit), 100)))
                .all()
            )
            return [
                {
                    "id": row.id,
                    "topic": row.topic,
                    "title": row.title,
                    "summary": row.summary,
                    "source_count": row.source_count,
                    "confidence": row.confidence,
                    "learned_at": self._iso(row.learned_at),
                    "refreshed_at": self._iso(row.refreshed_at),
                }
                for row in rows
            ]

    def propose_upgrade(self, title: str, reason: str, benefit: str, evidence: list[str] | None = None) -> dict:
        """Create a human-reviewable SAGE improvement proposal."""
        self._permission("world.propose_upgrade")

        title = str(title).strip()
        reason = str(reason).strip()
        benefit = str(benefit).strip()
        if not title or not reason or not benefit:
            raise ValueError("Upgrade proposal requires title, reason, and benefit.")

        with SessionLocal() as db:
            row = UpgradeProposal(
                id=self._id("upg"),
                title=title[:500],
                reason=reason[:10000],
                benefit=benefit[:10000],
                evidence_json=json.dumps(list(evidence or [])[:50], ensure_ascii=False),
                status="proposed",
                created_at=self._now(),
            )
            db.add(row)
            db.commit()
            return {
                "success": True,
                "proposal": {
                    "id": row.id,
                    "title": row.title,
                    "reason": row.reason,
                    "benefit": row.benefit,
                    "evidence": list(evidence or [])[:50],
                    "status": row.status,
                    "created_at": self._iso(row.created_at),
                },
            }

    def list_upgrade_proposals(self, limit: int = 20) -> list[dict]:
        self._permission("world.read")
        with SessionLocal() as db:
            rows = (
                db.query(UpgradeProposal)
                .order_by(UpgradeProposal.created_at.desc())
                .limit(max(1, min(int(limit), 100)))
                .all()
            )
            return [
                {
                    "id": row.id,
                    "title": row.title,
                    "reason": row.reason,
                    "benefit": row.benefit,
                    "evidence": json.loads(row.evidence_json or "[]"),
                    "status": row.status,
                    "created_at": self._iso(row.created_at),
                }
                for row in rows
            ]

    def status(self) -> dict:
        self._permission("world.read")
        return {
            "success": True,
            "system": "SAGE WORLD INTELLIGENCE",
            "version": self.VERSION,
            "world_learning_enabled": True,
            "public_sources_only": True,
            "self_modification": False,
            "upgrade_proposals_require_human_review": True,
            "refresh_interval_hours": self.REFRESH_INTERVAL_HOURS,
            "default_topics": list(DEFAULT_TOPICS),
            "due_topics": self.due(),
        }


world_intelligence = WorldIntelligenceEngine()
