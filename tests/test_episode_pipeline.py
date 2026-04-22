from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = REPO_ROOT / "scripts" / "episode_pipeline.py"
EXAMPLE_SEED = REPO_ROOT / "examples" / "minimum-seed.json"


class EpisodePipelineCliTests(unittest.TestCase):
    maxDiff = None

    def run_cli(self, *args: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *map(str, args)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

    def combined_output(self, result: subprocess.CompletedProcess[str]) -> str:
        return f"{result.stdout}\n{result.stderr}".strip()

    def test_init_with_seed_passes_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "种子项目"
            init_result = self.run_cli(
                PIPELINE,
                "init-project",
                "种子项目",
                "--path",
                tmp,
                "--seed-file",
                EXAMPLE_SEED,
            )
            self.assertEqual(init_result.returncode, 0, self.combined_output(init_result))

            preflight_result = self.run_cli(PIPELINE, "preflight", project_dir)
            self.assertEqual(preflight_result.returncode, 0, self.combined_output(preflight_result))
            self.assertIn("Preflight 通过", preflight_result.stdout)

    def test_plan_requires_preflight_ready_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "空壳项目"
            init_result = self.run_cli(PIPELINE, "init-project", "空壳项目", "--path", tmp)
            self.assertEqual(init_result.returncode, 0, self.combined_output(init_result))

            plan_result = self.run_cli(
                PIPELINE,
                "plan",
                project_dir,
                "--episode-num",
                "1",
                "--title",
                "测试标题",
                "--core-event",
                "测试核心事件",
            )
            self.assertNotEqual(plan_result.returncode, 0)
            self.assertIn("项目尚未通过 preflight", plan_result.stdout)
            self.assertFalse((project_dir / "runtime" / "episode-0001" / "plan.md").exists())

    def test_seeded_project_can_generate_scene_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "链路项目"
            init_result = self.run_cli(
                PIPELINE,
                "init-project",
                "链路项目",
                "--path",
                tmp,
                "--seed-file",
                EXAMPLE_SEED,
            )
            self.assertEqual(init_result.returncode, 0, self.combined_output(init_result))

            plan_result = self.run_cli(PIPELINE, "plan", project_dir, "--episode-num", "1")
            self.assertEqual(plan_result.returncode, 0, self.combined_output(plan_result))

            compose_result = self.run_cli(PIPELINE, "compose-scenes", project_dir, "--episode-num", "1")
            self.assertEqual(compose_result.returncode, 0, self.combined_output(compose_result))
            self.assertTrue((project_dir / "runtime" / "episode-0001" / "scene-01" / "scene.prompt.md").exists())

    def test_force_seed_can_upgrade_existing_skeleton(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "升级项目"
            init_result = self.run_cli(PIPELINE, "init-project", "升级项目", "--path", tmp)
            self.assertEqual(init_result.returncode, 0, self.combined_output(init_result))

            upgrade_result = self.run_cli(
                PIPELINE,
                "init-project",
                "升级项目",
                "--path",
                tmp,
                "--seed-file",
                EXAMPLE_SEED,
                "--force",
            )
            self.assertEqual(upgrade_result.returncode, 0, self.combined_output(upgrade_result))

            preflight_result = self.run_cli(PIPELINE, "preflight", project_dir)
            self.assertEqual(preflight_result.returncode, 0, self.combined_output(preflight_result))
            self.assertTrue((project_dir / "series-bible.md.bak").exists())

    def test_finish_refuses_to_write_back_invalid_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "回写项目"
            init_result = self.run_cli(
                PIPELINE,
                "init-project",
                "回写项目",
                "--path",
                tmp,
                "--seed-file",
                EXAMPLE_SEED,
            )
            self.assertEqual(init_result.returncode, 0, self.combined_output(init_result))

            bad_script = Path(tmp) / "bad-script.md"
            bad_script.write_text("这不是合法剧本格式。\n", encoding="utf-8")

            finish_result = self.run_cli(
                PIPELINE,
                "finish",
                project_dir,
                "1",
                bad_script,
                "--summary",
                "测试摘要",
            )
            self.assertNotEqual(finish_result.returncode, 0)
            self.assertIn("Finish 终止", finish_result.stdout)
            self.assertFalse((project_dir / "episodes" / "episode-0001.md").exists())


if __name__ == "__main__":
    unittest.main()
