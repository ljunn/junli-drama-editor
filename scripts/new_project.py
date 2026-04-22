#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""初始化微短剧项目结构。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def safe_project_dirname(project_name: str) -> str:
    return re.sub(r"[\\/]+", "-", project_name).strip() or "短剧项目"


def backup_existing_file(path: Path) -> Path:
    backup_path = path.with_suffix(path.suffix + ".bak")
    counter = 1
    while backup_path.exists():
        backup_path = path.with_suffix(path.suffix + f".bak{counter}")
        counter += 1
    backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path


def write_project_file(path: Path, content: str, *, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return
    if path.exists() and overwrite:
        backup_existing_file(path)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def stringify(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return default


def as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def load_seed(seed_file: str | None) -> dict[str, Any]:
    if not seed_file:
        return {}

    path = Path(seed_file).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"seed 文件不存在：{path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"seed 文件不是合法 JSON：{path}") from exc

    if not isinstance(data, dict):
        raise ValueError("seed 文件根节点必须是 JSON object。")
    return data


def render_markdown_table(headers: list[str], rows: list[dict[str, Any]]) -> list[str]:
    header_line = "| " + " | ".join(headers) + " |"
    divider_line = "| " + " | ".join("-" * len(header) for header in headers) + " |"
    rendered_rows = [header_line, divider_line]
    for row in rows:
        rendered_rows.append("| " + " | ".join(stringify(row.get(header, "")) for header in headers) + " |")
    return rendered_rows


def build_task_log(project_name: str) -> str:
    return f"""# 创作进度日志

## 当前状态
- 剧名：{project_name}
- 创作阶段：筹备中
- 最新完成集：无
- 当前处理集：无
- 下一集目标：无
- 最近交付文件：无

## 最近三集摘要
- 暂无

## 活跃伏笔
| 伏笔 | 状态 |
|------|------|
| 暂无 | 未记录 |
"""


def build_history_template() -> str:
    return """# 剧集历史

| 集数 | 标题 | 状态 | 核心事件 | 摘要 |
|------|------|------|----------|------|
"""


def build_hooks_template() -> str:
    return """# 伏笔列表

## 活跃伏笔
| 伏笔名称 | 当前状态 | 首次出现 | 备注 |
|----------|----------|----------|------|

## 已回收伏笔
| 伏笔名称 | 回收集数 | 备注 |
|----------|----------|------|
"""


def build_series_bible(project_name: str, seed: dict[str, Any]) -> str:
    female_lead = as_mapping(seed.get("female_lead"))
    series_visual_style = as_mapping(seed.get("series_visual_style"))
    hook_types = as_mapping(seed.get("hook_types"))
    lines = [
        "# 剧集基本信息",
        "",
        f"剧名：{stringify(seed.get('title'), project_name) or project_name}",
        f"类型：{stringify(seed.get('genre'))}",
        f"总集数：{stringify(seed.get('total_episodes'))}",
        f"单集时长：{stringify(seed.get('episode_duration'))}",
        f"目标平台：{stringify(seed.get('target_platform'))}",
        f"目标受众：{stringify(seed.get('target_audience'))}",
        "",
        "# 世界观",
        "",
        f"故事背景：{stringify(seed.get('story_background'))}",
        f"核心设定：{stringify(seed.get('core_setting'))}",
        f"主线冲突：{stringify(seed.get('main_conflict'))}",
        f"主角进入主线的切口：{stringify(seed.get('entry_point'), stringify(female_lead.get('主线任务')))}",
        "",
        "# 核心爽点类型",
        "",
        f"- 打脸：{stringify(hook_types.get('打脸'))}",
        f"- 逆袭：{stringify(hook_types.get('逆袭'))}",
        f"- 马甲掉落：{stringify(hook_types.get('马甲掉落'))}",
        f"- 情感反转：{stringify(hook_types.get('情感反转'))}",
        "",
        "# 视觉风格",
        "",
        f"- 主色调：{stringify(series_visual_style.get('主色调'))}",
        f"- 常用镜头：{stringify(series_visual_style.get('常用镜头'))}",
        f"- 高光场景：{stringify(series_visual_style.get('高光场景'))}",
    ]
    return "\n".join(lines)


def build_character_section(title: str, data: dict[str, Any], include_catchphrase: bool) -> list[str]:
    lines = [
        f"## {title}",
        "",
        f"- 姓名：{stringify(data.get('姓名'))}",
        f"- 年龄：{stringify(data.get('年龄'))}",
        f"- 固定外貌：{stringify(data.get('固定外貌'))}",
        f"- 服装系统：{stringify(data.get('服装系统'))}",
        f"- 性格：{stringify(data.get('性格'))}",
    ]
    if include_catchphrase:
        lines.append(f"- 口头禅：{stringify(data.get('口头禅'))}")
    lines.extend(
        [
            f"- 表面身份：{stringify(data.get('表面身份'))}",
            f"- 隐藏身份：{stringify(data.get('隐藏身份'))}",
            f"- 技能 / 金手指：{stringify(data.get('技能 / 金手指'))}",
            f"- 情感线：{stringify(data.get('情感线'))}",
            f"- 主线任务：{stringify(data.get('主线任务'))}",
        ]
    )
    return lines


def build_character_design(seed: dict[str, Any]) -> str:
    female_lead = as_mapping(seed.get("female_lead"))
    male_lead = as_mapping(seed.get("male_lead"))
    rows = [row for row in as_list(seed.get("knowledge_table")) if isinstance(row, dict)]
    if not rows:
        rows = [{"角色": "", "是否知晓核心秘密": "", "当前已知信息": "", "当前服装/造型": ""}]

    lines = [
        "# 核心角色",
        "",
        *build_character_section("女主", female_lead, include_catchphrase=True),
        "",
        *build_character_section("男主", male_lead, include_catchphrase=False),
        "",
        "## 反派 / 关键配角",
        "",
        stringify(seed.get("supporting_roles_note"), "按同样结构补齐。"),
        "",
        "## 角色知情状态表",
        "",
        *render_markdown_table(
            ["角色", "是否知晓核心秘密", "当前已知信息", "当前服装/造型"],
            rows,
        ),
    ]
    return "\n".join(lines)


def build_visual_bible(seed: dict[str, Any]) -> str:
    visual_rules = as_mapping(seed.get("visual_rules"))
    color_rules = as_mapping(visual_rules.get("色彩系统"))
    scene_rules = as_mapping(visual_rules.get("场景设计"))
    lens_rules = as_mapping(visual_rules.get("镜头语言"))
    light_rules = as_mapping(visual_rules.get("光影系统"))
    lines = [
        "# 色彩系统",
        "",
        f"- 红色：{stringify(color_rules.get('红色'))}",
        f"- 黑色：{stringify(color_rules.get('黑色'))}",
        f"- 金色：{stringify(color_rules.get('金色'))}",
        f"- 白色：{stringify(color_rules.get('白色'))}",
        "",
        "# 场景设计",
        "",
        f"- 主战场：{stringify(scene_rules.get('主战场'))}",
        f"- 豪门场景：{stringify(scene_rules.get('豪门场景'))}",
        f"- 亲密场景：{stringify(scene_rules.get('亲密场景'))}",
        f"- 打脸场景：{stringify(scene_rules.get('打脸场景'))}",
        "",
        "# 镜头语言",
        "",
        f"- 打脸时刻：{stringify(lens_rules.get('打脸时刻'))}",
        f"- 秘密揭露：{stringify(lens_rules.get('秘密揭露'))}",
        f"- 男主出场：{stringify(lens_rules.get('男主出场'))}",
        f"- 女主反杀：{stringify(lens_rules.get('女主反杀'))}",
        "",
        "# 光影系统",
        "",
        f"- 正面情绪：{stringify(light_rules.get('正面情绪'))}",
        f"- 阴谋场景：{stringify(light_rules.get('阴谋场景'))}",
        f"- 对峙时刻：{stringify(light_rules.get('对峙时刻'))}",
    ]
    return "\n".join(lines)


def build_narrative_style(seed: dict[str, Any]) -> str:
    narrative_rules = as_mapping(seed.get("narrative_rules"))
    dialogue_style = as_mapping(seed.get("dialogue_style"))
    emotion_physicalization = as_mapping(seed.get("emotion_physicalization"))
    forbidden_items = as_mapping(seed.get("forbidden_items"))
    lines = [
        "# 每集必达",
        "",
        f"- 爽点数量：{stringify(narrative_rules.get('爽点数量'))}",
        f"- 节奏要求：{stringify(narrative_rules.get('节奏要求'))}",
        f"- 开场要求：{stringify(narrative_rules.get('开场要求'))}",
        f"- 结尾卡点要求：{stringify(narrative_rules.get('结尾卡点要求'))}",
        "",
        "# 对白风格",
        "",
        f"- 句长：{stringify(dialogue_style.get('句长'))}",
        f"- 情绪：{stringify(dialogue_style.get('情绪'))}",
        f"- 禁用口癖：{stringify(dialogue_style.get('禁用口癖'))}",
        f"- 爽金句：{stringify(dialogue_style.get('爽金句'))}",
        "",
        "# 情感物理化",
        "",
        f"- ❌ 禁止：{stringify(emotion_physicalization.get('❌ 禁止'))}",
        f"- ✅ 改写方式：{stringify(emotion_physicalization.get('✅ 改写方式'))}",
        "",
        "# 禁止事项",
        "",
        f"- 角色 OOC：{stringify(forbidden_items.get('角色 OOC'))}",
        f"- 提前揭露秘密：{stringify(forbidden_items.get('提前揭露秘密'))}",
        f"- 无意义水词：{stringify(forbidden_items.get('无意义水词'))}",
        f"- 大段心理描写：{stringify(forbidden_items.get('大段心理描写'))}",
    ]
    return "\n".join(lines)


def build_outline(seed: dict[str, Any]) -> str:
    outline_entries = []
    for item in as_list(seed.get("outline")):
        if isinstance(item, str):
            outline_entries.append(item.strip())
            continue
        if not isinstance(item, dict):
            continue
        episode = stringify(item.get("episode") or item.get("集数"))
        title = stringify(item.get("title") or item.get("标题"))
        core_event = stringify(item.get("core_event") or item.get("核心事件"))
        if episode:
            outline_entries.append(f"{episode}:{title}-{core_event}".rstrip("-"))

    if not outline_entries:
        outline_entries = [f"{index}:标题-核心事件" for index in range(1, 11)]
    return "\n".join(outline_entries)


def build_role_state(seed: dict[str, Any]) -> str:
    current_states = as_mapping(seed.get("current_states"))
    knowledge_rows = [row for row in as_list(seed.get("state_knowledge")) if isinstance(row, dict)]
    wardrobe = as_mapping(seed.get("wardrobe"))
    if not knowledge_rows:
        knowledge_rows = [{"角色": "", "知道什么": "", "绝对不知道什么": "", "备注": ""}]

    lines = [
        "# 角色状态",
        "",
        "## 当前集后状态",
        "",
        f"- 女主：{stringify(current_states.get('女主'))}",
        f"- 男主：{stringify(current_states.get('男主'))}",
        f"- 反派 1：{stringify(current_states.get('反派 1'))}",
        f"- 反派 2：{stringify(current_states.get('反派 2'))}",
        "",
        "## 知情状态表",
        "",
        *render_markdown_table(["角色", "知道什么", "绝对不知道什么", "备注"], knowledge_rows),
        "",
        "## 当前服装与造型",
        "",
        f"- 女主：{stringify(wardrobe.get('女主'))}",
        f"- 男主：{stringify(wardrobe.get('男主'))}",
        f"- 反派 1：{stringify(wardrobe.get('反派 1'))}",
        f"- 反派 2：{stringify(wardrobe.get('反派 2'))}",
    ]
    return "\n".join(lines)


def build_drama_overview(project_name: str, seed: dict[str, Any]) -> str:
    overview = as_mapping(seed.get("overview"))
    return f"""# 短剧概况

- 剧名：{stringify(seed.get('title'), project_name) or project_name}
- 类型：{stringify(seed.get('genre'))}
- 总集数：{stringify(seed.get('total_episodes'))}
- 单集时长：{stringify(seed.get('episode_duration'))}
- 目标平台：{stringify(seed.get('target_platform'))}
- 目标受众：{stringify(seed.get('target_audience'))}
- 付费卡点：{stringify(overview.get('付费卡点'))}
- 故事看点：{stringify(overview.get('故事看点'))}

## 300 字梗概

{stringify(overview.get('300字梗概'), '待补充。')}
"""


def build_story_outline(seed: dict[str, Any]) -> str:
    story_outline = as_mapping(seed.get("story_outline"))
    return f"""# 故事大纲

## 背景

{stringify(story_outline.get('背景'), '待补充。')}

## 切入点

{stringify(story_outline.get('切入点'), '待补充。')}

## 铺垫

{stringify(story_outline.get('铺垫'), '待补充。')}

## 高潮

{stringify(story_outline.get('高潮'), '待补充。')}

## 结尾与后续钩子

{stringify(story_outline.get('结尾与后续钩子'), '待补充。')}
"""


def build_character_bios(seed: dict[str, Any]) -> str:
    female_lead = as_mapping(seed.get("female_lead"))
    male_lead = as_mapping(seed.get("male_lead"))
    return f"""# 人物小传

## {stringify(female_lead.get('姓名'), '角色 1')}

- 基础信息：{stringify(female_lead.get('表面身份'))}
- 外观造型：{stringify(female_lead.get('固定外貌'))}
- 性格特质：{stringify(female_lead.get('性格'))}
- 身份设定：{stringify(female_lead.get('隐藏身份'))}
- 技能 / 金手指：{stringify(female_lead.get('技能 / 金手指'))}
- 情感线：{stringify(female_lead.get('情感线'))}
- 剧情主线：{stringify(female_lead.get('主线任务'))}

## {stringify(male_lead.get('姓名'), '角色 2')}

- 基础信息：{stringify(male_lead.get('表面身份'))}
- 外观造型：{stringify(male_lead.get('固定外貌'))}
- 性格特质：{stringify(male_lead.get('性格'))}
- 身份设定：{stringify(male_lead.get('隐藏身份'))}
- 技能 / 金手指：{stringify(male_lead.get('技能 / 金手指'))}
- 情感线：{stringify(male_lead.get('情感线'))}
- 剧情主线：{stringify(male_lead.get('主线任务'))}
"""


def build_episode_synopsis(seed: dict[str, Any]) -> str:
    items = [item for item in as_list(seed.get("episode_synopsis")) if isinstance(item, dict)]
    if not items:
        return """# 分集梗概

## 第 1 集

- 起因：
- 经过：
- 结果 / 卡点：
"""

    lines = ["# 分集梗概", ""]
    for item in items:
        episode = stringify(item.get("episode") or item.get("集数"))
        if not episode:
            continue
        lines.extend(
            [
                f"## 第 {episode} 集",
                "",
                f"- 起因：{stringify(item.get('起因'))}",
                f"- 经过：{stringify(item.get('经过'))}",
                f"- 结果 / 卡点：{stringify(item.get('结果 / 卡点'))}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def create_drama_project(
    project_name: str,
    output_dir: Path,
    seed_data: dict[str, Any] | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    seed = seed_data or {}
    project_dir = output_dir / safe_project_dirname(project_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    for directory in ("docs", "episodes", "runtime", "state"):
        (project_dir / directory).mkdir(parents=True, exist_ok=True)

    write_project_file(project_dir / "series-bible.md", build_series_bible(project_name, seed), overwrite=overwrite)
    write_project_file(project_dir / "character-design.md", build_character_design(seed), overwrite=overwrite)
    write_project_file(project_dir / "visual-bible.md", build_visual_bible(seed), overwrite=overwrite)
    write_project_file(project_dir / "narrative-style.md", build_narrative_style(seed), overwrite=overwrite)
    write_project_file(project_dir / "linenew.md", build_outline(seed), overwrite=overwrite)
    write_project_file(project_dir / "state" / "角色状态.md", build_role_state(seed), overwrite=overwrite)
    write_project_file(project_dir / "state" / "伏笔列表.md", build_hooks_template(), overwrite=overwrite)
    write_project_file(project_dir / "state" / "剧集历史.md", build_history_template(), overwrite=overwrite)
    write_project_file(project_dir / "task_log.md", build_task_log(project_name), overwrite=overwrite)

    write_project_file(project_dir / "docs" / "短剧概况.md", build_drama_overview(project_name, seed), overwrite=overwrite)
    write_project_file(project_dir / "docs" / "故事大纲.md", build_story_outline(seed), overwrite=overwrite)
    write_project_file(project_dir / "docs" / "人物小传.md", build_character_bios(seed), overwrite=overwrite)
    write_project_file(project_dir / "docs" / "分集梗概.md", build_episode_synopsis(seed), overwrite=overwrite)

    return project_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化微短剧项目结构")
    parser.add_argument("project_name", help="项目名")
    parser.add_argument(
        "--path",
        default=".",
        help="输出目录，默认当前目录",
    )
    parser.add_argument(
        "--seed-file",
        help="可选 JSON 文件；若提供，则按最小可写标准预填核心配置、状态和第 1 集信息。",
    )
    parser.add_argument("--force", action="store_true", help="覆盖已有同名项目中的标准文件，并先写入 .bak 备份。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seed_data = load_seed(args.seed_file)
    project_dir = create_drama_project(
        args.project_name,
        Path(args.path).resolve(),
        seed_data=seed_data,
        overwrite=args.force,
    )
    print(project_dir)


if __name__ == "__main__":
    main()
