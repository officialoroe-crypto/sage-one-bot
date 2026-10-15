"""Database package bootstrap.

Import additive models here so Base.metadata.create_all() registers profile,
user memory, world-intelligence, Spark, and Evolution tables alongside the
existing SAGE schema.
"""

from identity.profile import UserProfile  # noqa: F401
from identity.memory import ProfileMemory  # noqa: F401
from world_intelligence.models import (  # noqa: F401
    UpgradeProposal,
    WorldKnowledge,
    WorldSignal,
)
from economy.models import (  # noqa: F401
    EvolutionProfile,
    SparkLedgerEntry,
    SparkWallet,
)

from sales.models import SalesActivity, SalesLead  # noqa: F401
