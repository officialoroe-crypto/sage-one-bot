"""Keep Flutter API client paths aligned with the FastAPI route surface."""

from pathlib import Path
import re

ROOT = Path(__file__).parents[1]
CLIENT_FILES = [
    ROOT / "frontend" / "lib" / "core" / "sage_api.dart",
    ROOT / "frontend" / "lib" / "core" / "identity_client.dart",
]
ROUTE_FILES = [
    ROOT / "app" / "main.py",
    ROOT / "identity" / "api.py",
    ROOT / "economy" / "api.py",
    ROOT / "workflows" / "api.py",
    ROOT / "world_intelligence" / "api.py",
    ROOT / "missions" / "api.py",
    ROOT / "opportunities" / "api.py",
    ROOT / "learning" / "api.py",
]


def _normalize(path: str) -> str:
    path = path.split("?", maxsplit=1)[0]
    path = re.sub(r"\$[A-Za-z_]\w*", "{param}", path)
    return re.sub(r"\{[^}]+\}", "{param}", path)


def _client_endpoints() -> set[tuple[str, str]]:
    sage_api = CLIENT_FILES[0].read_text(encoding="utf-8")
    identity = CLIENT_FILES[1].read_text(encoding="utf-8")
    endpoints: set[tuple[str, str]] = set()

    verbs = {
        "authorizedGet": "GET",
        "authorizedPost": "POST",
        "authorizedPatch": "PATCH",
        "authorizedDelete": "DELETE",
    }
    for match in re.finditer(
        r"_(authorizedGet|authorizedPost|authorizedPatch|authorizedDelete)\(\s*['\"]([^'\"]+)",
        sage_api,
    ):
        endpoints.add((verbs[match.group(1)], _normalize(match.group(2))))

    for match in re.finditer(
        r"_authorized\(\s*'(GET|POST)'\s*,\s*'([^']+)",
        identity,
    ):
        endpoints.add((match.group(1), _normalize(match.group(2))))

    # These requests build their Uri directly rather than using the helpers above.
    endpoints.update(
        {
            ("GET", "/notifications"),
            ("GET", "/world/knowledge"),
            ("POST", "/tools/execute"),
            ("GET", "/identity/config"),
            ("POST", "/identity/dev-login"),
            ("POST", "/identity/google"),
        }
    )
    return endpoints


def _backend_endpoints() -> set[tuple[str, str]]:
    endpoints: set[tuple[str, str]] = set()
    for path in ROUTE_FILES:
        source = path.read_text(encoding="utf-8")
        prefix_match = re.search(
            r"APIRouter\([^)]*prefix\s*=\s*['\"]([^'\"]+)",
            source,
            re.DOTALL,
        )
        prefix = prefix_match.group(1) if prefix_match else ""
        for match in re.finditer(
            r"@(?:app|router)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)",
            source,
        ):
            method = match.group(1).upper()
            route = _normalize(prefix + match.group(2))
            endpoints.add((method, route))
    return endpoints


def test_flutter_api_endpoints_exist_in_fastapi():
    missing = sorted(_client_endpoints() - _backend_endpoints())
    assert not missing, f"Flutter API paths have no matching FastAPI route: {missing}"
