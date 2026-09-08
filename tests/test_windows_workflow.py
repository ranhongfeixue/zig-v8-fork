from pathlib import Path
import re
import subprocess
import tempfile
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
    def test_prepare_v8_disables_depot_tools_auto_update(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            cache_root = root / "lp-cache"
            depot_tools = cache_root / "depot_tools-14.9.207.35"
            depot_tools.mkdir(parents=True)
            (depot_tools / ".bootstrap-complete").touch()

            gclient = depot_tools / "gclient"
            gclient.write_text(
                """#!/bin/sh
if [ "${DEPOT_TOOLS_UPDATE:-}" != "0" ]; then
    echo "depot_tools auto update was not disabled" >&2
    exit 23
fi
""",
                encoding="utf-8",
            )
            gclient.chmod(0o755)

            python = depot_tools / "python-bin" / "python3"
            python.parent.mkdir()
            python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            python.chmod(0o755)

            result = subprocess.run(
                [
                    "zig",
                    "build",
                    "prepare-v8",
                    "-Dtarget=x86_64-windows-msvc",
                    f"-Dcache_root={cache_root}",
                    "--cache-dir",
                    str(root / "zig-cache"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                result.returncode,
                0,
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )

    def test_shell_file_writes_preserve_windows_backslashes(self) -> None:
        contents = '{"status":"opt-out"}\n'
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = (
                Path(temporary_directory)
                / r"D:\a\zig-v8-fork\.lp-cache\build_telemetry.cfg"
            )

            subprocess.run(
                [
                    "sh",
                    "-c",
                    "printf '%s' \"$1\" > \"$2\"",
                    "write-file",
                    contents,
                    destination,
                ],
                check=True,
            )

            self.assertEqual(destination.read_text(encoding="utf-8"), contents)

        build_script = (ROOT / "build.zig").read_text(encoding="utf-8")
        self.assertIn("fn addWriteFileCommand(", build_script)
        self.assertEqual(build_script.count("addWriteFileCommand("), 4)
        self.assertNotIn('b.fmt("echo ', build_script)

    def test_depot_tools_copy_materializes_symlink_launchers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "depot_tools"
            destination = root / "copied_depot_tools"
            source.mkdir()
            (source / "tool.py").write_text("launcher contents\n", encoding="utf-8")
            (source / "tool").symlink_to("tool.py")

            subprocess.run(
                ["cp", "-rL", source, destination],
                check=True,
            )

            copied_launcher = destination / "tool"
            self.assertFalse(copied_launcher.is_symlink())
            self.assertEqual(
                copied_launcher.read_text(encoding="utf-8"),
                "launcher contents\n",
            )

        build_script = (ROOT / "build.zig").read_text(encoding="utf-8")
        self.assertIn('b.addSystemCommand(&.{ "cp", "-rL" })', build_script)

    def test_reusable_workflow_inherits_each_callers_permissions(self) -> None:
        reusable = load_workflow("_prebuild-v8.yml")
        windows = load_workflow("build-windows.yml")
        release = load_workflow("build-release.yml")

        self.assertNotIn("permissions", reusable)
        self.assertEqual(windows["permissions"], {"contents": "read"})
        self.assertEqual(release["permissions"], {"contents": "write"})

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

    def test_windows_archive_listing_preserves_llvm_lib_option_in_git_bash(self) -> None:
        workflow = load_workflow("_prebuild-v8.yml")
        steps = workflow["jobs"]["build"]["steps"]
        package = next(step for step in steps if step.get("name") == "Find v8 library")

        self.assertRegex(
            package["run"],
            re.compile(r"(?m)^\s*MSYS2_ARG_CONV_EXCL=/list\s+llvm-lib\.exe\s+/list\b"),
            "Git Bash must not rewrite llvm-lib's /list option as a filesystem path",
        )

    def test_windows_host_runs_depot_tools_batch_launchers_through_cmd(self) -> None:
        build_script = (ROOT / "build.zig").read_text(encoding="utf-8")

        self.assertIn('@import("builtin")', build_script)
        self.assertIn('"cmd.exe", "/d", "/c"', build_script)
        self.assertIn('"{s}/{s}.bat"', build_script)
        self.assertIn('"{s}/bootstrap/win_tools.bat"', build_script)


if __name__ == "__main__":
    unittest.main()
