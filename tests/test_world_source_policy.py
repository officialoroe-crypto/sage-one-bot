from world_intelligence.source_policy import WorldSourcePolicy


def test_policy_accepts_http_and_https():
    policy = WorldSourcePolicy()
    assert policy.allows("https://example.com/article")[0]
    assert policy.allows("http://example.com/article")[0]
    assert not policy.allows("ftp://example.com/file")[0]


def test_policy_supports_subdomains_and_blocking():
    policy = WorldSourcePolicy(
        allowed_domains={"example.com"},
        blocked_domains={"blocked.example.com"},
    )
    assert policy.allows("https://news.example.com/story")[0]
    assert not policy.allows("https://blocked.example.com/story")[0]


def test_policy_limits_domain_concentration():
    policy = WorldSourcePolicy(max_sources_per_domain=1)
    selected, rejected = policy.select([
        {"url": "https://example.com/a"},
        {"url": "https://example.com/b"},
        {"url": "https://other.com/c"},
    ])
    assert len(selected) == 2
    assert len(rejected) == 1
    assert rejected[0]["reason"] == "domain_diversity_limit"


def test_allowlist_is_explicit():
    policy = WorldSourcePolicy(allowed_domains={"official.example"})
    selected, rejected = policy.select([
        {"url": "https://official.example/a"},
        {"url": "https://other.example/b"},
    ])
    assert len(selected) == 1
    assert rejected[0]["reason"] == "domain_not_in_allowlist"
