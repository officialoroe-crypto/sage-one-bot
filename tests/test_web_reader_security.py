from dataclasses import dataclass
from web.reader import WebReader


@dataclass
class FakeResponse:
    status_code: int
    url: str
    headers: dict[str, str]
    chunks: list[bytes]
    closed: bool = False

    def iter_content(self, chunk_size: int = 65536):
        yield from self.chunks

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def close(self):
        self.closed = True


def test_web_reader_revalidates_redirect_targets(monkeypatch):
    reader = WebReader()
    calls: list[str] = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if url == "https://public.example/start":
            return FakeResponse(
                status_code=302,
                url=url,
                headers={"location": "http://127.0.0.1:8000/admin"},
                chunks=[],
            )
        raise AssertionError("Private redirect target must never be requested.")

    monkeypatch.setattr("web.reader.requests.get", fake_get)

    result = reader.read("https://public.example/start")

    assert result["success"] is False
    assert "Private or local network targets are blocked" in result["error"]
    assert calls == ["https://public.example/start"]


def test_web_reader_follows_safe_redirects_after_validation(monkeypatch):
    reader = WebReader()
    calls: list[str] = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if url == "https://public.example/start":
            return FakeResponse(
                status_code=302,
                url=url,
                headers={"location": "/article"},
                chunks=[],
            )
        return FakeResponse(
            status_code=200,
            url=url,
            headers={"content-type": "text/html; charset=utf-8"},
            chunks=[b"<html><body><article>SAGE public content</article></body></html>"],
        )

    monkeypatch.setattr("web.reader.requests.get", fake_get)
    monkeypatch.setattr(reader, "_validate_url", lambda url: (True, ""))

    response = reader._download("https://public.example/start")

    assert response.url == "https://public.example/article"
    assert response._sage_content_bytes.startswith(b"<html>")
    response.close()
    assert calls == [
        "https://public.example/start",
        "https://public.example/article",
    ]


def test_web_reader_caps_redirect_chain(monkeypatch):
    reader = WebReader()

    def fake_get(url, **kwargs):
        return FakeResponse(
            status_code=302,
            url=url,
            headers={"location": url + "/next"},
            chunks=[],
        )

    monkeypatch.setattr("web.reader.requests.get", fake_get)
    monkeypatch.setattr(reader, "_validate_url", lambda url: (True, ""))

    result = reader.read("https://public.example/start")

    assert result["success"] is False
    assert "Too many redirects" in result["error"]
