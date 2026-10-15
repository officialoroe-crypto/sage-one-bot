from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any


# ============================================================
# PERMISSION DECISION
# ============================================================

@dataclass
class PermissionDecision:
    allowed: bool
    reason: str
    permission: str
    risk: str
    emergency_stop: bool = False
    owner_authorized: bool = False


# ============================================================
# OWNER CONTROL PLANE
# ============================================================

class PermissionEngine:
    """
    Central authority layer for SAGE ONE.

    Core rule:

        CAPABILITY != PERMISSION

    A tool can exist without being authorized to execute.

    The owner remains the final authority.

    Emergency stop has priority over normal permissions.
    """

    RISK_LEVELS = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    def __init__(self):
        self._lock = RLock()

        # ----------------------------------------------------
        # SYSTEM STATE
        # ----------------------------------------------------

        self.emergency_stop = False
        self.system_locked = False

        # Maximum risk Sage may autonomously execute.
        #
        # This is intentionally conservative.
        self.max_autonomous_risk = "medium"

        # ----------------------------------------------------
        # OWNER PERMISSIONS
        # ----------------------------------------------------

        self.permissions: dict[str, bool] = {

            # Core system
            "system.read": True,
            "system.status": True,

            # Memory
            "memory.read": True,
            "memory.write": True,

            # Tasks / missions
            "task.read": True,
            "task.write": True,

            "mission.read": True,
            "mission.create": True,
            "mission.execute": True,
            "mission.verify": True,

            # Research
            "research.read": True,
            "research.execute": True,

            # Tools
            "tool.discover": True,
            "tool.execute": True,

            # Files
            "file.read": False,
            "file.write": False,
            "file.delete": False,

            # Network / web
            "web.read": False,
            "web.write": False,

            # Computer
            "computer.read": False,
            "computer.control": False,

            # Phone
            "phone.read": False,
            "phone.control": False,

            # Communications
            "email.read": False,
            "email.send": False,

            "message.read": False,
            "message.send": False,

            # Calendar
            "calendar.read": False,
            "calendar.write": False,

            # External accounts
            "external.account.read": False,
            "external.account.write": False,

            # Financial authority
            "financial.read": False,
            "financial.prepare": True,
            "financial.execute": False,

            # Spending
            "spending.prepare": True,
            "spending.execute": False,

            # Automation
            "automation.read": True,
            "automation.create": True,
            "automation.execute": True,

            # Agents
            "agent.read": True,
            "agent.create": True,
            "agent.execute": True,

            # Security administration
            "security.read": True,
            "security.modify": False,

            # Control plane
            "control.read": True,
            "control.modify": True,
            "control.emergency_stop": True,
            "control.emergency_resume": True,
        }

        # ----------------------------------------------------
        # RISK OVERRIDES
        # ----------------------------------------------------

        self.permission_risk: dict[str, str] = {
            "system.read": "low",
            "system.status": "low",

            "memory.read": "low",
            "memory.write": "medium",

            "task.read": "low",
            "task.write": "medium",

            "mission.read": "low",
            "mission.create": "medium",
            "mission.execute": "medium",
            "mission.verify": "medium",

            "research.read": "low",
            "research.execute": "medium",

            "tool.discover": "low",
            "tool.execute": "medium",

            "file.read": "medium",
            "file.write": "high",
            "file.delete": "critical",

            "web.read": "medium",
            "web.write": "high",

            "computer.read": "medium",
            "computer.control": "high",

            "phone.read": "medium",
            "phone.control": "high",

            "email.read": "medium",
            "email.send": "high",

            "message.read": "medium",
            "message.send": "high",

            "calendar.read": "low",
            "calendar.write": "medium",

            "external.account.read": "high",
            "external.account.write": "critical",

            "financial.read": "high",
            "financial.prepare": "medium",
            "financial.execute": "critical",

            "spending.prepare": "medium",
            "spending.execute": "critical",

            "automation.read": "low",
            "automation.create": "medium",
            "automation.execute": "high",

            "agent.read": "low",
            "agent.create": "medium",
            "agent.execute": "high",

            "security.read": "low",
            "security.modify": "critical",

            "control.read": "low",
            "control.modify": "critical",
            "control.emergency_stop": "critical",
            "control.emergency_resume": "critical",
        }

        # ----------------------------------------------------
        # AUDIT
        # ----------------------------------------------------

        self.audit_log: list[dict[str, Any]] = []

        # ----------------------------------------------------
        # OWNER IDENTITY
        # ----------------------------------------------------

        self.owner_identity = {
            "role": "owner",
            "authority": "final",
            "initialized": True,
        }

    # ========================================================
    # INTERNAL HELPERS
    # ========================================================

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _risk_value(self, risk: str) -> int:
        return self.RISK_LEVELS.get(
            str(risk).lower(),
            self.RISK_LEVELS["critical"],
        )

    def _max_risk_value(self) -> int:
        return self._risk_value(
            self.max_autonomous_risk
        )

    def _record(
        self,
        *,
        tool_name: str | None,
        permission: str,
        risk: str,
        allowed: bool,
        reason: str,
        source: str = "permission_engine",
    ):
        with self._lock:
            self.audit_log.append(
                {
                    "timestamp": self._now(),
                    "tool": tool_name,
                    "permission": permission,
                    "risk": risk,
                    "allowed": allowed,
                    "reason": reason,
                    "source": source,
                    "emergency_stop": self.emergency_stop,
                    "system_locked": self.system_locked,
                }
            )

    # ========================================================
    # PERMISSION CHECK
    # ========================================================

    def check(
        self,
        permission: str,
        risk: str = "low",
        *,
        tool_name: str | None = None,
        owner_authorized: bool = True,
    ) -> PermissionDecision:

        risk = str(risk or "low").lower()

        # ----------------------------------------------------
        # EMERGENCY STOP HAS HIGHEST PRIORITY
        # ----------------------------------------------------

        if self.emergency_stop:

            allowed_during_stop = {
                "system.read",
                "system.status",
                "control.read",
                "control.emergency_resume",
            }

            if permission not in allowed_during_stop:
                reason = (
                    "Denied: SAGE ONE emergency stop is active."
                )

                self._record(
                    tool_name=tool_name,
                    permission=permission,
                    risk=risk,
                    allowed=False,
                    reason=reason,
                )

                return PermissionDecision(
                    allowed=False,
                    reason=reason,
                    permission=permission,
                    risk=risk,
                    emergency_stop=True,
                    owner_authorized=owner_authorized,
                )

        # ----------------------------------------------------
        # SYSTEM LOCK
        # ----------------------------------------------------

        if self.system_locked:

            allowed_while_locked = {
                "system.read",
                "system.status",
                "control.read",
                "control.emergency_resume",
            }

            if permission not in allowed_while_locked:
                reason = (
                    "Denied: SAGE ONE system lock is active."
                )

                self._record(
                    tool_name=tool_name,
                    permission=permission,
                    risk=risk,
                    allowed=False,
                    reason=reason,
                )

                return PermissionDecision(
                    allowed=False,
                    reason=reason,
                    permission=permission,
                    risk=risk,
                    emergency_stop=self.emergency_stop,
                    owner_authorized=owner_authorized,
                )

        # ----------------------------------------------------
        # OWNER AUTHORITY
        # ----------------------------------------------------

        if not owner_authorized:
            reason = (
                "Denied: owner authorization is required."
            )

            self._record(
                tool_name=tool_name,
                permission=permission,
                risk=risk,
                allowed=False,
                reason=reason,
            )

            return PermissionDecision(
                allowed=False,
                reason=reason,
                permission=permission,
                risk=risk,
                emergency_stop=self.emergency_stop,
                owner_authorized=False,
            )

        # ----------------------------------------------------
        # UNKNOWN PERMISSION
        # ----------------------------------------------------

        if permission not in self.permissions:

            reason = (
                f"Denied: unknown permission '{permission}'."
            )

            self._record(
                tool_name=tool_name,
                permission=permission,
                risk=risk,
                allowed=False,
                reason=reason,
            )

            return PermissionDecision(
                allowed=False,
                reason=reason,
                permission=permission,
                risk=risk,
                emergency_stop=self.emergency_stop,
                owner_authorized=owner_authorized,
            )

        # ----------------------------------------------------
        # EXPLICIT PERMISSION
        # ----------------------------------------------------

        if not self.permissions[permission]:

            reason = (
                f"Denied: permission '{permission}' "
                f"is not granted."
            )

            self._record(
                tool_name=tool_name,
                permission=permission,
                risk=risk,
                allowed=False,
                reason=reason,
            )

            return PermissionDecision(
                allowed=False,
                reason=reason,
                permission=permission,
                risk=risk,
                emergency_stop=self.emergency_stop,
                owner_authorized=owner_authorized,
            )

        # ----------------------------------------------------
        # AUTONOMOUS RISK LIMIT
        # ----------------------------------------------------

        risk_value = self._risk_value(risk)

        if risk_value > self._max_risk_value():

            reason = (
                f"Denied: risk '{risk}' exceeds "
                f"autonomous risk limit "
                f"'{self.max_autonomous_risk}'."
            )

            self._record(
                tool_name=tool_name,
                permission=permission,
                risk=risk,
                allowed=False,
                reason=reason,
            )

            return PermissionDecision(
                allowed=False,
                reason=reason,
                permission=permission,
                risk=risk,
                emergency_stop=self.emergency_stop,
                owner_authorized=owner_authorized,
            )

        # ----------------------------------------------------
        # ALLOWED
        # ----------------------------------------------------

        reason = "Permission granted."

        self._record(
            tool_name=tool_name,
            permission=permission,
            risk=risk,
            allowed=True,
            reason=reason,
        )

        return PermissionDecision(
            allowed=True,
            reason=reason,
            permission=permission,
            risk=risk,
            emergency_stop=self.emergency_stop,
            owner_authorized=owner_authorized,
        )

    # ========================================================
    # PERMISSION MANAGEMENT
    # ========================================================

    def set_permission(
        self,
        permission: str,
        allowed: bool,
    ):
        with self._lock:

            if permission == "control.emergency_stop":
                if allowed:
                    self.emergency_stop = True
                else:
                    self.emergency_stop = False

            self.permissions[permission] = bool(allowed)

            self._record(
                tool_name=None,
                permission=permission,
                risk=self.permission_risk.get(
                    permission,
                    "medium",
                ),
                allowed=True,
                reason=(
                    f"Permission '{permission}' "
                    f"set to {bool(allowed)}."
                ),
                source="owner_control",
            )

    # Compatibility alias for future code.
    def set(self, permission: str, allowed: bool):
        self.set_permission(permission, allowed)

    def get_permissions(self):
        with self._lock:
            return dict(self.permissions)

    # Compatibility alias.
    def get_all(self):
        return self.get_permissions()

    # ========================================================
    # RISK MANAGEMENT
    # ========================================================

    def set_max_autonomous_risk(self, risk: str):
        risk = str(risk).lower()

        if risk not in self.RISK_LEVELS:
            raise ValueError(
                f"Invalid risk level: {risk}"
            )

        with self._lock:
            self.max_autonomous_risk = risk

            self._record(
                tool_name=None,
                permission="control.modify",
                risk="critical",
                allowed=True,
                reason=(
                    f"Maximum autonomous risk "
                    f"changed to '{risk}'."
                ),
                source="owner_control",
            )

    def get_max_autonomous_risk(self) -> str:
        return self.max_autonomous_risk

    # ========================================================
    # EMERGENCY STOP
    # ========================================================

    def emergency_stop_now(
        self,
        reason: str = "Owner requested emergency stop.",
    ):
        with self._lock:

            self.emergency_stop = True

            self._record(
                tool_name=None,
                permission="control.emergency_stop",
                risk="critical",
                allowed=True,
                reason=reason,
                source="emergency_stop",
            )

        return {
            "success": True,
            "emergency_stop": True,
            "reason": reason,
            "timestamp": self._now(),
        }

    # ========================================================
    # EMERGENCY RESUME
    # ========================================================

    def resume(
        self,
        reason: str = "Owner requested system resume.",
    ):
        with self._lock:

            self.emergency_stop = False

            self._record(
                tool_name=None,
                permission="control.emergency_resume",
                risk="critical",
                allowed=True,
                reason=reason,
                source="owner_control",
            )

        return {
            "success": True,
            "emergency_stop": False,
            "reason": reason,
            "timestamp": self._now(),
        }

    # ========================================================
    # SYSTEM LOCK
    # ========================================================

    def lock(
        self,
        reason: str = "Owner requested system lock.",
    ):
        with self._lock:

            self.system_locked = True

            self._record(
                tool_name=None,
                permission="control.modify",
                risk="critical",
                allowed=True,
                reason=reason,
                source="owner_control",
            )

        return {
            "success": True,
            "system_locked": True,
            "reason": reason,
            "timestamp": self._now(),
        }

    def unlock(
        self,
        reason: str = "Owner requested system unlock.",
    ):
        with self._lock:

            self.system_locked = False

            self._record(
                tool_name=None,
                permission="control.modify",
                risk="critical",
                allowed=True,
                reason=reason,
                source="owner_control",
            )

        return {
            "success": True,
            "system_locked": False,
            "reason": reason,
            "timestamp": self._now(),
        }

    # ========================================================
    # STATUS
    # ========================================================

    def status(self):
        with self._lock:
            return {
                "owner": dict(self.owner_identity),
                "emergency_stop": self.emergency_stop,
                "system_locked": self.system_locked,
                "max_autonomous_risk": self.max_autonomous_risk,
                "permission_count": len(self.permissions),
                "enabled_permissions": sum(
                    1
                    for value in self.permissions.values()
                    if value
                ),
                "disabled_permissions": sum(
                    1
                    for value in self.permissions.values()
                    if not value
                ),
            }

    # ========================================================
    # AUDIT
    # ========================================================

    def record(
        self,
        tool_name,
        permission,
        risk,
        allowed,
        reason,
    ):
        self._record(
            tool_name=tool_name,
            permission=permission,
            risk=risk,
            allowed=allowed,
            reason=reason,
        )

    def audit(self):
        with self._lock:
            return list(self.audit_log)


# ============================================================
# SINGLETON
# ============================================================

permissions = PermissionEngine()