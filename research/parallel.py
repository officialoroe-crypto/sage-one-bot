"""Bounded parallel execution for independent Research OS I/O phases.

Search queries and source reads are independent network/tool operations, so
SAGE can overlap them without changing evidence ordering. The concurrency
bound prevents research from becoming an uncontrolled local workload.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from research.engine import ResearchEngine


class ParallelResearchEngine(ResearchEngine):
    """Research engine with bounded parallel search and read phases."""

    def __init__(self, max_parallel: int = 3):
        super().__init__()
        self.max_parallel = max(1, int(max_parallel))

    def _collect_sources(self, queries, result_limit):
        """Run independent searches concurrently, then merge deterministically."""
        results_by_index = {}
        errors_by_index = {}

        with ThreadPoolExecutor(
            max_workers=min(self.max_parallel, len(queries)),
            thread_name_prefix="sage-research-search",
        ) as executor:
            futures = {
                executor.submit(self._search, query, result_limit): index
                for index, query in enumerate(queries)
            }
            for future in as_completed(futures):
                index = futures[future]
                try:
                    results_by_index[index] = future.result()
                except Exception as error:
                    errors_by_index[index] = str(error)

        sources = []
        errors = []
        seen_urls = set()

        for index, query in enumerate(queries):
            if index in errors_by_index:
                errors.append(f"{query}: {errors_by_index[index]}")
                continue

            search_result = results_by_index.get(index)
            if not isinstance(search_result, dict) or not search_result.get("success"):
                error = search_result.get("error", "Unknown search error") if isinstance(search_result, dict) else "Invalid search response."
                errors.append(f"{query}: {error}")
                continue

            nested = self._unwrap(search_result)
            if not nested:
                errors.append(f"{query}: invalid search response.")
                continue

            results = nested.get("results", [])
            if not isinstance(results, list):
                errors.append(f"{query}: search results were not a list.")
                continue

            for item in results:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url", "")).strip()
                normalized_url = self._normalize_url(url)
                if not normalized_url or normalized_url in seen_urls:
                    continue
                seen_urls.add(normalized_url)
                try:
                    rank = int(item.get("rank", len(sources) + 1))
                except Exception:
                    rank = len(sources) + 1
                sources.append(
                    self._source_from_search_item(item, url, query, rank)
                )

        return sources, errors

    def _source_from_search_item(self, item, url, query, rank):
        from research.engine import ResearchSource

        return ResearchSource(
            source_id=self._source_id(url),
            rank=rank,
            title=str(item.get("title", "")),
            url=url,
            snippet=str(item.get("snippet", "")),
            query=query,
            retrieved_at=self._now(),
        )

    def _read_sources(self, sources, errors):
        """Read independent sources concurrently and apply results by source order."""
        sources_to_read = sources[: self.max_sources_to_read]
        results = {}
        failures = {}

        with ThreadPoolExecutor(
            max_workers=min(self.max_parallel, len(sources_to_read)) or 1,
            thread_name_prefix="sage-research-read",
        ) as executor:
            futures = {
                executor.submit(self._read_source, source.url): index
                for index, source in enumerate(sources_to_read)
            }
            for future in as_completed(futures):
                index = futures[future]
                try:
                    results[index] = future.result()
                except Exception as error:
                    failures[index] = str(error)

        read_count = 0
        readable_count = 0

        for index, source in enumerate(sources_to_read):
            source.read = True
            read_count += 1

            if index in failures:
                source.read_success = False
                source.read_error = failures[index]
                errors.append(f"{source.url}: {failures[index]}")
                continue

            read_result = results.get(index)
            if not isinstance(read_result, dict) or not read_result.get("success"):
                nested = self._unwrap(read_result) if isinstance(read_result, dict) else None
                error = nested.get("error") if nested else (read_result.get("error", "Unknown reader error") if isinstance(read_result, dict) else "Invalid reader response.")
                source.read_success = False
                source.read_error = str(error)
                errors.append(f"{source.url}: {error}")
                continue

            document = self._unwrap(read_result)
            if not document:
                source.read_success = False
                source.read_error = "Invalid web reader response."
                errors.append(f"{source.url}: invalid reader response.")
                continue

            source.read_success = bool(document.get("success"))
            if not source.read_success:
                source.read_error = str(document.get("error", "Web page could not be read."))
                errors.append(f"{source.url}: {source.read_error}")
                continue

            readable_count += 1
            source.final_url = document.get("final_url")
            source.title = str(document.get("title")) if document.get("title") else source.title
            source.author = str(document.get("author")) if document.get("author") else None
            source.publication_date = str(document.get("date")) if document.get("date") else None
            source.site_name = str(document.get("site_name")) if document.get("site_name") else None
            source.language = str(document.get("language")) if document.get("language") else None
            source.content = str(document.get("content", ""))
            source.content_length = int(document.get("content_length", len(source.content)) or 0)
            source.word_count = int(document.get("word_count", len(source.content.split())) or 0)
            source.content_sha256 = document.get("content_sha256")
            source.read_error = None

        return read_count, readable_count


parallel_research_engine = ParallelResearchEngine()
