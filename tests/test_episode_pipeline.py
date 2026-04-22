from __future__ import annotations

import json
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

    def init_seeded_project(self, tmp: str, name: str) -> Path:
        project_dir = Path(tmp) / name
        init_result = self.run_cli(
            PIPELINE,
            "init-project",
            name,
            "--path",
            tmp,
            "--seed-file",
            EXAMPLE_SEED,
        )
        self.assertEqual(init_result.returncode, 0, self.combined_output(init_result))
        return project_dir

    def build_valid_script(self, *, include_knowledge_risk: bool = False) -> str:
        risky_line = (
            '顾清漪:"遗嘱和旧案证据都在你手里，你还想装到什么时候。"' if include_knowledge_risk else '顾清漪:"你今晚一定会露底，我等着看你怎么收场。"' 
        )
        lines = [
            "场景1: 顾家宴会厅(0-20秒)",
            "【环境空镜2s】宾客围住珠宝展台，快门和议论声一起压上来。",
            "(主体)顾晚昭冷白皮、黑长直、白衬衫黑西裙，站在裂开的手镯前。",
            "(环境)长桌反光，礼服人群半围成弧，顾家主位空着却更有压迫感。",
            "(动作)顾晚昭扣住手镯裂口，把顾清漪递来的鉴定单压回台面，逼她当众把锅扛回去。",
            "(光影)冷白顶灯压在她眉骨上，珠面反出一道硬光。",
            "(镜头)先给手镯裂口特写，再切顾晚昭抬眼反打全场。",
            "(画质)4K，珠面高光清晰，人物边缘锐利。",
            "台词:",
            '顾清漪:"是你碰坏的。"',
            '顾晚昭:"我只碰真货，不碰你做的局。"',
            '裴砚川:"继续，让她把话说完。"',
            "场景2: 顾家走廊(20-40秒)",
            "【环境空镜2s】走廊尽头的监控灯一闪，佣人脚步声被厚地毯吞掉。",
            "(主体)裴砚川深灰西装、黑袖扣，立在走廊拐角，视线一直压着顾晚昭。",
            "(环境)玻璃墙映出两人的半身影，走廊尽头只剩一条冷白灯带。",
            "(动作)裴砚川借黑色袖扣的反光挡住镜头死角，顾晚昭顺势把遗嘱备份的假线索塞进他掌心又立刻抽走。",
            "(光影)侧光把两人的脸切成明暗两半，气压更紧。",
            "(镜头)先给袖扣特写，再切双人压脸近景，最后跟一个手部交换动作。",
            "(画质)4K，金属反光和袖口纹理都清楚。",
            "台词:",
            '裴砚川:"你回顾家，不像只为修东西。"',
            '顾晚昭:"你盯着我，也不像只为看戏。"',
            '裴砚川:"遗嘱备份真在你手里吗？"',
            "场景3: 珠宝修复室(40-60秒)",
            "【环境空镜2s】冷柜和工具台并排亮起，修复灯把空气切得很硬。",
            "(主体)顾晚昭摘下手套，露出稳到近乎冷漠的手势，顾曼琳站在门口没有进来。",
            "(环境)金属托盘、修复针和碎钻盒排成一线，谁碰过都一目了然。",
            "(动作)顾晚昭当面指出手镯断口是二次切割，顾曼琳想压住话头，反被她把监控时间点钉死在今晚家宴前。",
            "(光影)修复灯直照断口，顾曼琳半张脸沉进暗处。",
            "(镜头)先切断口微距，再切顾晚昭平视顾曼琳的稳镜头。",
            "(画质)4K，金属纹理和指尖动作清晰可辨。",
            "台词:",
            '顾曼琳:"你一个修复师，说话别越界。"',
            '顾晚昭:"断口是旧刀，新伤是今晚补的，越界的是你的人。"',
            '顾曼琳:"你最好别把这间屋子当成你的法庭。"',
            "场景4: 顾家露台(60-80秒)",
            "【环境空镜2s】夜风掀动窗帘，露台外的城市灯海像一层冷金噪点。",
            "(主体)顾清漪亮片银裙、锋利猫眼妆，堵在露台出口，顾晚昭背后是半开的玻璃门。",
            "(环境)栏杆外是高空，脚边散着刚被踩皱的宴会邀请卡，玻璃门上映着宴会厅里不断靠近的人影。",
            "(动作)顾清漪想逼顾晚昭当场认输，顾晚昭故意让她再往前一步，裴砚川在门内抬手截住保镖，让局势停在最危险的一秒，也把所有退路一起压死。",
            "(光影)逆光勾出顾清漪裙摆的硬边，顾晚昭正脸被门内冷光托起来。",
            "(镜头)先给顾清漪逼近的压脸近景，再切顾晚昭不退的正反打，最后收在裴砚川抬手止人的中近景。",
            "(画质)4K，裙面亮片和玻璃冷反射都锐利。",
            "台词:",
            risky_line,
            '顾晚昭:"你敢再往前半步，我就让全场知道谁在做假。"',
            '裴砚川:"门别关，今晚谁都别想替顾家收场。"',
        ]
        return "\n".join(lines) + "\n"

    def build_valid_shot(self, *, seconds: str = "0-5秒", extra_dialogue: str | None = None) -> str:
        lines = [
            f"镜头1: 顾家宴会厅({seconds})",
            "(主体)顾晚昭白衬衫黑西裙，视线钉死在裂开的手镯上。",
            "(环境)宴会厅灯光压在珠宝展台上，宾客影子在她背后晃动。",
            "(动作)顾晚昭抬眼锁住顾清漪，右手按住手镯裂口不让她抽走。",
            "(光影)冷白顶灯压出她眉骨的硬边，裂口反出一道冷光。",
            "(镜头)固定近景起，轻推到她按住裂口的手部。",
            "(画质)4K，金属纹理和人物边缘清晰。",
            "台词:",
            '顾晚昭:"你急着甩锅，不如先解释谁碰过它。"',
        ]
        if extra_dialogue:
            lines.append(extra_dialogue)
        return "\n".join(lines) + "\n"

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
            project_dir = self.init_seeded_project(tmp, "链路项目")

            plan_result = self.run_cli(PIPELINE, "plan", project_dir, "--episode-num", "1")
            self.assertEqual(plan_result.returncode, 0, self.combined_output(plan_result))

            compose_result = self.run_cli(PIPELINE, "compose-scenes", project_dir, "--episode-num", "1")
            self.assertEqual(compose_result.returncode, 0, self.combined_output(compose_result))
            prompt_path = project_dir / "runtime" / "episode-0001" / "scene-01" / "scene.prompt.md"
            self.assertTrue(prompt_path.exists())
            prompt_text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("## Few-shot 对照", prompt_text)
            self.assertIn("## 抓人规则", prompt_text)
            self.assertIn("软卡点 vs 狠卡点", prompt_text)
            self.assertIn("当前场至少回应 1 个旧悬念", prompt_text)

    def test_screenplay_format_reference_separates_scene_and_shot_modes(self) -> None:
        reference_text = (REPO_ROOT / "references" / "screenplay-format.md").read_text(encoding="utf-8")
        self.assertIn("## 2. 5秒单镜头格式", reference_text)
        self.assertIn("镜头1: 订婚宴后台(0-5秒)", reference_text)
        self.assertNotIn("(镜头)5s眼部特写，切二人中景", reference_text)

    def test_compose_shots_prompt_enforces_single_5_second_shot_skeleton(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.init_seeded_project(tmp, "单镜头提示项目")

            plan_result = self.run_cli(PIPELINE, "plan", project_dir, "--episode-num", "1")
            self.assertEqual(plan_result.returncode, 0, self.combined_output(plan_result))

            scene_path = project_dir / "runtime" / "episode-0001" / "scene-01" / "scene.md"
            scene_path.parent.mkdir(parents=True, exist_ok=True)
            scene_path.write_text(
                "\n".join(
                    [
                        "## 当前场摘要",
                        "- 地点：顾家宴会厅",
                        "- 人物：顾晚昭、顾清漪、裴砚川",
                        "- 入场状态：顾晚昭刚发现手镯事故是局。",
                        "- 当前场目标：当众反压顾清漪。",
                        "- 当前场冲突：顾清漪想把责任压到女主头上。",
                        "- 出场变化：男主开始确认女主手里另有筹码。",
                        "",
                        "## 5秒镜头单元表",
                        "| 镜头 | 秒数 | 画面目标 | 人物/动作 | 台词/口型 | 承上启下 |",
                        "|------|------|----------|-----------|-----------|----------|",
                        "| 1 | 0-5秒 | 女主锁定做局人 | 顾晚昭抬眼盯住顾清漪，手指按住裂口 | 无台词 | 压到镜头2继续反打 |",
                        "| 2 | 5-10秒 | 继妹先声夺人 | 顾清漪前压半步，抢先甩锅 | 顾清漪:\\\"是你碰坏的。\\\" | 把压力交给镜头3 |",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            compose_result = self.run_cli(
                PIPELINE,
                "compose-shots",
                project_dir,
                "--episode-num",
                "1",
                "--scene-num",
                "1",
                "--shot-num",
                "1",
            )
            self.assertEqual(compose_result.returncode, 0, self.combined_output(compose_result))

            prompt_path = project_dir / "runtime" / "episode-0001" / "scene-01" / "shot-001.prompt.md"
            self.assertTrue(prompt_path.exists())
            prompt_text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("只输出 `镜头1:` 这一镜头", prompt_text)
            self.assertIn("镜头1: 顾家宴会厅(0-5秒)", prompt_text)
            self.assertIn("场景1: 地点(0-45秒)", prompt_text)
            self.assertIn("下面这种输出是错的，禁止出现", prompt_text)

    def test_quality_checklist_mentions_single_shot_mode(self) -> None:
        checklist_text = (REPO_ROOT / "references" / "quality-checklist.md").read_text(encoding="utf-8")
        self.assertIn("## 单镜头检查", checklist_text)
        self.assertIn("不要拿 `review` 的场景块规则去检查 `shot-001.md`", checklist_text)

    def test_workflow_catalog_defaults_to_directory_delivery(self) -> None:
        result = self.run_cli(PIPELINE, "workflows")
        self.assertEqual(result.returncode, 0, self.combined_output(result))
        self.assertIn("步骤: compose-scenes -> compose-shots", result.stdout)
        self.assertNotIn("步骤: compose-scenes -> compose-shots -> stitch-scenes", result.stdout)

    def test_check_shot_accepts_valid_single_shot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shot_path = Path(tmp) / "shot-001.md"
            shot_path.write_text(self.build_valid_shot(), encoding="utf-8")

            result = self.run_cli(PIPELINE, "check-shot", shot_path)
            self.assertEqual(result.returncode, 0, self.combined_output(result))
            self.assertIn("单镜头数：1", result.stdout)

    def test_check_shot_rejects_scene_block_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shot_path = Path(tmp) / "not-a-shot.md"
            shot_path.write_text(self.build_valid_script(), encoding="utf-8")

            result = self.run_cli(PIPELINE, "check-shot", shot_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("检测到 `场景X:` 场景块", result.stdout)

    def test_check_shot_rejects_non_5_second_or_multi_dialogue_shot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shot_path = Path(tmp) / "bad-shot.md"
            shot_path.write_text(
                self.build_valid_shot(
                    seconds="0-8秒",
                    extra_dialogue='顾清漪:"你拿不出证据。"',
                ),
                encoding="utf-8",
            )

            result = self.run_cli(PIPELINE, "review-shot", shot_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("不是严格 5 秒镜头", result.stdout)
            self.assertIn("有效对白超过 1 句", result.stdout)

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
            project_dir = self.init_seeded_project(tmp, "回写项目")

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
            project_dir = self.init_seeded_project(tmp, "续写项目")

            plan_result = self.run_cli(PIPELINE, "plan", project_dir, "--episode-num", "2")
            self.assertNotEqual(plan_result.returncode, 0)
            self.assertIn("未找到第1集剧本文件", plan_result.stdout)
            self.assertIn("state/剧集历史.md 还没有第1集记录", plan_result.stdout)

    def test_finish_blocks_structurally_valid_but_thin_script_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.init_seeded_project(tmp, "质量门项目")

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

    def test_consistency_check_flags_knowledge_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.init_seeded_project(tmp, "一致性项目")

            script_path = Path(tmp) / "knowledge-risk.md"
            script_path.write_text(self.build_valid_script(include_knowledge_risk=True), encoding="utf-8")

            result = self.run_cli(
                PIPELINE,
                "consistency-check",
                project_dir,
                "--episode-num",
                "1",
                "--script-path",
                script_path,
            )
            self.assertEqual(result.returncode, 0, self.combined_output(result))
            self.assertIn("知情越权风险", result.stdout)
            self.assertIn("顾清漪", result.stdout)

    def test_finish_writes_state_diff_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.init_seeded_project(tmp, "状态差异项目")

            script_path = Path(tmp) / "episode-1.md"
            script_path.write_text(self.build_valid_script(), encoding="utf-8")

            finish_result = self.run_cli(
                PIPELINE,
                "finish",
                project_dir,
                "1",
                script_path,
                "--summary",
                "女主借手镯事故反压继妹，并把遗嘱线索抛到男主面前。",
            )
            self.assertEqual(finish_result.returncode, 0, self.combined_output(finish_result))

            state_diff_path = project_dir / "state" / "pending" / "episode-0001.state-diff.json"
            self.assertTrue(state_diff_path.exists())
            payload = json.loads(state_diff_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["episode_num"], 1)
            self.assertEqual(payload["proposed_updates"]["history_row"]["status"], "已完成")
            self.assertIn("speakers", payload["script_signals"])
            self.assertNotIn("----", payload["script_signals"]["active_hook_names"])
            self.assertIn("editable_updates", payload)
            self.assertIn("episode-0001.state-diff.json", finish_result.stdout)

    def test_apply_state_diff_updates_markdown_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = self.init_seeded_project(tmp, "应用差异项目")

            script_path = Path(tmp) / "episode-1.md"
            script_path.write_text(self.build_valid_script(), encoding="utf-8")

            finish_result = self.run_cli(
                PIPELINE,
                "finish",
                project_dir,
                "1",
                script_path,
                "--summary",
                "女主借手镯事故反压继妹，并把遗嘱线索抛到男主面前。",
            )
            self.assertEqual(finish_result.returncode, 0, self.combined_output(finish_result))

            state_diff_path = project_dir / "state" / "pending" / "episode-0001.state-diff.json"
            payload = json.loads(state_diff_path.read_text(encoding="utf-8"))
            payload["editable_updates"]["role_state"]["current_states"][1]["value"] = "已明确怀疑顾晚昭就是失踪长女，并准备继续试探。"
            payload["editable_updates"]["role_state"]["knowledge_rows"][1]["known"] = "顾家账目异常，手镯事故像有人做局，并怀疑女主握有遗嘱线索。"
            payload["editable_updates"]["hook_state"]["active_hooks"][0]["status"] = "已确认和女主当前行动直接绑定，男主开始主动试探。"
            payload["editable_updates"]["hook_state"]["resolved_hooks"].append(
                {"name": "手镯事故做局", "episode": "第1集", "note": "已在家宴上被女主当场拆穿。"}
            )
            state_diff_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            apply_result = self.run_cli(
                PIPELINE,
                "apply-state-diff",
                project_dir,
                "--episode-num",
                "1",
            )
            self.assertEqual(apply_result.returncode, 0, self.combined_output(apply_result))

            role_state_text = (project_dir / "state" / "角色状态.md").read_text(encoding="utf-8")
            hook_state_text = (project_dir / "state" / "伏笔列表.md").read_text(encoding="utf-8")
            self.assertIn("已明确怀疑顾晚昭就是失踪长女", role_state_text)
            self.assertIn("怀疑女主握有遗嘱线索", role_state_text)
            self.assertIn("手镯事故做局", hook_state_text)
            self.assertIn("已在家宴上被女主当场拆穿", hook_state_text)
            self.assertIn("已确认和女主当前行动直接绑定", hook_state_text)
            self.assertNotIn("根据已交付剧本确认角色知情", role_state_text)
            self.assertNotIn("根据已交付剧本确认伏笔新增", hook_state_text)
            self.assertTrue((project_dir / "state" / "角色状态.md.bak").exists())
            self.assertTrue((project_dir / "state" / "伏笔列表.md.bak").exists())


if __name__ == "__main__":
    unittest.main()
