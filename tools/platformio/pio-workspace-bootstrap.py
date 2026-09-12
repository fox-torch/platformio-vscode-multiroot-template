from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

PROJECT_CONTAINER = "projects"
CONFIG_NAME = "platformio-workspace.json"
DEFAULT_WORKSPACE_NAME = "platformio-workspace"
EXCLUDED_PARTS = {".git", ".pio", "archive", "templates", "node_modules"}


def load_config(root: Path) -> dict:
    path = root / CONFIG_NAME
    raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    workspace_name = raw.get("workspaceName", DEFAULT_WORKSPACE_NAME)
    if not isinstance(workspace_name, str) or not workspace_name.strip():
        raise ValueError("workspaceName must be a non-empty string")
    if "/" in workspace_name or "\\" in workspace_name:
        raise ValueError("workspaceName must be a file name, not a path")

    groups: list[tuple[PurePosixPath, str]] = []
    for item in raw.get("groups", []):
        if not isinstance(item, dict):
            raise ValueError("Each groups entry must be an object")
        group_path = item.get("path")
        label = item.get("label")
        if not isinstance(group_path, str) or not group_path.strip():
            raise ValueError("groups.path must be a non-empty relative path")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("groups.label must be a non-empty string")
        normalized = PurePosixPath(group_path.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError(f"Invalid groups.path: {group_path}")
        groups.append((normalized, label.strip()))

    return {"workspaceName": workspace_name.strip(), "groups": groups}


def discover_projects(root: Path) -> list[Path]:
    search_root = root / PROJECT_CONTAINER
    if not search_root.is_dir():
        return []
    projects: set[Path] = set()
    for config in search_root.rglob("platformio.ini"):
        relative = config.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        projects.add(config.parent.resolve())
    return sorted(projects, key=lambda path: path.relative_to(root).as_posix().lower())


def display_name(root: Path, project: Path, groups: list[tuple[PurePosixPath, str]]) -> str:
    relative = PurePosixPath(project.relative_to(root / PROJECT_CONTAINER).as_posix())
    relative_parts = relative.parts
    for group_path, label in sorted(groups, key=lambda item: len(item[0].parts), reverse=True):
        group_parts = group_path.parts
        if relative_parts[: len(group_parts)] != group_parts:
            continue
        tail = relative_parts[len(group_parts) :]
        return " / ".join((label, *tail)) if tail else label
    return "PJ / " + " / ".join(relative_parts)


def workspace_payload(root: Path, projects: list[Path], config: dict) -> dict:
    names = {project: display_name(root, project, config["groups"]) for project in projects}
    if len(set(names.values())) != len(names):
        raise ValueError("Workspace display names are not unique. Adjust group labels in platformio-workspace.json.")

    excluded = {".pio": True}
    for project in projects:
        excluded[project.relative_to(root).as_posix()] = True

    folders = [{"path": str(root), "name": root.name}]
    folders.extend({"path": str(project), "name": names[project]} for project in projects)
    return {
        "folders": folders,
        "settings": {
            "platformio-ide.activateProjectOnTextEditorChange": True,
            "platformio-ide.autoOpenPlatformIOIniFile": False,
            "platformio-ide.autoRebuildAutocompleteIndex": True,
            "files.exclude": excluded,
        },
    }


def workspace_filename(config: dict) -> str:
    name = config["workspaceName"]
    return name if name.endswith(".code-workspace") else f"{name}.code-workspace"


def write_workspace(root: Path, projects: list[Path], config: dict) -> Path:
    out_dir = root / ".pio" / "workspace"
    out_dir.mkdir(parents=True, exist_ok=True)
    workspace = out_dir / workspace_filename(config)
    rendered = json.dumps(workspace_payload(root, projects, config), indent=2, ensure_ascii=False) + "\n"
    if workspace.exists() and workspace.read_text(encoding="utf-8") == rendered:
        return workspace
    temporary = workspace.with_suffix(".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(workspace)
    return workspace


def vscode_user_data_dir() -> Path | None:
    cache_path = os.environ.get("VSCODE_CODE_CACHE_PATH")
    if not cache_path:
        return None
    cache = Path(cache_path).resolve()
    if cache.parent.name != "CachedData":
        return None
    return cache.parent.parent


def spawn_workspace_switch(root: Path, workspace: Path) -> None:
    vscode_pid = os.environ.get("VSCODE_PID")
    if not vscode_pid:
        return
    out_dir = workspace.parent
    ipc_hook = os.environ.get("VSCODE_IPC_HOOK", "")
    session = hashlib.sha256(f"{vscode_pid}|{ipc_hook}".encode("utf-8")).hexdigest()[:16]
    marker = out_dir / f"switched-{session}"
    if marker.exists():
        return
    marker.write_text("started\n", encoding="ascii")

    helper = root / "tools" / "platformio" / "pio-workspace-switch.py"
    user_data = vscode_user_data_dir()
    command = [sys.executable, str(helper), str(workspace), str(root), str(marker)]
    if user_data is not None:
        command.append(str(user_data))
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(command, close_fds=True, **kwargs)


def run(root: Path) -> Path:
    root = root.resolve()
    config = load_config(root)
    projects = discover_projects(root)
    workspace = write_workspace(root, projects, config)
    spawn_workspace_switch(root, workspace)
    return workspace


def _project_root_from_platformio() -> Path | None:
    try:
        Import("env")  # type: ignore[name-defined]
    except NameError:
        return None
    return Path(env["PROJECT_DIR"])  # type: ignore[name-defined]


if __name__ == "__main__":
    selected_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    print(run(selected_root))
else:
    platformio_root = _project_root_from_platformio()
    if platformio_root is not None:
        run(platformio_root)
