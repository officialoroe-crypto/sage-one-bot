"""
SAGE ONE Web Reader.

Responsibilities:
- Fetch public HTTP/HTTPS pages
- Extract meaningful page content
- Extract metadata
- Normalize source information
- Protect against obvious local/private-network targets
- Return structured evidence for the research subsystem

The reader intentionally does NOT summarize or interpret content.
It produces source evidence.
"""

from __future__ import annotations

import hashlib
import ipaddress
import socket
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import trafilatura


DEFAULT_TIMEOUT = 20
DEFAULT_MAX_BYTES = 5_000_000
DEFAULT_MAX_CHARS = 100_000

USER_AGENT = (
    "SAGE-ONE-WebReader/1.0 "
    "(research retrieval; public web content)"
)


@dataclass
class WebDocument:
    success: bool
    url: str
    final_url: str | None
    title: str | None
    author: str | None
    date: str | None
    site_name: str | None
    language: str | None
    content: str
    content_length: int
    word_count: int
    content_sha256: str | None
    retrieved_at: str
    status_code: int | None
    content_type: str | None
    truncated: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WebReader:
    """
    Public-web page reader.

    This component only retrieves and extracts content.
    Higher layers are responsible for research, synthesis,
    citations, decisions, and actions.
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_chars: int = DEFAULT_MAX_CHARS,
    ):
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_chars = max_chars

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_url(self, url: str) -> tuple[bool, str]:
        if not isinstance(url, str) or not url.strip():
            return False, "URL is required."

        url = url.strip()

        if len(url) > 4096:
            return False, "URL is too long."

        parsed = urlparse(url)

        if parsed.scheme.lower() not in {"http", "https"}:
            return False, "Only HTTP and HTTPS URLs are supported."

        if not parsed.hostname:
            return False, "URL hostname is missing."

        hostname = parsed.hostname.strip().lower()

        if hostname in {
            "localhost",
            "localhost.localdomain",
        }:
            return False, "Localhost URLs are blocked."

        # Block obvious internal hostnames.
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            return False, "Internal hostnames are blocked."

        # Resolve hostname and reject private/local IPs.
        try:
            addresses = socket.getaddrinfo(
                hostname,
                parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
                type=socket.SOCK_STREAM,
            )

            for address in addresses:
                ip_text = address[4][0]

                try:
                    ip = ipaddress.ip_address(ip_text)
                except ValueError:
                    continue

                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_multicast
                    or ip.is_reserved
                    or ip.is_unspecified
                ):
                    return False, "Private or local network targets are blocked."

        except socket.gaierror:
            # DNS failure will also be handled during the request.
            pass
        except Exception:
            pass

        return True, ""

    # ------------------------------------------------------------------
    # HTTP retrieval
    # ------------------------------------------------------------------

    def _download(self, url: str) -> requests.Response:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5"
            ),
            "Accept-Language": "en-US,en;q=0.8",
            "Cache-Control": "no-cache",
        }

        # Never let requests follow redirects automatically. A public URL can
        # redirect to localhost, a cloud metadata endpoint, or another private
        # network target, so every redirect destination must pass the same SSRF
        # validation as the original URL.
        current_url = url
        max_redirects = 5

        for _ in range(max_redirects + 1):
            valid, reason = self._validate_url(current_url)
            if not valid:
                raise ValueError(reason)

            response = requests.get(
                current_url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=False,
                stream=True,
            )

            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                response.close()
                if not location:
                    raise ValueError("Redirect response did not provide a location.")
                current_url = urljoin(current_url, location)
                continue

            response.raise_for_status()

            content_type = (
                response.headers.get("content-type", "")
                .lower()
                .strip()
            )

            # Only process web/text documents.
            allowed_types = (
                "text/html",
                "application/xhtml+xml",
                "text/plain",
                "application/xml",
                "text/xml",
            )

            if content_type and not any(
                item in content_type for item in allowed_types
            ):
                response.close()
                raise ValueError(
                    f"Unsupported content type: {content_type}"
                )

            data = bytearray()

            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue

                data.extend(chunk)

                if len(data) > self.max_bytes:
                    response.close()
                    raise ValueError(
                        f"Page exceeds maximum size of {self.max_bytes} bytes."
                    )

            response._sage_content_bytes = bytes(data)
            response.url = current_url

            return response

        raise ValueError(f"Too many redirects (maximum {max_redirects}).")

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _extract(
        self,
        html: str,
        final_url: str,
    ) -> tuple[str, dict[str, Any]]:
        document = trafilatura.bare_extraction(
            html,
            url=final_url,
        )

        if document is None:
            text = trafilatura.extract(
                html,
                url=final_url,
                include_comments=False,
                include_tables=True,
                include_links=True,
                with_metadata=False,
            )

            if not text:
                return "", {}

            return text.strip(), {}

        metadata = document.as_dict()

        text = (
            metadata.get("text")
            or getattr(document, "text", None)
            or ""
        )

        return text.strip(), metadata

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read(
        self,
        url: str,
        max_chars: int | None = None,
    ) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).isoformat()

        valid, reason = self._validate_url(url)

        if not valid:
            return WebDocument(
                success=False,
                url=url,
                final_url=None,
                title=None,
                author=None,
                date=None,
                site_name=None,
                language=None,
                content="",
                content_length=0,
                word_count=0,
                content_sha256=None,
                retrieved_at=retrieved_at,
                status_code=None,
                content_type=None,
                truncated=False,
                error=reason,
            ).to_dict()

        limit = max_chars or self.max_chars

        if limit < 1:
            limit = self.max_chars

        try:
            response = self._download(url)

            final_url = response.url
            status_code = response.status_code
            content_type = response.headers.get("content-type")

            raw_bytes = getattr(
                response,
                "_sage_content_bytes",
                b"",
            )

            encoding = response.encoding or "utf-8"

            try:
                html = raw_bytes.decode(
                    encoding,
                    errors="replace",
                )
            except Exception:
                html = raw_bytes.decode(
                    "utf-8",
                    errors="replace",
                )

            response.close()

            content, metadata = self._extract(
                html,
                final_url,
            )

            if not content:
                return WebDocument(
                    success=False,
                    url=url,
                    final_url=final_url,
                    title=metadata.get("title"),
                    author=metadata.get("author"),
                    date=metadata.get("date"),
                    site_name=metadata.get("sitename"),
                    language=metadata.get("language"),
                    content="",
                    content_length=0,
                    word_count=0,
                    content_sha256=None,
                    retrieved_at=retrieved_at,
                    status_code=status_code,
                    content_type=content_type,
                    truncated=False,
                    error="No meaningful page content could be extracted.",
                ).to_dict()

            truncated = False

            if len(content) > limit:
                content = content[:limit].rstrip()
                truncated = True

            digest = hashlib.sha256(
                content.encode("utf-8", errors="replace")
            ).hexdigest()

            return WebDocument(
                success=True,
                url=url,
                final_url=final_url,
                title=metadata.get("title"),
                author=metadata.get("author"),
                date=metadata.get("date"),
                site_name=(
                    metadata.get("sitename")
                    or metadata.get("site_name")
                ),
                language=metadata.get("language"),
                content=content,
                content_length=len(content),
                word_count=len(content.split()),
                content_sha256=digest,
                retrieved_at=retrieved_at,
                status_code=status_code,
                content_type=content_type,
                truncated=truncated,
                error=None,
            ).to_dict()

        except requests.Timeout:
            return WebDocument(
                success=False,
                url=url,
                final_url=None,
                title=None,
                author=None,
                date=None,
                site_name=None,
                language=None,
                content="",
                content_length=0,
                word_count=0,
                content_sha256=None,
                retrieved_at=retrieved_at,
                status_code=None,
                content_type=None,
                truncated=False,
                error="Web request timed out.",
            ).to_dict()

        except requests.RequestException as exc:
            return WebDocument(
                success=False,
                url=url,
                final_url=None,
                title=None,
                author=None,
                date=None,
                site_name=None,
                language=None,
                content="",
                content_length=0,
                word_count=0,
                content_sha256=None,
                retrieved_at=retrieved_at,
                status_code=None,
                content_type=None,
                truncated=False,
                error=f"Web request failed: {exc}",
            ).to_dict()

        except Exception as exc:
            return WebDocument(
                success=False,
                url=url,
                final_url=None,
                title=None,
                author=None,
                date=None,
                site_name=None,
                language=None,
                content="",
                content_length=0,
                word_count=0,
                content_sha256=None,
                retrieved_at=retrieved_at,
                status_code=None,
                content_type=None,
                truncated=False,
                error=f"Reader error: {exc}",
            ).to_dict()


web_reader = WebReader()