"""Host resource monitoring and local execution protection for SAGE ONE."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
import time

try:
    import psutil
except ImportError:  # pragma: no cover - optional local fallback
    psutil = None


class ResourceBand(str, Enum):
    SAFE = "safe"
    BUSY = "busy"
    HEAVY = "heavy"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ResourceSnapshot:
    cpu_percent: float
    memory_percent: float | None
    cpu_count: int
    timestamp: float

    @property
    def band(self) -> ResourceBand:
        if self.cpu_percent < 40:
            return ResourceBand.SAFE
        if self.cpu_percent < 70:
            return ResourceBand.BUSY
        if self.cpu_percent < 85:
            return ResourceBand.HEAVY
        return ResourceBand.CRITICAL


class ResourceGuard:
    """Lightweight host-resource guard for local SAGE execution."""

    def __init__(
        self,
        soft_cpu_percent: float = 50.0,
        hard_cpu_percent: float = 70.0,
        critical_cpu_percent: float = 85.0,
        sample_interval: float = 0.05,
    ):
        if not 1 <= soft_cpu_percent < hard_cpu_percent <= 100:
            raise ValueError("CPU thresholds must satisfy 1 <= soft < hard <= 100")
        if not hard_cpu_percent < critical_cpu_percent <= 100:
            raise ValueError("critical CPU threshold must be above hard threshold")
        if sample_interval < 0:
            raise ValueError("sample_interval cannot be negative")

        self.soft_cpu_percent = soft_cpu_percent
        self.hard_cpu_percent = hard_cpu_percent
        self.critical_cpu_percent = critical_cpu_percent
        self.sample_interval = sample_interval

    def snapshot(self) -> ResourceSnapshot:
        if psutil is not None:
            cpu = float(psutil.cpu_percent(interval=self.sample_interval))
            memory = float(psutil.virtual_memory().percent)
        else:
            start = os.times()
            wall_start = time.perf_counter()
            if self.sample_interval:
                time.sleep(self.sample_interval)
            end = os.times()
            wall_elapsed = max(time.perf_counter() - wall_start, 0.0001)
            process_cpu = (end.user - start.user) + (end.system - start.system)
            cpu = min(100.0, max(0.0, process_cpu / wall_elapsed * 100.0))
            memory = None

        return ResourceSnapshot(
            cpu_percent=round(cpu, 2),
            memory_percent=round(memory, 2) if memory is not None else None,
            cpu_count=os.cpu_count() or 1,
            timestamp=time.time(),
        )

    def allows(self, snapshot: ResourceSnapshot) -> bool:
        return snapshot.cpu_percent < self.hard_cpu_percent

    def should_throttle(self, snapshot: ResourceSnapshot) -> bool:
        return snapshot.cpu_percent >= self.soft_cpu_percent

    def should_block(self, snapshot: ResourceSnapshot) -> bool:
        return snapshot.cpu_percent >= self.hard_cpu_percent

    def should_pause(self, snapshot: ResourceSnapshot) -> bool:
        return snapshot.cpu_percent >= self.critical_cpu_percent


resource_guard = ResourceGuard()
