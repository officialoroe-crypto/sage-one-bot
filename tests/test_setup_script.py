import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("sage_setup", Path(__file__).resolve().parent.parent / "scripts" / "sage_setup.py")
sage_setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sage_setup)


def test_env_roundtrip_skips_blank_values_and_keeps_others(tmp_path, monkeypatch):
    monkeypatch.setattr(sage_setup, "ENV_FILE", tmp_path / ".env")
    sage_setup.write_env({"GROQ_API_KEY": "abc", "GEMINI_API_KEY": "", "SAGE_ENV": "development"})
    assert sage_setup.read_env() == {"GROQ_API_KEY": "abc", "SAGE_ENV": "development"}


def test_report_fails_without_any_key_and_passes_with_one(monkeypatch):
    for var in ("GEMINI_API_KEY", "GROQ_API_KEY", "CEREBRAS_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    assert sage_setup.report({}, live=False) == 1
    assert sage_setup.report({"GROQ_API_KEY": "x"}, live=False) == 0
