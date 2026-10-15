"""Transparent, configurable source-selection rules for World Intelligence."""

from __future__ import annotations

import os
from collections import Counter
from urllib.parse import urlparse


class WorldSourcePolicy:
    def __init__(
        self,
        *,
        allowed_domains: set[str] | None = None,
        blocked_domains: set[str] | None = None,
        max_sources_per_domain: int = 2,
    ) -> None:
        self.allowed_domains = allowed_domains
        self.blocked_domains = blocked_domains or set()
        self.max_sources_per_domain = max(1, int(max_sources_per_domain))

    @classmethod
    def from_environment(cls) -> "WorldSourcePolicy":
        def domains(name: str) -> set[str]:
            return {
                item.strip().lower().lstrip(".")
                for item in os.getenv(name, "").split(",")
                if item.strip()
            }

        allowed = domains("SAGE_WORLD_ALLOWED_DOMAINS")
        return cls(
            allowed_domains=allowed or None,
            blocked_domains=domains("SAGE_WORLD_BLOCKED_DOMAINS"),
            max_sources_per_domain=max(
                1,
                int(os.getenv("SAGE_WORLD_MAX_SOURCES_PER_DOMAIN", "2")),
            ),
        )

    @staticmethod
    def domain(url: str) -> str | None:
        try:
            parsed = urlparse(str(url).strip())
        except ValueError:
            return None
        host = (parsed.hostname or "").lower().rstrip(".")
        return host or None

    @staticmethod
    def valid_url(url: str) -> bool:
        try:
            parsed = urlparse(str(url).strip())
        except ValueError:
            return False
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)

    @staticmethod
    def matches_domain(host: str, domain: str) -> bool:
        return host == domain or host.endswith("." + domain)

    def allows(self, url: str) -> tuple[bool, str]:
        if not self.valid_url(url):
            return False, "invalid_or_unsupported_url"

        host = self.domain(url)
        if host is None:
            return False, "missing_hostname"

        if any(self.matches_domain(host, blocked) for blocked in self.blocked_domains):
            return False, "blocked_domain"

        if self.allowed_domains and not any(
            self.matches_domain(host, allowed)
            for allowed in self.allowed_domains
        ):
            return False, "domain_not_in_allowlist"

        return True, "allowed"

    def select(self, sources: list[dict], limit: int = 20) -> tuple[list[dict], list[dict]]:
        selected: list[dict] = []
        rejected: list[dict] = []
        counts: Counter[str] = Counter()

        for source in sources:
            if len(selected) >= limit:
                rejected.append({
                    "url": source.get("final_url") or source.get("url"),
                    "reason": "source_limit",
                })
                continue

            url = str(source.get("final_url") or source.get("url") or "").strip()
            allowed, reason = self.allows(url)
            host = self.domain(url) or "unknown"

            if not allowed:
                rejected.append({"url": url, "reason": reason})
                continue

            if counts[host] >= self.max_sources_per_domain:
                rejected.append({"url": url, "reason": "domain_diversity_limit"})
                continue

            counts[host] += 1
            selected.append(source)

        return selected, rejected


world_source_policy = WorldSourcePolicy.from_environment()
