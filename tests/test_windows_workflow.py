from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def load_workflow(name: str) -> dict:
    path = WORKFLOWS / name
    if not path.is_file():
        raise AssertionError(f"missing workflow: {path.relative_to(ROOT)}")
    with path.open(encoding="utf-8") as workflow_file:
        document = yaml.load(workflow_file, Loader=yaml.BaseLoader)
    if not isinstance(document, dict):
        raise AssertionError(f"workflow is not a mapping: {path.relative_to(ROOT)}")
    return document


class WindowsWorkflowTests(unittest.TestCase):
    def test_windows_branch_builds_on_a_windows_runner(self) -> None:
        workflow = load_workflow("build-windows.yml")

        self.assertEqual(
            workflow["on"]["push"]["branches"],
            ["zig-v8-fork/windows-msvc"],
        )
        self.assertIn("workflow_dispatch", workflow["on"])
        self.assertEqual(workflow["permissions"], {"contents": "read"})

        job = workflow["jobs"]["build-x86_64-windows"]
        self.assertEqual(job["uses"], "./.github/workflows/_prebuild-v8.yml")
        self.assertEqual(job["with"]["runner"], "windows-2022")
        self.assertEqual(job["with"]["target"], "x86_64-windows-msvc")
        self.assertEqual(job["with"]["build_type"], "release")

    def test_reusable_build_uploads_a_windows_archive(self) -> None:
        workflow = load_workflow("_prebuild-v8.yml")
        steps = workflow["jobs"]["build"]["steps"]

        setup_zig = next(
            step for step in steps
            if step.get("uses", "").startswith("mlugg/setup-zig@")
        )
        self.assertEqual(setup_zig["with"]["version"], "0.16.0")

        package = next(step for step in steps if step.get("name") == "Find v8 library")
        script = package["run"]
        self.assertIn("c_v8.lib", script)
        self.assertIn("libc_v8_", script)
        self.assertIn(".a", script)

        uploads = [
            step for step in steps
            if step.get("uses", "").startswith("actions/upload-artifact@")
        ]
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0]["with"]["path"], "libc_v8_*.a")
        self.assertNotIn("if", uploads[0])

    def test_windows_host_runs_depot_tools_batch_launchers_through_cmd(self) -> None:
        build_script = (ROOT / "build.zig").read_text(encoding="utf-8")

        self.assertIn('@import("builtin")', build_script)
        self.assertIn('"cmd.exe", "/d", "/c"', build_script)
        self.assertIn('"{s}/{s}.bat"', build_script)


if __name__ == "__main__":
    unittest.main()
