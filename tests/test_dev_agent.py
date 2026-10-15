from pathlib import Path

import pytest

from dev_agent.policy import AgentPolicy


def test_policy_allows_source_and_tests(tmp_path: Path):
    policy = AgentPolicy(tmp_path)
    assert policy.can_read("brain/router.py")
    assert policy.can_write("dev_agent/example.py")
    assert policy.can_write("tests/test_example.py")


def test_policy_blocks_secrets_and_git_for_read_and_write(tmp_path: Path):
    policy = AgentPolicy(tmp_path)
    for path in (".env", "config/.env", ".git/config", "credentials.json"):
        assert not policy.can_read(path)
        assert not policy.can_write(path)
        with pytest.raises(PermissionError):
            policy.assert_read_allowed(path)
        with pytest.raises(PermissionError):
            policy.assert_write_allowed(path)


def test_policy_blocks_remote_and_destructive_commands(tmp_path: Path):
    policy = AgentPolicy(tmp_path)
    blocked = (
        "git push origin main",
        "git reset --hard HEAD",
        "git clean -fd",
        "git checkout main",
        "python -c print(1)",
        "python -m pip install requests",
    )
    for command in blocked:
        with pytest.raises(PermissionError):
            policy.validate_check_command(command)


def test_policy_allows_read_only_git_and_compile_checks(tmp_path: Path):
    policy = AgentPolicy(tmp_path)
    assert policy.validate_check_command("git status --short")
    assert policy.validate_check_command("git diff -- app")
    assert policy.validate_check_command("git log -1")
    assert policy.validate_check_command("python -m py_compile dev_agent/policy.py")
    assert policy.validate_check_command("pytest tests/test_dev_agent.py")
