from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionMode(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass(frozen=True)
class ConnectivityState:
    online: bool
    reason: str = ""


class ExecutionModeRouter:
    """Select online/offline execution without choosing a provider."""

    def select(self, connectivity: ConnectivityState) -> ExecutionMode:
        return ExecutionMode.ONLINE if connectivity.online else ExecutionMode.OFFLINE


mode_router = ExecutionModeRouter()
