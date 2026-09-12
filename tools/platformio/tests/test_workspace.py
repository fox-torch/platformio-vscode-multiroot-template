from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("workspace_bootstrap", TOOLS / "pio-workspace-bootstrap.py")
assert SPEC and SPEC.loader
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def make_project(root: Path, relative: str) -> Path:
    project = root / "projects" / relative
    project.mkdir(parents=True, exist_ok=True)
    (project / "platformio.ini").write_text("[env:test]\nplatform = native\n", encoding="utf-8")
    return project


class WorkspaceTests(unittest.TestCase):
    def test_group_names_and_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "platformio-workspace.json").write_text(json.dumps({
                "workspaceName": "demo",
                "groups": [{"path": "firmware", "label": "FW"}, {"path": "tests", "label": "TEST"}],
            }), encoding="utf-8")
            make_project(root, "firmware/main-controller")
            make_project(root, "tests/sensors/tof")
            make_project(root, "experiments/demo")
            config = bootstrap.load_config(root)
            projects = bootstrap.discover_projects(root)
            payload = bootstrap.workspace_payload(root, projects, config)
            names = [folder["name"] for folder in payload["folders"][1:]]
            self.assertEqual(names, ["PJ / experiments / demo", "FW / main-controller", "TEST / sensors / tof"])

    def test_generated_workspace_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "platformio-workspace.json").write_text(
                '{"workspaceName":"my-workspace","groups":[]}', encoding="utf-8"
            )
            make_project(root, "sample")
            workspace = bootstrap.run(root)
            self.assertEqual(workspace.name, "my-workspace.code-workspace")
            data = json.loads(workspace.read_text(encoding="utf-8"))
            self.assertEqual(data["folders"][1]["name"], "PJ / sample")
            self.assertTrue(data["settings"]["files.exclude"]["projects/sample"])

    def test_duplicate_display_names_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = make_project(root, "a/controller")
            second = make_project(root, "b/controller")
            config = {"workspaceName": "demo", "groups": [(bootstrap.PurePosixPath("a"), "X"), (bootstrap.PurePosixPath("b"), "X")]}
            with self.assertRaises(ValueError):
                bootstrap.workspace_payload(root, [first, second], config)

    def test_invalid_group_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "platformio-workspace.json").write_text(
                '{"groups":[{"path":"../outside","label":"BAD"}]}', encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                bootstrap.load_config(root)


if __name__ == "__main__":
    unittest.main()
