"""
SAGE ONE Built-in Tools.

Core tools exposed through the Tool Registry.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from tools.registry import registry


# ============================================================
# SYSTEM TIME
# ============================================================

def sage_time() -> dict[str, Any]:

    return {
        "success": True,
        "tool": "sage_time",
        "result": {
            "utc_time": datetime.now(
                timezone.utc
            ).isoformat()
        },
    }


# ============================================================
# SYSTEM STATUS
# ============================================================

def sage_status() -> dict[str, Any]:

    return {
        "success": True,
        "tool": "sage_status",
        "result": {
            "service": "SAGE ONE",
            "status": "operational",
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    }


# ============================================================
# WEB SEARCH
# ============================================================

def web_search(
    query: str,
    max_results: int = 5,
) -> dict[str, Any]:

    if not isinstance(
        query,
        str,
    ) or not query.strip():

        return {
            "success": False,
            "query": query,
            "result_count": 0,
            "results": [],
            "error": "Search query is required.",
        }

    try:

        from ddgs import DDGS

        limit = max(
            1,
            min(
                int(max_results),
                10,
            ),
        )

        search_kwargs = {
            "query": query.strip(),
            "max_results": limit,
        }

        raw_results = DDGS().text(
            **search_kwargs
        )

        results = []

        for rank, item in enumerate(
            raw_results or [],
            start=1,
        ):

            results.append(
                {
                    "rank": rank,
                    "title": item.get(
                        "title"
                    ),
                    "url": (
                        item.get("href")
                        or item.get("url")
                    ),
                    "snippet": (
                        item.get("body")
                        or item.get("snippet")
                    ),
                }
            )

        return {
            "success": True,
            "query": query.strip(),
            "result_count": len(
                results
            ),
            "results": results,
        }

    except Exception as exc:

        return {
            "success": False,
            "query": query,
            "result_count": 0,
            "results": [],
            "error": (
                f"Web search failed: {exc}"
            ),
        }


# ============================================================
# WEB READER
# ============================================================

def web_read(
    url: str,
    max_chars: int = 100000,
) -> dict[str, Any]:

    try:

        from web.reader import web_reader

        result = web_reader.read(
            url=url,
            max_chars=max_chars,
        )

        return {
            "success": bool(
                result.get(
                    "success"
                )
            ),
            "tool": "web_read",
            "result": result,
        }

    except Exception as exc:

        return {
            "success": False,
            "tool": "web_read",
            "result": {
                "success": False,
                "url": url,
                "content": "",
                "error": (
                    f"Web reader failed: {exc}"
                ),
            },
        }


# ============================================================
# RESEARCH
# ============================================================

def research_web(
    question: str,
    max_queries: int = 5,
    max_results_per_query: int = 5,
):

    from research.engine import (
        research_engine
    )

    return research_engine.research(
        question=question,
        max_queries=max_queries,
        max_results_per_query=(
            max_results_per_query
        ),
    )


# ============================================================
# RESEARCH SYNTHESIS
# ============================================================

def research_synthesize(
    question: str,
    max_queries: int = 5,
    max_results_per_query: int = 5,
):

    from research.synthesis import (
        research_synthesis_engine
    )

    return (
        research_synthesis_engine.synthesize(
            question=question,
            max_queries=max_queries,
            max_results_per_query=(
                max_results_per_query
            ),
        )
    )


# ============================================================
# REGISTER TOOLS
# ============================================================

def register_builtin_tools():

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    if not registry.exists(
        "sage_time"
    ):

        registry.register(
            name="sage_time",
            description=(
                "Get the current UTC timestamp."
            ),
            capability="system.time",
            risk="low",
            permission="system.read",
            handler=sage_time,
            parameters={
                "properties": {}
            },
        )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if not registry.exists(
        "sage_status"
    ):

        registry.register(
            name="sage_status",
            description=(
                "Get the current SAGE ONE runtime status."
            ),
            capability="system.status",
            risk="low",
            permission="system.status",
            handler=sage_status,
            parameters={
                "properties": {}
            },
        )

    # --------------------------------------------------------
    # WEB SEARCH
    # --------------------------------------------------------

    if not registry.exists(
        "web_search"
    ):

        registry.register(
            name="web_search",
            description=(
                "Search the public web and return "
                "ranked search results with titles, "
                "URLs, and snippets."
            ),
            capability="web.search",
            risk="low",
            permission="web.read",
            handler=web_search,
            parameters={
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The web search query."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": (
                            "Maximum number of results."
                        ),
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": [
                    "query"
                ],
            },
        )

    # --------------------------------------------------------
    # WEB READ
    # --------------------------------------------------------

    if not registry.exists(
        "web_read"
    ):

        registry.register(
            name="web_read",
            description=(
                "Open a public HTTP/HTTPS webpage "
                "and extract its meaningful main "
                "content and metadata."
            ),
            capability="web.read",
            risk="low",
            permission="web.read",
            handler=web_read,
            parameters={
                "properties": {
                    "url": {
                        "type": "string",
                        "description": (
                            "Public webpage URL to read."
                        ),
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": (
                            "Maximum extracted characters returned."
                        ),
                        "minimum": 1000,
                        "maximum": 200000,
                    },
                },
                "required": [
                    "url"
                ],
            },
        )

    # --------------------------------------------------------
    # RAW RESEARCH
    # --------------------------------------------------------

    if not registry.exists(
        "research_web"
    ):

        registry.register(
            name="research_web",
            description=(
                "Research a question using multiple "
                "public web searches and return "
                "deduplicated source evidence."
            ),
            capability="research.execute",
            risk="low",
            permission="research.execute",
            handler=research_web,
            parameters={
                "properties": {
                    "question": {
                        "type": "string",
                        "description": (
                            "Research question."
                        ),
                    },
                    "max_queries": {
                        "type": "integer",
                        "description": (
                            "Maximum search queries."
                        ),
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "max_results_per_query": {
                        "type": "integer",
                        "description": (
                            "Maximum search results "
                            "per query."
                        ),
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": [
                    "question"
                ],
            },
        )

    # --------------------------------------------------------
    # FULL RESEARCH + SYNTHESIS
    # --------------------------------------------------------

    if not registry.exists(
        "research_synthesize"
    ):

        registry.register(
            name="research_synthesize",
            description=(
                "Perform multi-source web research, "
                "read the sources, build evidence, "
                "cross-check claims, detect conflicts, "
                "assign confidence, and produce a "
                "citation-ready research report."
            ),
            capability="research.synthesize",
            risk="low",
            permission="research.execute",
            handler=research_synthesize,
            parameters={
                "properties": {
                    "question": {
                        "type": "string",
                        "description": (
                            "Question that SAGE should research "
                            "and synthesize."
                        ),
                    },
                    "max_queries": {
                        "type": "integer",
                        "description": (
                            "Maximum number of search queries."
                        ),
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "max_results_per_query": {
                        "type": "integer",
                        "description": (
                            "Maximum results per search query."
                        ),
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": [
                    "question"
                ],
            },
        )


# Register immediately when imported.
register_builtin_tools()