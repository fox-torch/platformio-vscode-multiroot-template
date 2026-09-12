from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_CONTAINER = "projects"
DISCOVERY_EXCLUDED = {".git", ".pio", "archive", "templates", "node_modules"}
COPY_EXCLUDED_DIRS = {
    ".git", ".pio", ".pioenvs", ".piolibdeps", ".vscode", ".idea",
    "__pycache__", "node_modules",
}
COPY_EXCLUDED_FILES = {".DS_Store", "Thumbs.db", "compile_commands.json"}
GENERATED_VSCODE_FILES = ("c_cpp_properties.json", "launch.json", "extensions.json")


def find_pio() -> str:
    found = shutil.which("pio") or shutil.which("platformio")
    if found:
        return found
    candidates = [
        Path.home() / ".platformio/penv/Scripts/pio.exe",
        Path.home() / ".platformio/penv/bin/pio",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise RuntimeError("PlatformIO Core was not found. Install PlatformIO IDE first.")


def run_command(command: list[str]) -> int:
    print("> " + " ".join(command), flush=True)
    return subprocess.run(command).returncode


def require_project(path: Path) -> Path:
    project = path.expanduser().resolve()
    if not (project / "platformio.ini").is_file():
        raise RuntimeError(f"platformio.ini was not found: {project}")
    return project


def remove_generated_metadata(project: Path) -> None:
    cache = project / ".pio"
    if cache.exists():
        print(f"Removing generated cache: {cache}", flush=True)
        shutil.rmtree(cache)
    compile_db = project / "compile_commands.json"
    compile_db.unlink(missing_ok=True)
    vscode = project / ".vscode"
    for name in GENERATED_VSCODE_FILES:
        (vscode / name).unlink(missing_ok=True)
    if vscode.exists() and not any(vscode.iterdir()):
        vscode.rmdir()


def repair_project(project: Path) -> int:
    project = require_project(project)
    pio = find_pio()
    remove_generated_metadata(project)
    print(f"Restoring dependencies and building: {project}", flush=True)
    if run_command([pio, "run", "--project-dir", str(project)]) != 0:
        print("Build failed. Check platformio.ini, lib_deps, and source code.", file=sys.stderr)
        return 1

    print("Regenerating VS Code metadata...", flush=True)
    command = [pio, "project", "init", "--project-dir", str(project), "--ide", "vscode"]
    if run_command(command) != 0:
        print("Build succeeded, but VS Code metadata regeneration failed.", file=sys.stderr)
        return 2
    print(f"Repair complete: {project}", flush=True)
    return 0


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_destination_parent(repo: Path, parent: Path) -> Path:
    parent = parent.expanduser().resolve()
    container = (repo / PROJECT_CONTAINER).resolve()
    if parent != container and not is_under(parent, container):
        raise RuntimeError("Destination must be under projects/.")
    parent.mkdir(parents=True, exist_ok=True)
    return parent


def copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in COPY_EXCLUDED_DIRS or name in COPY_EXCLUDED_FILES:
            ignored.add(name)
        elif name.endswith((".code-workspace", ".pyc", ".log", ".tmp", ".bak")):
            ignored.add(name)
    return ignored


def choose_destination(parent: Path, name: str) -> Path:
    candidate = parent / name
    suffix = 2
    while candidate.exists():
        candidate = parent / f"{name}-{suffix}"
        suffix += 1
    return candidate


def import_project(repo: Path, source: Path, destination_parent: Path) -> int:
    source = require_project(source)
    destination_parent = validate_destination_parent(repo, destination_parent)
    destination = choose_destination(destination_parent, source.name)

    staging_root = repo / ".pio" / "maintenance" / "import-staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    stage_dir = Path(tempfile.mkdtemp(prefix="import-", dir=staging_root))
    staged_project = stage_dir / source.name
    try:
        print(f"Staging copy: {source} -> {staged_project}", flush=True)
        shutil.copytree(source, staged_project, ignore=copy_ignore)
        require_project(staged_project)
        print(f"Activating imported project: {destination}", flush=True)
        shutil.move(str(staged_project), str(destination))
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)

    print("Local/generated files were excluded from the copy.", flush=True)
    result = repair_project(destination)
    if result == 0:
        print(f"Import complete: {destination}", flush=True)
    else:
        print(
            f"Import copy is preserved for troubleshooting: {destination}",
            file=sys.stderr,
        )
    return result


def discover_projects(repo: Path) -> list[Path]:
    projects: set[Path] = set()
    root = repo / PROJECT_CONTAINER
    if not root.is_dir():
        return []
    for config in root.rglob("platformio.ini"):
        relative = config.relative_to(repo)
        if any(part in DISCOVERY_EXCLUDED for part in relative.parts):
            continue
        projects.add(config.parent.resolve())
    return sorted(projects, key=lambda path: path.as_posix().lower())


def list_projects(repo: Path) -> int:
    for project in discover_projects(repo):
        print(project.relative_to(repo).as_posix())
    return 0


def repair_all(repo: Path) -> int:
    failed: list[Path] = []
    projects = discover_projects(repo)
    if not projects:
        print("No PlatformIO projects found.")
        return 0
    for project in projects:
        print(f"\n=== Repair: {project.relative_to(repo)} ===", flush=True)
        if repair_project(project) != 0:
            failed.append(project)
    if failed:
        print("\nRepair failed:", file=sys.stderr)
        for project in failed:
            print(f"- {project.relative_to(repo)}", file=sys.stderr)
        return 1
    print("\nAll PlatformIO projects repaired successfully.", flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PlatformIO multi-project maintenance tools")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    sub = parser.add_subparsers(dest="action", required=True)
    repair = sub.add_parser("repair", help="Repair one PlatformIO project")
    repair.add_argument("project", type=Path)
    sub.add_parser("repair-all", help="Repair every PlatformIO project")
    sub.add_parser("list", help="List PlatformIO projects")
    importer = sub.add_parser("import", help="Import an external PlatformIO project")
    importer.add_argument("source", type=Path)
    importer.add_argument("destination_parent", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo_root.expanduser().resolve()
    try:
        if args.action == "repair":
            return repair_project(args.project)
        if args.action == "repair-all":
            return repair_all(repo)
        if args.action == "list":
            return list_projects(repo)
        if args.action == "import":
            return import_project(repo, args.source, args.destination_parent)
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
