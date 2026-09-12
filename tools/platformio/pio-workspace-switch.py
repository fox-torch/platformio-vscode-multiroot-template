from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def find_vscode_cli() -> str | None:
    found = shutil.which("code")
    if found:
        return found
    candidates: list[Path] = []
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(Path(local_app_data) / "Programs/Microsoft VS Code/bin/code.cmd")
    elif sys.platform == "darwin":
        candidates.extend([
            Path("/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"),
            Path.home() / "Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
        ])
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def append_log(log: Path, message: str) -> None:
    with log.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip() + "\n")


def run_cli(command: list[str], log: Path) -> int:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        append_log(log, f"ERROR {command!r}: {exc}")
        return 1
    append_log(log, f"RC={result.returncode} CMD={command!r}")
    if result.stdout.strip():
        append_log(log, f"STDOUT {result.stdout.strip()}")
    if result.stderr.strip():
        append_log(log, f"STDERR {result.stderr.strip()}")
    return result.returncode


def switch_workspace(workspace: Path, root: Path, marker: Path, user_data: Path | None) -> int:
    log = workspace.parent / "switch.log"
    cli = find_vscode_cli()
    if not cli:
        append_log(log, "VS Code CLI was not found; leaving the root folder open.")
        marker.unlink(missing_ok=True)
        return 1
    base = [cli]
    if user_data is not None:
        base.extend(["--user-data-dir", str(user_data)])
    time.sleep(2)
    for attempt in range(1, 4):
        focus_rc = run_cli(base + [str(root / "platformio.ini")], log)
        time.sleep(2)
        switch_rc = run_cli(base + ["--reuse-window", str(workspace)], log)
        if focus_rc == 0 and switch_rc == 0:
            marker.write_text("ok\n", encoding="ascii")
            return 0
        append_log(log, f"Retrying workspace switch after attempt {attempt}.")
        time.sleep(2)
    marker.unlink(missing_ok=True)
    return 1


def main() -> int:
    if len(sys.argv) not in (4, 5):
        return 2
    workspace = Path(sys.argv[1]).resolve()
    root = Path(sys.argv[2]).resolve()
    marker = Path(sys.argv[3]).resolve()
    user_data = Path(sys.argv[4]).resolve() if len(sys.argv) == 5 else None
    return switch_workspace(workspace, root, marker, user_data)


if __name__ == "__main__":
    raise SystemExit(main())
