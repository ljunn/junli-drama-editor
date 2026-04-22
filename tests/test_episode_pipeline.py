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
            prompt_path = project_dir / "runtime" / "episode-0001" / "scene-01" / "scene.prompt.md"
            self.assertTrue(prompt_path.exists())
            prompt_text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("## Few-shot 对照", prompt_text)
            self.assertIn("软卡点 vs 狠卡点", prompt_text)

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

    def test_plan_blocks_episode_two_when_context_is_thin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "续写项目"
            init_result = self.run_cli(
                PIPELINE,
                "init-project",
                "续写项目",
                "--path",
                tmp,
                "--seed-file",
                EXAMPLE_SEED,
            )
            self.assertEqual(init_result.returncode, 0, self.combined_output(init_result))

            plan_result = self.run_cli(PIPELINE, "plan", project_dir, "--episode-num", "2")
            self.assertNotEqual(plan_result.returncode, 0)
            self.assertIn("未找到第1集剧本文件", plan_result.stdout)
            self.assertIn("state/剧集历史.md 还没有第1集记录", plan_result.stdout)

    def test_finish_blocks_structurally_valid_but_thin_script_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "质量门项目"
            init_result = self.run_cli(
                PIPELINE,
                "init-project",
                "质量门项目",
                "--path",
                tmp,
                "--seed-file",
                EXAMPLE_SEED,
            )
            self.assertEqual(init_result.returncode, 0, self.combined_output(init_result))

            thin_script = Path(tmp) / "thin-script.md"
            thin_script.write_text(
                "\n".join(
                    [
                        "场景1: 顾家宴会厅(0-20秒)",
                        "【环境空镜2s】宾客围观。",
                        "(主体)顾晚昭白衬衫黑西裙，站在手镯展台前。",
                        "(动作)她抬手按住裂开的手镯。",
                        "(光影)冷白灯压住她的脸。",
                        "(镜头)近景推进到手镯裂口。",
                        "(画质)4K。",
                        "台词:",
                        "顾晚昭:\"别碰。\"",
                        "场景2: 顾家走廊(20-40秒)",
                        "【环境空镜2s】走廊很静。",
                        "(主体)裴砚川深灰西装，停在拐角。",
                        "(动作)他拦住顾晚昭的去路。",
                        "(光影)侧光切脸。",
                        "(镜头)双人对切。",
                        "(画质)4K。",
                        "台词:",
                        "裴砚川:\"等等。\"",
                        "场景3: 监控死角(40-60秒)",
                        "【环境空镜2s】红点闪一下。",
                        "(主体)顾晚昭压低声音。",
                        "(动作)她把录音笔藏回袖口。",
                        "(光影)背景压暗。",
                        "(镜头)手部特写。",
                        "(画质)4K。",
                        "台词:",
                        "顾晚昭:\"你看错了。\"",
                        "场景4: 顾家露台(60-80秒)",
                        "【环境空镜2s】风吹窗帘。",
                        "(主体)顾清漪倚在栏杆旁。",
                        "(动作)她盯着顾晚昭冷笑。",
                        "(光影)逆光勾边。",
                        "(镜头)压脸近景。",
                        "(画质)4K。",
                        "台词:",
                        "顾清漪:\"你输了。\"",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            finish_result = self.run_cli(
                PIPELINE,
                "finish",
                project_dir,
                "1",
                thin_script,
                "--summary",
                "测试摘要",
            )
            self.assertNotEqual(finish_result.returncode, 0)
            self.assertIn("结构虽然过关", finish_result.stdout)
            self.assertIn("有效对白偏少", finish_result.stdout)
            self.assertFalse((project_dir / "episodes" / "episode-0001.md").exists())

            override_result = self.run_cli(
                PIPELINE,
                "finish",
                project_dir,
                "1",
                thin_script,
                "--summary",
                "测试摘要",
                "--allow-quality-warnings",
            )
            self.assertEqual(override_result.returncode, 0, self.combined_output(override_result))
            self.assertTrue((project_dir / "episodes" / "episode-0001.md").exists())


if __name__ == "__main__":
    unittest.main()
