from __future__ import annotations

from ashare_replay.services.ops import docker_environment_check


def test_docker_check_reports_missing_docker(monkeypatch):
    monkeypatch.setenv("PATH", "")
    result = docker_environment_check(run_compose_config=False)
    assert result["docker"]["installed"] is False
    assert result["can_run_compose"] is False
    assert result["next_actions"]
