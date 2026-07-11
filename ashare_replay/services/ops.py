from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from typing import Any

from ashare_replay.config import PROJECT_ROOT


def _run_command(command: list[str], timeout: int = 15) -> dict[str, Any]:
    try:
        result = subprocess.run(  # noqa: S603 - command list is fixed by internal callers.
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip()[:1000],
            "stderr": result.stderr.strip()[:1000],
        }
    except Exception as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def docker_environment_check(run_compose_config: bool = True) -> dict[str, Any]:
    docker_path = shutil.which("docker")
    result: dict[str, Any] = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "project_root": str(PROJECT_ROOT),
        "docker": {
            "installed": docker_path is not None,
            "path": docker_path,
            "version": None,
            "daemon_running": False,
        },
        "compose": {
            "available": False,
            "version": None,
            "config_valid": False,
            "config_message": "未检查",
        },
        "can_run_compose": False,
        "next_actions": [],
    }
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        result["next_actions"].append("缺少 docker-compose.yml。")
        return result
    if docker_path is None:
        result["next_actions"].append("请先安装并启动 Docker Desktop。")
        result["compose"]["config_message"] = "未安装 Docker，无法检查 Compose。"
        return result

    version = _run_command(["docker", "--version"])
    result["docker"]["version"] = version["stdout"] or version["stderr"]
    info = _run_command(["docker", "info"], timeout=10)
    result["docker"]["daemon_running"] = info["ok"]
    if not info["ok"]:
        result["next_actions"].append("Docker 已安装但服务未运行，请打开 Docker Desktop。")

    compose_version = _run_command(["docker", "compose", "version"])
    result["compose"]["available"] = compose_version["ok"]
    result["compose"]["version"] = compose_version["stdout"] or compose_version["stderr"]
    if not compose_version["ok"]:
        result["next_actions"].append("当前 Docker 缺少 Compose 插件，请升级 Docker Desktop。")

    if run_compose_config and compose_version["ok"]:
        compose_config = _run_command(["docker", "compose", "config"], timeout=20)
        result["compose"]["config_valid"] = compose_config["ok"]
        result["compose"]["config_message"] = compose_config["stdout"] or compose_config["stderr"]
        if not compose_config["ok"]:
            result["next_actions"].append("docker-compose.yml 未通过配置检查。")
    elif not run_compose_config:
        result["compose"]["config_message"] = "按参数跳过 Compose 配置检查。"

    result["can_run_compose"] = bool(
        result["docker"]["installed"]
        and result["docker"]["daemon_running"]
        and result["compose"]["available"]
        and (result["compose"]["config_valid"] or not run_compose_config)
    )
    if result["can_run_compose"]:
        result["next_actions"].append("Docker 环境可用，可以运行 start_windows.bat 或 sh start.sh。")
    return result


def format_ops_check_text(result: dict[str, Any]) -> str:
    docker = result["docker"]
    compose = result["compose"]
    lines = [
        "Docker 环境检查结果",
        f"- Docker 是否安装：{'是' if docker['installed'] else '否'}",
        f"- Docker 服务是否运行：{'是' if docker['daemon_running'] else '否'}",
        f"- Compose 是否可用：{'是' if compose['available'] else '否'}",
        f"- Compose 配置是否有效：{'是' if compose['config_valid'] else '否'}",
        f"- 是否可以启动容器链路：{'是' if result['can_run_compose'] else '否'}",
    ]
    if result["next_actions"]:
        lines.append("下一步：")
        lines.extend(f"- {item}" for item in result["next_actions"])
    return "\n".join(lines)
