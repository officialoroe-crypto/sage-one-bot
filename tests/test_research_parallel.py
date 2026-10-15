import threading
import time

from research.parallel import ParallelResearchEngine


def test_parallel_research_limits_search_concurrency_and_preserves_order():
    engine = ParallelResearchEngine(max_parallel=2)
    active = 0
    peak = 0
    lock = threading.Lock()

    def fake_search(query, max_results):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return {
            "success": True,
            "results": [
                {
                    "url": f"https://example.com/{query.replace(' ', '-')}",
                    "title": query,
                    "snippet": "snippet",
                    "rank": 1,
                }
            ],
        }

    engine._search = fake_search
    sources, errors = engine._collect_sources(["one", "two", "three", "four"], 2)

    assert not errors
    assert peak <= 2
    assert [source.query for source in sources] == ["one", "two", "three", "four"]


def test_parallel_research_limits_read_concurrency_and_applies_results_deterministically():
    engine = ParallelResearchEngine(max_parallel=2)
    active = 0
    peak = 0
    lock = threading.Lock()

    sources = [
        engine._source_from_search_item(
            {"title": f"source-{index}", "snippet": "snippet", "rank": index + 1},
            f"https://example.com/{index}",
            "query",
            index + 1,
        )
        for index in range(4)
    ]

    def fake_read(url):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        index = url.rsplit("/", 1)[-1]
        return {
            "success": True,
            "result": {
                "success": True,
                "title": f"read-{index}",
                "content": f"content-{index}",
                "content_length": 9,
                "word_count": 1,
            },
        }

    engine._read_source = fake_read
    errors = []
    read_count, readable_count = engine._read_sources(sources, errors)

    assert not errors
    assert peak <= 2
    assert read_count == 4
    assert readable_count == 4
    assert [source.title for source in sources] == ["read-0", "read-1", "read-2", "read-3"]


def test_public_research_engine_uses_parallel_implementation():
    import research.engine as engine_module
    import research

    assert isinstance(research.research_engine, ParallelResearchEngine)
    assert engine_module.research_engine is research.research_engine
