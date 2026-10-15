"""SAGE ONE World Intelligence and continuous public-knowledge learning."""

from permissions.engine import permissions

# World learning is explicitly granted as a bounded public-information
# capability. It cannot write to the web, change permissions, or self-modify.
permissions.permissions.setdefault("world.read", True)
permissions.permissions.setdefault("world.observe", True)
permissions.permissions.setdefault("world.learn", True)
permissions.permissions.setdefault("world.propose_upgrade", True)
permissions.permission_risk.setdefault("world.read", "low")
permissions.permission_risk.setdefault("world.observe", "low")
permissions.permission_risk.setdefault("world.learn", "low")
permissions.permission_risk.setdefault("world.propose_upgrade", "medium")

from world_intelligence.engine import world_intelligence  # noqa: E402

__all__ = ["world_intelligence"]
