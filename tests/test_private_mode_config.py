import importlib

import config.settings as settings_module


def test_development_defaults_to_private_owner_mode(monkeypatch):
    monkeypatch.delenv("SAGE_ENV", raising=False)
    monkeypatch.delenv("SAGE_PRIVATE_MODE", raising=False)
    monkeypatch.delenv("SAGE_DEV_MODE", raising=False)
    module = importlib.reload(settings_module)
    assert module.settings.ENVIRONMENT == "development"
    assert module.settings.PRIVATE_MODE is True
    assert module.settings.DEVELOPER_MODE is True


def test_production_does_not_inherit_private_owner_mode(monkeypatch):
    monkeypatch.setenv("SAGE_ENV", "production")
    monkeypatch.delenv("SAGE_PRIVATE_MODE", raising=False)
    monkeypatch.delenv("SAGE_DEV_MODE", raising=False)
    module = importlib.reload(settings_module)
    assert module.settings.PRIVATE_MODE is False
    assert module.settings.DEVELOPER_MODE is False

    monkeypatch.setenv("SAGE_ENV", "development")
    importlib.reload(settings_module)
