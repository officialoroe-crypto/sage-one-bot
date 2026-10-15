from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from tools.registry import registry


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class ResearchSource:
    source_id: str
    rank: int
    title: str
    url: str
    snippet: str
    query: str
    retrieved_at: str

    # Web-reading fields
    read: bool = False
    read_success: bool = False
    final_url: str | None = None
    author: str | None = None
    publication_date: str | None = None
    site_name: str | None = None
    language: str | None = None
    content: str = ""
    content_length: int = 0
    word_count: int = 0
    content_sha256: str | None = None
    read_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchResult:
    success: bool
    question: str
    queries: list[str]
    sources: list[ResearchSource]
    source_count: int
    read_count: int
    readable_count: int
    evidence_count: int
    errors: list[str]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "question": self.question,
            "queries": self.queries,
            "sources": [
                source.to_dict()
                for source in self.sources
            ],
            "source_count": self.source_count,
            "read_count": self.read_count,
            "readable_count": self.readable_count,
            "evidence_count": self.evidence_count,
            "errors": self.errors,
            "created_at": self.created_at,
        }


# ============================================================
# RESEARCH ENGINE
# ============================================================

class ResearchEngine:

    def __init__(self):
        self.max_queries = 5
        self.max_results_per_query = 5
        self.max_sources_to_read = 10
        self.max_chars_per_source = 100000

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    @staticmethod
    def _now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    # --------------------------------------------------------
    # SOURCE ID
    # --------------------------------------------------------

    @staticmethod
    def _source_id(url: str) -> str:
        import hashlib

        return hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()[:16]

    # --------------------------------------------------------
    # URL NORMALIZATION
    # --------------------------------------------------------

    @staticmethod
    def _normalize_url(url: str) -> str:
        url = str(url).strip()

        if not url:
            return ""

        parsed = urlparse(url)

        scheme = parsed.scheme.lower()
        hostname = (parsed.hostname or "").lower()

        if parsed.port:
            netloc = f"{hostname}:{parsed.port}"
        else:
            netloc = hostname

        path = parsed.path.rstrip("/")

        return f"{scheme}://{netloc}{path}"

    # --------------------------------------------------------
    # QUERY GENERATION
    # --------------------------------------------------------

    def build_queries(
        self,
        question: str,
    ) -> list[str]:

        question = question.strip()

        if not question:
            return []

        queries = [
            question,
            f"{question} latest information",
            f"{question} official source",
            f"{question} analysis",
            f"{question} evidence",
        ]

        unique: list[str] = []
        seen: set[str] = set()

        for query in queries:

            normalized = query.lower().strip()

            if normalized in seen:
                continue

            seen.add(normalized)
            unique.append(query)

        return unique[:self.max_queries]

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    def _search(
        self,
        query: str,
        max_results: int,
    ) -> dict[str, Any]:

        if not registry.exists("web_search"):

            return {
                "success": False,
                "error": "web_search tool is not registered.",
            }

        try:

            return registry.execute(
                "web_search",
                {
                    "query": query,
                    "max_results": max_results,
                },
            )

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
            }

    # --------------------------------------------------------
    # READ
    # --------------------------------------------------------

    def _read_source(
        self,
        url: str,
    ) -> dict[str, Any]:

        if not registry.exists("web_read"):

            return {
                "success": False,
                "error": "web_read tool is not registered.",
            }

        try:

            return registry.execute(
                "web_read",
                {
                    "url": url,
                    "max_chars": self.max_chars_per_source,
                },
            )

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
            }

    # --------------------------------------------------------
    # EXTRACT NESTED RESULT
    # --------------------------------------------------------

    @staticmethod
    def _unwrap(
        value: Any,
    ) -> dict[str, Any] | None:

        if not isinstance(value, dict):
            return None

        current = value

        # Handles nested tool wrappers such as:
        #
        # {
        #   "success": true,
        #   "tool": "...",
        #   "result": {
        #       "success": true,
        #       ...
        #   }
        # }
        #
        for _ in range(5):

            if not isinstance(current, dict):
                return None

            nested = current.get("result")

            if isinstance(nested, dict):
                current = nested
                continue

            return current

        return current if isinstance(current, dict) else None

    # --------------------------------------------------------
    # SOURCE CREATION
    # --------------------------------------------------------

    def _collect_sources(
        self,
        queries: list[str],
        result_limit: int,
    ) -> tuple[list[ResearchSource], list[str]]:

        sources: list[ResearchSource] = []
        errors: list[str] = []

        seen_urls: set[str] = set()

        for query in queries:

            search_result = self._search(
                query=query,
                max_results=result_limit,
            )

            if not search_result.get("success"):

                errors.append(
                    f"{query}: "
                    f"{search_result.get('error', 'Unknown search error')}"
                )

                continue

            nested = self._unwrap(search_result)

            if not nested:
                errors.append(
                    f"{query}: invalid search response."
                )
                continue

            results = nested.get(
                "results",
                [],
            )

            if not isinstance(results, list):
                errors.append(
                    f"{query}: search results were not a list."
                )
                continue

            for item in results:

                if not isinstance(item, dict):
                    continue

                url = str(
                    item.get("url", "")
                ).strip()

                if not url:
                    continue

                normalized_url = self._normalize_url(url)

                if not normalized_url:
                    continue

                if normalized_url in seen_urls:
                    continue

                seen_urls.add(normalized_url)

                try:
                    rank = int(
                        item.get(
                            "rank",
                            len(sources) + 1,
                        )
                    )
                except Exception:
                    rank = len(sources) + 1

                sources.append(
                    ResearchSource(
                        source_id=self._source_id(url),
                        rank=rank,
                        title=str(
                            item.get(
                                "title",
                                "",
                            )
                        ),
                        url=url,
                        snippet=str(
                            item.get(
                                "snippet",
                                "",
                            )
                        ),
                        query=query,
                        retrieved_at=self._now(),
                    )
                )

        return sources, errors

    # --------------------------------------------------------
    # READ SOURCES
    # --------------------------------------------------------

    def _read_sources(
        self,
        sources: list[ResearchSource],
        errors: list[str],
    ) -> tuple[int, int]:

        read_count = 0
        readable_count = 0

        # Only read the highest-ranked unique sources.
        sources_to_read = sources[
            :self.max_sources_to_read
        ]

        for source in sources_to_read:

            source.read = True
            read_count += 1

            read_result = self._read_source(
                source.url
            )

            if not read_result.get("success"):

                nested = self._unwrap(
                    read_result
                )

                error = (
                    nested.get("error")
                    if nested
                    else read_result.get(
                        "error",
                        "Unknown reader error",
                    )
                )

                source.read_success = False
                source.read_error = str(error)

                errors.append(
                    f"{source.url}: {error}"
                )

                continue

            document = self._unwrap(
                read_result
            )

            if not document:
                source.read_success = False
                source.read_error = (
                    "Invalid web reader response."
                )

                errors.append(
                    f"{source.url}: invalid reader response."
                )

                continue

            source.read_success = bool(
                document.get("success")
            )

            if not source.read_success:

                source.read_error = str(
                    document.get(
                        "error",
                        "Web page could not be read.",
                    )
                )

                errors.append(
                    f"{source.url}: {source.read_error}"
                )

                continue

            readable_count += 1

            source.final_url = document.get(
                "final_url"
            )

            source.title = (
                str(document.get("title"))
                if document.get("title")
                else source.title
            )

            source.author = (
                str(document.get("author"))
                if document.get("author")
                else None
            )

            source.publication_date = (
                str(document.get("date"))
                if document.get("date")
                else None
            )

            source.site_name = (
                str(document.get("site_name"))
                if document.get("site_name")
                else None
            )

            source.language = (
                str(document.get("language"))
                if document.get("language")
                else None
            )

            source.content = str(
                document.get(
                    "content",
                    "",
                )
            )

            source.content_length = int(
                document.get(
                    "content_length",
                    len(source.content),
                )
                or 0
            )

            source.word_count = int(
                document.get(
                    "word_count",
                    len(source.content.split()),
                )
                or 0
            )

            source.content_sha256 = document.get(
                "content_sha256"
            )

            source.read_error = None

        return read_count, readable_count

    # --------------------------------------------------------
    # EVIDENCE
    # --------------------------------------------------------

    @staticmethod
    def _build_evidence(
        sources: list[ResearchSource],
    ) -> list[dict[str, Any]]:

        evidence: list[dict[str, Any]] = []

        for source in sources:

            if not source.read_success:
                continue

            if not source.content.strip():
                continue

            evidence.append(
                {
                    "evidence_id": (
                        f"{source.source_id}:content"
                    ),
                    "source_id": source.source_id,
                    "title": source.title,
                    "url": source.final_url or source.url,
                    "site_name": source.site_name,
                    "author": source.author,
                    "publication_date": source.publication_date,
                    "language": source.language,
                    "content": source.content,
                    "content_length": source.content_length,
                    "word_count": source.word_count,
                    "content_sha256": source.content_sha256,
                    "retrieved_at": source.retrieved_at,
                }
            )

        return evidence

    # --------------------------------------------------------
    # MAIN RESEARCH METHOD
    # --------------------------------------------------------

    def research(
        self,
        question: str,
        max_queries: int | None = None,
        max_results_per_query: int | None = None,
    ) -> dict[str, Any]:

        question = str(
            question
        ).strip()

        if not question:

            return {
                "success": False,
                "error": "Research question cannot be empty.",
            }

        query_limit = (
            max_queries
            if max_queries is not None
            else self.max_queries
        )

        result_limit = (
            max_results_per_query
            if max_results_per_query is not None
            else self.max_results_per_query
        )

        try:
            query_limit = max(
                1,
                min(int(query_limit), 10),
            )
        except Exception:
            query_limit = self.max_queries

        try:
            result_limit = max(
                1,
                min(int(result_limit), 10),
            )
        except Exception:
            result_limit = self.max_results_per_query

        queries = self.build_queries(
            question
        )[:query_limit]

        if not queries:

            return {
                "success": False,
                "error": "No research queries could be generated.",
            }

        # ----------------------------------------------------
        # PHASE 1: SEARCH
        # ----------------------------------------------------

        sources, errors = self._collect_sources(
            queries=queries,
            result_limit=result_limit,
        )

        # ----------------------------------------------------
        # PHASE 2: READ
        # ----------------------------------------------------

        read_count, readable_count = self._read_sources(
            sources=sources,
            errors=errors,
        )

        # ----------------------------------------------------
        # PHASE 3: EVIDENCE
        # ----------------------------------------------------

        evidence = self._build_evidence(
            sources
        )

        # Evidence is deliberately attached to the response
        # so later synthesis layers can consume it directly.
        result = ResearchResult(
            success=len(sources) > 0,
            question=question,
            queries=queries,
            sources=sources,
            source_count=len(sources),
            read_count=read_count,
            readable_count=readable_count,
            evidence_count=len(evidence),
            errors=errors,
            created_at=self._now(),
        ).to_dict()

        result["evidence"] = evidence

        # ----------------------------------------------------
        # PIPELINE STATUS
        # ----------------------------------------------------

        result["pipeline"] = {
            "search": {
                "completed": len(sources) > 0,
                "source_count": len(sources),
            },
            "read": {
                "completed": read_count > 0,
                "attempted": read_count,
                "successful": readable_count,
            },
            "evidence": {
                "completed": len(evidence) > 0,
                "count": len(evidence),
            },
            "synthesis": {
                "completed": False,
                "status": "pending",
            },
        }

        return result


research_engine = ResearchEngine()