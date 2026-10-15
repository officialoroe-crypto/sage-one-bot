"""SAGE ONE Research subsystem."""

import research.engine as _research_engine_module

from research.engine import ResearchEngine, ResearchResult, ResearchSource
from research.parallel import ParallelResearchEngine, parallel_research_engine

# Keep the public engine name stable while upgrading its independent I/O
# phases to bounded parallel execution. research.synthesis imports the same
# module-level singleton, so the specialized Research OS pipeline receives the
# optimization without changing its public API.
_research_engine_module.research_engine = parallel_research_engine
research_engine = parallel_research_engine

from research.synthesis import (
    ResearchClaim,
    ResearchReport,
    ResearchSynthesisEngine,
    research_synthesis_engine,
)

__all__ = [
    "ResearchEngine",
    "ParallelResearchEngine",
    "ResearchResult",
    "ResearchSource",
    "research_engine",
    "parallel_research_engine",
    "ResearchClaim",
    "ResearchReport",
    "ResearchSynthesisEngine",
    "research_synthesis_engine",
]
