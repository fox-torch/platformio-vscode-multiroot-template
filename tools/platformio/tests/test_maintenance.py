from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("maintenance", TOOLS / "maintenance.py")
assert SPEC and SPEC.loader
maintenance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(maintenance)


class MaintenanceTests(unittest.TestCase):
    def test_discover_projects_under_projects_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inside = root / "projects" / "tests" / "demo"
            inside.mkdir(parents=True)
            (inside / "platformio.ini").write_text("[env:test]\nplatform=native\n", encoding="utf-8")
            outside = root / "other"
            outside.mkdir()
            (outside / "platformio.ini").write_text("[env:test]\nplatform=native\n", encoding="utf-8")
            self.assertEqual(maintenance.discover_projects(root), [inside.resolve()])

    def test_destination_must_be_under_projects(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            allowed = root / "projects" / "imports"
            self.assertEqual(maintenance.validate_destination_parent(root, allowed), allowed.resolve())
            with self.assertRaises(RuntimeError):
                maintenance.validate_destination_parent(root, root / "outside")

    def test_copy_ignore_removes_generated_state(self) -> None:
        ignored = maintenance.copy_ignore("x", [
            ".git", ".pio", ".vscode", "compile_commands.json", "build.log", "src"
        ])
        self.assertEqual(
            ignored,
            {".git", ".pio", ".vscode", "compile_commands.json", "build.log"},
        )


if __name__ == "__main__":
    unittest.main()
