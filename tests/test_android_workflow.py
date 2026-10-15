from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "sage-one-android-apk.yml"


def test_android_release_workflow_has_endpoint_override_and_release_outputs():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "pull_request:" in text
    assert "api_url:" in text
    assert "SAGE_ANDROID_API_URL" in text
    assert 'dart-define=SAGE_API_URL="$SAGE_ANDROID_API_URL"' in text
    assert "http://127.0.0.1:8010" in text
    assert "timeout-minutes: 30" in text
    assert "concurrency:" in text
    assert "cache: true" in text
    assert "parsed.hostname" in text
    assert "Credentials must not be embedded" in text
    assert "usesCleartextTraffic" in text
    assert "local HTTP API access" in text
    assert "flutter analyze" in text
    assert "flutter test" in text
    assert "flutter build apk --release" in text
    assert "flutter build appbundle --release" in text
    assert "app-release.apk" in text
    assert "app-release.aab" in text
    assert "retention-days: 14" in text
