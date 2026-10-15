"""Controlled execution gateway for SAGE ONE tools."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .models import ActionPlan, ActionRequest, ActionResult
from .verification import VerificationEngine


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "null":
        return value is None
    return True


def _validate_arguments(parameters: dict[str, Any], arguments: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not isinstance(arguments, dict):
        return ["Arguments must be an object."]

    required = parameters.get("required", [])
    if isinstance(required, list):
        for name in required:
            if name not in arguments:
                errors.append(f"Missing required argument: {name}")

    properties = parameters.get("properties", {})
    if not isinstance(properties, dict):
        return errors

    for name, value in arguments.items():
        spec = properties.get(name)
        if not isinstance(spec, dict):
            # Keep forward compatibility with schemas that permit extra fields.
            continue

        expected = spec.get("type")
        if isinstance(expected, str) and not _type_matches(value, expected):
            errors.append(
                f"Argument '{name}' must be of type {expected}."
            )
            continue

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            minimum = spec.get("minimum")
            maximum = spec.get("maximum")
            if minimum is not None and value < minimum:
                errors.append(
                    f"Argument '{name}' must be >= {minimum}."
                )
            if maximum is not None and value > maximum:
                errors.append(
                    f"Argument '{name}' must be <= {maximum}."
                )

        if isinstance(value, list):
            item_spec = spec.get("items")
            if isinstance(item_spec, dict) and isinstance(item_spec.get("type"), str):
                item_type = item_spec["type"]
                for index, item in enumerate(value):
                    if not _type_matches(item, item_type):
                        errors.append(
                            f"Argument '{name}[{index}]' must be of type {item_type}."
                        )

    return errors


class SQLAlchemyActionLogStore:
    """Durable ActionLog writer using the existing SAGE database model."""

    def __init__(self) -> None:
        from database.connection import SessionLocal
        from database.models import ActionLog, ActionEvidence

        self._session_factory = SessionLocal
        self._model = ActionLog
        self._evidence_model = ActionEvidence

    def start(
        self,
        *,
        action_id: str,
        request: ActionRequest,
        capability: str | None,
        permission: str,
        risk: str,
        permission_allowed: bool,
        permission_reason: str,
        started_at: datetime,
    ) -> str:
        db = self._session_factory()
        try:
            row = self._model(
                id=action_id,
                owner_key=request.owner_key,
                session_id=request.session_id,
                task_id=request.task_id,
                mission_id=request.mission_id,
                parent_action_id=request.parent_action_id,
                source=request.source,
                tool=request.tool_name,
                capability=capability or "unknown",
                permission=permission,
                risk=risk,
                arguments=_json_text(request.arguments),
                permission_allowed=int(permission_allowed),
                permission_reason=permission_reason,
                status="started",
                started_at=started_at,
            )
            db.add(row)
            db.commit()
            return action_id
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def record_evidence(
        self,
        *,
        action_id: str,
        mission_id: str | None,
        task_id: str | None,
        parent_action_id: str | None,
        evidence_type: str,
        content: Any,
        verified: bool,
    ) -> str:
        db = self._session_factory()
        evidence_id = str(uuid4())
        try:
            row = self._evidence_model(
                id=evidence_id,
                action_id=action_id,
                mission_id=mission_id,
                task_id=task_id,
                parent_action_id=parent_action_id,
                evidence_type=evidence_type,
                content=_json_text(content),
                verified=int(verified),
                created_at=datetime.now(timezone.utc),
            )
            db.add(row)
            db.commit()
            return evidence_id
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def finish(
        self,
        *,
        action_id: str,
        status: str,
        result: Any = None,
        error: str | None = None,
        completed_at: datetime,
        duration_ms: int,
    ) -> None:
        db = self._session_factory()
        try:
            row = db.query(self._model).filter(self._model.id == action_id).first()
            if row is None:
                raise RuntimeError(f"ActionLog not found: {action_id}")
            row.status = status
            row.result = _json_text(result) if result is not None else None
            row.error = error
            row.completed_at = completed_at
            row.duration_ms = duration_ms
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


class AgenticActionEngine:
    """The only controlled gateway an agent should use to execute tools."""

    def __init__(
        self,
        *,
        registry: Any | None = None,
        permission_engine: Any | None = None,
        log_store: Any | None = None,
        verification_engine: VerificationEngine | None = None,
        event_store: Any | None = None,
    ) -> None:
        if registry is None:
            from tools.registry import registry as default_registry
            registry = default_registry

        if permission_engine is None:
            from permissions.engine import permissions as default_permissions
            permission_engine = default_permissions

        self.registry = registry
        self.permission_engine = permission_engine
        self.log_store = log_store or SQLAlchemyActionLogStore()
        self.verification_engine = verification_engine or VerificationEngine()
        self.event_store = event_store

    def _emit_event(
        self,
        *,
        event_type: str,
        request: ActionRequest,
        action_id: str | None,
        status: str | None = None,
        payload: Any = None,
    ) -> str | None:
        if self.event_store is None:
            return None
        try:
            return self.event_store.emit(
                event_type=event_type,
                action_id=action_id,
                session_id=request.session_id,
                mission_id=request.mission_id,
                task_id=request.task_id,
                parent_action_id=request.parent_action_id,
                status=status,
                source=request.source,
                payload=payload,
            )
        except Exception:
            return None

    def plan(self, request: ActionRequest) -> ActionPlan:
        tool = self.registry.get(request.tool_name)
        if tool is None:
            return ActionPlan(
                tool_name=request.tool_name,
                capability=None,
                permission="unknown",
                risk="unknown",
                handler=None,
                arguments=dict(request.arguments),
                validation_errors=("Unknown tool.",),
            )

        errors = tuple(
            _validate_arguments(tool.parameters or {}, request.arguments)
        )
        return ActionPlan(
            tool_name=tool.name,
            capability=tool.capability,
            permission=tool.permission,
            risk=tool.risk,
            handler=tool.handler,
            arguments=dict(request.arguments),
            validation_errors=errors,
            output_schema=tool.output_schema,
            cost_policy=tool.cost_policy,
            timeout_seconds=tool.timeout_seconds,
            retry_policy=tool.retry_policy,
            verification_policy=tool.verification_policy,
            audit_policy=tool.audit_policy,
            side_effect_class=tool.side_effect_class,
        )

    def _terminal_log(
        self,
        *,
        request: ActionRequest,
        plan: ActionPlan,
        permission_allowed: bool,
        permission_reason: str,
        status: str,
        error: str,
    ) -> str | None:
        action_id = str(uuid4())
        started_at = datetime.now(timezone.utc)
        try:
            self.log_store.start(
                action_id=action_id,
                request=request,
                capability=plan.capability,
                permission=plan.permission,
                risk=plan.risk,
                permission_allowed=permission_allowed,
                permission_reason=permission_reason,
                started_at=started_at,
            )
            self.log_store.finish(
                action_id=action_id,
                status=status,
                error=error,
                completed_at=datetime.now(timezone.utc),
                duration_ms=max(
                    0,
                    int((time.monotonic() - time.monotonic()) * 1000),
                ),
            )
            event_type = "ActionPermissionDenied" if status == "denied" else "ActionRejected"
            self._emit_event(
                event_type=event_type,
                request=request,
                action_id=action_id,
                status=status,
                payload={"tool": plan.tool_name, "error": error},
            )
            return action_id
        except Exception:
            return None

    def execute(self, request: ActionRequest) -> ActionResult:
        plan = self.plan(request)

        if plan.handler is None:
            reason = "Unknown tool."
            action_id = self._terminal_log(
                request=request,
                plan=plan,
                permission_allowed=False,
                permission_reason=reason,
                status="denied",
                error=reason,
            )
            return ActionResult(
                success=False,
                action_id=action_id,
                tool_name=request.tool_name,
                status="denied",
                permission_allowed=False,
                permission_reason=reason,
                permission=plan.permission,
                risk=plan.risk,
                capability=plan.capability,
                error=reason,
                verification_status="not_requested",
            )

        decision = self.permission_engine.check(
            plan.permission,
            plan.risk,
            tool_name=plan.tool_name,
            owner_authorized=request.owner_authorized,
        )

        if not decision.allowed:
            action_id = self._terminal_log(
                request=request,
                plan=plan,
                permission_allowed=False,
                permission_reason=decision.reason,
                status="denied",
                error=decision.reason,
            )
            return ActionResult(
                success=False,
                action_id=action_id,
                tool_name=plan.tool_name,
                status="denied",
                permission_allowed=False,
                permission_reason=decision.reason,
                permission=plan.permission,
                risk=plan.risk,
                capability=plan.capability,
                error=decision.reason,
                verification_status="not_requested",
            )

        if plan.validation_errors:
            error = "; ".join(plan.validation_errors)
            action_id = self._terminal_log(
                request=request,
                plan=plan,
                permission_allowed=True,
                permission_reason=decision.reason,
                status="invalid_arguments",
                error=error,
            )
            return ActionResult(
                success=False,
                action_id=action_id,
                tool_name=plan.tool_name,
                status="invalid_arguments",
                permission_allowed=True,
                permission_reason=decision.reason,
                permission=plan.permission,
                risk=plan.risk,
                capability=plan.capability,
                error=error,
                verification_status="not_requested",
            )

        action_id = str(uuid4())
        started_at = datetime.now(timezone.utc)

        # Fail closed if durable audit creation fails: do not execute an action
        # that cannot be recorded.
        try:
            self.log_store.start(
                action_id=action_id,
                request=request,
                capability=plan.capability,
                permission=plan.permission,
                risk=plan.risk,
                permission_allowed=True,
                permission_reason=decision.reason,
                started_at=started_at,
            )

            event_ids = []
            event_id = self._emit_event(
                event_type="ActionStarted",
                request=request,
                action_id=action_id,
                status="started",
                payload={"tool": plan.tool_name, "capability": plan.capability},
            )
            if event_id:
                event_ids.append(event_id)
        except Exception as exc:
            return ActionResult(
                success=False,
                action_id=None,
                tool_name=plan.tool_name,
                status="audit_failed",
                permission_allowed=True,
                permission_reason=decision.reason,
                permission=plan.permission,
                risk=plan.risk,
                capability=plan.capability,
                error=f"ActionLog start failed; execution blocked: {exc}",
                verification_status="not_requested",
            )

        output: Any = None
        error: str | None = None
        execution_success = False
        event_ids = locals().get("event_ids", [])


        try:
            output = plan.handler(**plan.arguments)
            execution_success = not (
                isinstance(output, dict) and output.get("success") is False
            )
            if not execution_success:
                error = str(output.get("error") or "Tool reported success=false.")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        verification = (
            self.verification_engine.verify_execution(
                success=execution_success,
                result=output,
                error=error,
            )
            if request.verify
            else None
        )

        evidence: list[dict[str, Any]] = []
        if verification is not None:
            evidence_item = {
                "type": "execution_verification",
                "status": verification.status,
                "reason": verification.reason,
                "evidence": verification.evidence,
            }
            try:
                record_evidence = getattr(self.log_store, "record_evidence", None)
                if record_evidence is None:
                    evidence_item["persisted"] = False
                else:
                    evidence_id = record_evidence(
                        action_id=action_id,
                        mission_id=request.mission_id,
                        task_id=request.task_id,
                        parent_action_id=request.parent_action_id,
                        evidence_type="execution_verification",
                        content=evidence_item,
                        verified=verification.status == "passed",
                    )
                    evidence_item["evidence_id"] = evidence_id
                    evidence_item["persisted"] = True
            except Exception as exc:
                evidence_item["persist_error"] = str(exc)
                execution_success = False
                error = f"{error + '; ' if error else ''}Evidence persistence failed: {exc}"
            evidence.append(evidence_item)

        status = "completed" if execution_success else "failed"
        completed_at = datetime.now(timezone.utc)
        duration_ms = max(
            0,
            int((completed_at - started_at).total_seconds() * 1000),
        )

        try:
            self.log_store.finish(
                action_id=action_id,
                status=status,
                result=output,
                error=error,
                completed_at=completed_at,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            # The tool already ran, so report the audit failure explicitly.
            status = "audit_failed"
            error = (
                f"{error + '; ' if error else ''}"
                f"ActionLog completion failed: {exc}"
            )
            execution_success = False

        lifecycle_event = self._emit_event(
            event_type="ActionCompleted" if execution_success else "ActionFailed",
            request=request,
            action_id=action_id,
            status=status,
            payload={"tool": plan.tool_name, "error": error},
        )
        if lifecycle_event:
            event_ids.append(lifecycle_event)

        if verification is not None:
            verification_event = self._emit_event(
                event_type="VerificationCompleted",
                request=request,
                action_id=action_id,
                status=verification.status,
                payload={"reason": verification.reason, "evidence": verification.evidence},
            )
            if verification_event:
                event_ids.append(verification_event)

        return ActionResult(
            success=execution_success,
            action_id=action_id,
            tool_name=plan.tool_name,
            status=status,
            permission_allowed=True,
            permission_reason=decision.reason,
            permission=plan.permission,
            risk=plan.risk,
            capability=plan.capability,
            result=output,
            error=error,
            verification_status=(
                verification.status if verification else "not_requested"
            ),
            verification_reason=(
                verification.reason if verification else None
            ),
            duration_ms=duration_ms,
            mission_id=request.mission_id,
            parent_action_id=request.parent_action_id,
            evidence=evidence,
            event_ids=event_ids,
        )


from events.service import event_store as default_event_store

action_engine = AgenticActionEngine(event_store=default_event_store)
