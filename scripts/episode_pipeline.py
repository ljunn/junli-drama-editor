#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微短剧项目统一入口。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    from new_project import create_drama_project
except ModuleNotFoundError:
    from scripts.new_project import create_drama_project


REQUIRED_CORE_FILES = (
    "series-bible.md",
    "character-design.md",
    "visual-bible.md",
    "narrative-style.md",
    "linenew.md",
)

REQUIRED_STATE_FILES = (
    "state/角色状态.md",
    "state/伏笔列表.md",
    "state/剧集历史.md",
    "task_log.md",
)

RULE_LAYER_CATALOG: list[dict[str, Any]] = [
    {
        "id": "core-config",
        "title": "5 个核心配置文件",
        "sources": list(REQUIRED_CORE_FILES),
        "summary": "定义题材、角色、视觉、叙事风格和分集梗概。",
    },
    {
        "id": "state-memory",
        "title": "状态记忆文件",
        "sources": list(REQUIRED_STATE_FILES),
        "summary": "约束角色知情状态、伏笔状态、已完成剧集和当前进度。",
    },
    {
        "id": "delivery-rules",
        "title": "交付格式规则",
        "sources": [
            "references/screenplay-format.md",
            "references/quality-checklist.md",
        ],
        "summary": "约束单集剧本格式、3000 字符限制、场景块结构和风险词。",
    },
]

WORKFLOW_LAYER_CATALOG: list[dict[str, Any]] = [
    {
        "id": "init-project",
        "title": "新建短剧项目",
        "steps": ["init-project", "init"],
        "summary": "一次性建立 5 个配置文件、状态目录和投稿文档。",
    },
    {
        "id": "next-episode",
        "title": "继续写下一集",
        "steps": ["preflight", "resume", "plan", "compose"],
        "summary": "进入新一集前的标准准备链。",
    },
    {
        "id": "review",
        "title": "单集结构化质检",
        "steps": ["check"],
        "summary": "检查字数、场景块、格式和小说化风险；不替代人工爽点/卡点复核。",
    },
    {
        "id": "compose-scenes",
        "title": "分场创作包",
        "steps": ["compose-scenes", "stitch-scenes"],
        "summary": "把整集拆成多个场景 Prompt Pack，适合低输出长度模型和 5 秒视频镜头工作流。",
    },
    {
        "id": "finish",
        "title": "完结回写",
        "steps": ["finish"],
        "summary": "回写最近完成集、剧集历史，并生成状态文件待确认回写提醒。",
    },
]

COMMAND_LAYER_CATALOG: list[dict[str, Any]] = [
    {"group": "Layer", "commands": ["rules", "workflows", "commands"]},
    {
        "group": "Workflow",
        "commands": ["init-project", "next-episode", "compose-scenes", "review", "finish"],
    },
    {
        "group": "Primitive",
        "commands": ["init", "preflight", "resume", "plan", "compose", "compose-scenes", "stitch-scenes", "check", "finish"],
    },
]

BANNED_RISK_WORDS = (
    "心想",
    "内心",
    "觉得",
    "感觉",
    "仿佛",
    "似乎",
    "氛围",
    "空气里",
    "意识到",
)

PLACEHOLDER_VALUES = (
    "",
    "待补充",
    "待补充。",
    "标题",
    "核心事件",
    "标题-核心事件",
    "角色 1",
    "角色 2",
    "待命名",
)

COMPLETED_STATUSES = {"已完成", "done", "完成"}
TEXT_SCRIPT_EXTENSIONS = (".md", ".txt")
MIN_EFFECTIVE_SCRIPT_CHARS = 1200
MIN_DIALOGUE_LINES_PER_SCENE = 3
MIN_DIALOGUE_LINES_TOTAL = 12

DIALOGUE_LINE_PATTERN = re.compile(
    r"(?m)^(?!场景\d+[:：])(?!台词[:：])(?![【(（\-#])[^:\n：]{1,20}[:：]\s*(?!$)"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def normalize_value(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def is_placeholder_value(value: str, extra_placeholders: tuple[str, ...] = ()) -> bool:
    normalized = normalize_value(value)
    if not normalized:
        return True
    placeholder_values = {normalize_value(item) for item in PLACEHOLDER_VALUES + extra_placeholders}
    return normalized in placeholder_values


def extract_labeled_value(text: str, label: str, default: str = "") -> str:
    match = re.search(rf"(?m)^(?:-\s*)?{re.escape(label)}[:：][ \t]*(.*)$", text)
    return match.group(1).strip() if match else default


def extract_section(text: str, header: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(header)}\n(.*?)(?=^## |\Z)", text)
    return match.group(1).strip() if match else ""


def count_filled_labeled_values(text: str) -> int:
    count = 0
    for line in text.splitlines():
        match = re.match(r"^\s*(?:-\s*)?[^#|\n][^:：\n]+[:：]\s*(.*)$", line)
        if match and not is_placeholder_value(match.group(1), ("暂无", "无", "未记录")):
            count += 1
    return count


def has_nonempty_table_rows(text: str) -> bool:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if next_line.startswith("|"):
            next_cells = [cell.strip() for cell in next_line.strip().strip("|").split("|")]
            if next_cells and all(set(cell) <= {"-"} for cell in next_cells if cell):
                continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        if cells and all(set(cell) <= {"-"} for cell in cells if cell):
            continue
        if all(is_placeholder_value(cell, ("暂无", "无", "未记录")) for cell in cells):
            continue
        if any(not is_placeholder_value(cell, ("暂无", "无", "未记录")) for cell in cells):
            return True
    return False


def ensure_project_dir(project_dir: Path) -> Path:
    resolved = project_dir.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"项目目录不存在：{resolved}")
    return resolved


def extract_task_field(text: str, label: str, default: str = "无") -> str:
    match = re.search(rf"(?m)^- {re.escape(label)}：(.*)$", text)
    return match.group(1).strip() if match else default


def replace_task_field(text: str, label: str, value: str) -> str:
    pattern = rf"(?m)^- {re.escape(label)}：.*$"
    replacement = f"- {label}：{value}"
    if re.search(pattern, text):
        return re.sub(pattern, replacement, text, count=1)
    return text.rstrip() + f"\n{replacement}\n"


def replace_section(text: str, header: str, body_lines: list[str]) -> str:
    body = "\n".join(body_lines).rstrip() + "\n"
    pattern = rf"(?ms)(^## {re.escape(header)}\n)(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    if match:
        return text[: match.start(2)] + body + text[match.end(2) :]
    return text.rstrip() + f"\n\n## {header}\n" + body


def find_missing_files(project_dir: Path) -> list[str]:
    missing = []
    for relative_path in REQUIRED_CORE_FILES + REQUIRED_STATE_FILES:
        if not (project_dir / relative_path).exists():
            missing.append(relative_path)
    return missing


def parse_outline_entry(line: str) -> tuple[int | None, str | None, str | None]:
    match = re.match(r"^\s*(?:第\s*)?(\d+)\s*(?:集)?\s*[:：]\s*(.+)$", line.strip())
    if not match:
        return None, None, None
    episode_num = int(match.group(1))
    content = match.group(2).strip()
    parts = re.split(r"\s*[—\-–]\s*", content, maxsplit=1)
    title = parts[0].strip() if parts else None
    core_event = parts[1].strip() if len(parts) > 1 else ""
    sanitized_title = None if is_placeholder_value(title) else title
    sanitized_event = None if is_placeholder_value(core_event) else core_event
    return episode_num, sanitized_title, sanitized_event


def collect_outline_entries(text: str) -> list[tuple[int, str | None, str | None]]:
    entries: list[tuple[int, str | None, str | None]] = []
    for line in text.splitlines():
        episode_num, title, core_event = parse_outline_entry(line)
        if episode_num is None:
            continue
        entries.append((episode_num, title, core_event))
    return entries


def collect_preflight_blockers(project_dir: Path) -> list[str]:
    blockers: list[str] = []

    series_text = read_text(project_dir / "series-bible.md")
    for label in ("剧名", "类型", "总集数", "单集时长", "主线冲突"):
        value = extract_labeled_value(series_text, label)
        if is_placeholder_value(value):
            blockers.append(f"series-bible.md 未补齐 `{label}`。")

    character_text = read_text(project_dir / "character-design.md")
    for section_name in ("女主", "男主"):
        section_text = extract_section(character_text, section_name)
        if not section_text:
            blockers.append(f"character-design.md 缺少 `## {section_name}` 小节。")
            continue
        for label in ("姓名", "固定外貌", "表面身份"):
            value = extract_labeled_value(section_text, label)
            if is_placeholder_value(value):
                blockers.append(f"character-design.md 的 `{section_name}/{label}` 未补齐。")

    visual_text = read_text(project_dir / "visual-bible.md")
    if count_filled_labeled_values(visual_text) < 4:
        blockers.append("visual-bible.md 至少补齐 4 项明确的视觉/镜头/光影规则。")

    narrative_text = read_text(project_dir / "narrative-style.md")
    for label in ("爽点数量", "开场要求", "结尾卡点要求"):
        value = extract_labeled_value(narrative_text, label)
        if is_placeholder_value(value):
            blockers.append(f"narrative-style.md 未补齐 `{label}`。")

    outline_entries = collect_outline_entries(read_text(project_dir / "linenew.md"))
    valid_outline_entries = [entry for entry in outline_entries if entry[1] and entry[2]]
    if not valid_outline_entries:
        blockers.append("linenew.md 仍是模板占位，至少补 1 条真实的 `标题-核心事件` 分集线。")

    role_state_text = read_text(project_dir / "state" / "角色状态.md")
    current_state_section = extract_section(role_state_text, "当前集后状态")
    knowledge_section = extract_section(role_state_text, "知情状态表")
    if count_filled_labeled_values(current_state_section) < 2 and not has_nonempty_table_rows(knowledge_section):
        blockers.append("state/角色状态.md 还没有可用的角色状态或知情表。")

    return blockers


def collect_preflight_warnings(project_dir: Path) -> list[str]:
    warnings: list[str] = []

    hook_text = read_text(project_dir / "state" / "伏笔列表.md")
    if not has_nonempty_table_rows(extract_section(hook_text, "活跃伏笔")):
        warnings.append("state/伏笔列表.md 暂无活跃伏笔记录。首轮创作后建议尽快补齐。")

    history_rows = parse_history_rows(read_text(project_dir / "state" / "剧集历史.md"))
    if not any(row["status"] in COMPLETED_STATUSES for row in history_rows):
        warnings.append("state/剧集历史.md 还没有已完成剧集记录。")

    synopsis_text = read_text(project_dir / "docs" / "分集梗概.md")
    if synopsis_text and "待补充" in synopsis_text:
        warnings.append("docs/分集梗概.md 仍有占位内容，投稿资料阶段记得补齐。")

    return warnings


def parse_episode_outline_line(line: str, episode_num: int) -> tuple[str | None, str | None]:
    parsed_episode_num, title, core_event = parse_outline_entry(line)
    if parsed_episode_num != episode_num:
        return None, None
    return title, core_event


def lookup_episode_outline(project_dir: Path, episode_num: int) -> tuple[str | None, str | None]:
    outline_text = read_text(project_dir / "linenew.md")
    for line in outline_text.splitlines():
        title, core_event = parse_episode_outline_line(line, episode_num)
        if title:
            return title, core_event
    return None, None


def parse_history_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        if "集数" in line or set(line.replace("|", "").replace("-", "").strip()) == set():
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        rows.append(
            {
                "episode": cells[0],
                "title": cells[1],
                "status": cells[2],
                "core_event": cells[3],
                "summary": cells[4],
            }
        )
    return rows


def history_sort_key(row: dict[str, str]) -> int:
    try:
        return int(row["episode"])
    except (KeyError, ValueError):
        return 0


def recent_completed_rows(history_rows: list[dict[str, str]], before_episode: int | None = None, limit: int = 3) -> list[dict[str, str]]:
    completed = [row for row in history_rows if row["status"] in COMPLETED_STATUSES]
    if before_episode is not None:
        completed = [row for row in completed if history_sort_key(row) < before_episode]
    completed.sort(key=history_sort_key)
    return completed[-limit:]


def find_history_row(history_rows: list[dict[str, str]], episode_num: int) -> dict[str, str] | None:
    for row in history_rows:
        if history_sort_key(row) == episode_num:
            return row
    return None


def plan_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    return project_dir / "runtime" / f"episode-{episode_num:04d}.plan.md"


def prompt_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    return project_dir / "runtime" / f"episode-{episode_num:04d}.prompt.md"


def scene_prompt_path_for_episode(project_dir: Path, episode_num: int, scene_num: int) -> Path:
    return project_dir / "runtime" / f"episode-{episode_num:04d}.scene-{scene_num:02d}.prompt.md"


def stitched_scene_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    return project_dir / "runtime" / f"episode-{episode_num:04d}.assembled.md"


def canonical_episode_script_path(project_dir: Path, episode_num: int) -> Path:
    return project_dir / "episodes" / f"episode-{episode_num:04d}.md"


def episode_script_candidates(base_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for extension in TEXT_SCRIPT_EXTENSIONS:
        candidates.extend(sorted(base_dir.rglob(f"*{extension}")))
    return candidates


def episode_file_matches(path: Path, episode_num: int) -> bool:
    name = path.stem
    patterns = (
        rf"第\s*{episode_num}\s*集",
        rf"(?:^|[^0-9]){episode_num:04d}(?:[^0-9]|$)",
        rf"(?:^|[^0-9]){episode_num:03d}(?:[^0-9]|$)",
        rf"(?:^|[^0-9]){episode_num:02d}(?:[^0-9]|$)",
        rf"(?:^|[^0-9]){episode_num}(?:[^0-9]|$)",
    )
    return any(re.search(pattern, name) for pattern in patterns)


def find_episode_script(project_dir: Path, episode_num: int) -> Path | None:
    candidates: list[Path] = []
    for directory in ("episodes", "runtime"):
        base_dir = project_dir / directory
        if not base_dir.exists():
            continue
        for path in episode_script_candidates(base_dir):
            if path.name.endswith(".plan.md") or path.name.endswith(".prompt.md"):
                continue
            if episode_file_matches(path, episode_num):
                candidates.append(path)
    return candidates[0] if candidates else None


def persist_episode_script(project_dir: Path, episode_num: int, source_path: Path) -> Path:
    destination = canonical_episode_script_path(project_dir, episode_num)
    destination.parent.mkdir(parents=True, exist_ok=True)
    script_text = read_text(source_path).rstrip()
    destination.write_text((script_text + "\n") if script_text else "", encoding="utf-8")
    return destination


def parse_scene_plan_rows(plan_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    table_started = False
    for line in plan_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("| 场景 |"):
            table_started = True
            continue
        if not table_started:
            continue
        if stripped.startswith("|------"):
            continue
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 5 or not cells[0].isdigit():
            continue
        rows.append(
            {
                "scene": cells[0],
                "target_seconds": cells[1],
                "entry_state": cells[2],
                "escalation": cells[3],
                "payoff": cells[4],
            }
        )
    return rows


def estimate_video_unit_count(duration_text: str, shot_seconds: int) -> int:
    numbers = [int(item) for item in re.findall(r"\d+", duration_text)]
    if not numbers:
        return 8
    max_seconds = max(numbers)
    return max(1, (max_seconds + shot_seconds - 1) // shot_seconds)


def find_scene_output_files(project_dir: Path, episode_num: int) -> list[tuple[int, Path]]:
    runtime_dir = project_dir / "runtime"
    if not runtime_dir.exists():
        return []

    scene_files: dict[int, Path] = {}
    pattern = re.compile(rf"^episode-{episode_num:04d}\.scene-(\d+)(?:\.[^.]+)?\.(md|txt)$")
    for path in episode_script_candidates(runtime_dir):
        if path.name.endswith(".prompt.md"):
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        scene_num = int(match.group(1))
        if scene_num not in scene_files:
            scene_files[scene_num] = path
    return sorted(scene_files.items(), key=lambda item: item[0])


def tail_excerpt(text: str, max_chars: int = 1800) -> str:
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    return "...\n" + stripped[-max_chars:]


def extract_episode_synopsis(project_dir: Path, episode_num: int) -> str:
    synopsis_text = read_text(project_dir / "docs" / "分集梗概.md")
    match = re.search(rf"(?ms)^## 第\s*{episode_num}\s*集\s*\n(.*?)(?=^## |\Z)", synopsis_text)
    if not match:
        return ""
    section = match.group(1).strip()
    return "" if count_filled_labeled_values(section) == 0 else section


def update_task_log_status(project_dir: Path, episode_num: int, title: str, stage: str) -> None:
    task_log_path = project_dir / "task_log.md"
    task_log = read_text(task_log_path)
    if not task_log:
        return
    task_log = replace_task_field(task_log, "创作阶段", stage)
    task_log = replace_task_field(task_log, "当前处理集", f"第{episode_num}集《{title}》")
    task_log_path.write_text(task_log, encoding="utf-8")


def prepend_section_note(text: str, header: str, note: str, max_items: int = 5) -> str:
    existing = extract_section(text, header)
    lines = [line.strip() for line in existing.splitlines() if line.strip()]
    filtered = [line for line in lines if line != note]
    return replace_section(text, header, [note, *filtered[: max_items - 1]])


def collect_episode_context_issues(
    project_dir: Path,
    episode_num: int,
    title: str,
    core_event: str,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if is_placeholder_value(title):
        blockers.append("当前集标题为空，请在 linenew.md 或 `--title` 中补齐。")
    if is_placeholder_value(core_event):
        blockers.append("当前集核心事件为空，请在 linenew.md 或 `--core-event` 中补齐。")

    plan_path = plan_path_for_episode(project_dir, episode_num)
    if not plan_path.exists():
        blockers.append(f"未找到场景卡：{plan_path.relative_to(project_dir)}。请先运行 `plan`。")

    history_rows = parse_history_rows(read_text(project_dir / "state" / "剧集历史.md"))
    previous_row = find_history_row(history_rows, episode_num - 1) if episode_num > 1 else None
    if episode_num > 1 and not previous_row:
        blockers.append(f"state/剧集历史.md 还没有第{episode_num - 1}集记录，无法稳定续写第{episode_num}集。")
    if previous_row and previous_row["status"] not in COMPLETED_STATUSES:
        blockers.append(f"第{episode_num - 1}集尚未标记为已完成，先别直接续写第{episode_num}集。")
    if episode_num > 1 and not find_episode_script(project_dir, episode_num - 1):
        warnings.append(f"未找到第{episode_num - 1}集剧本文件，将只使用历史摘要衔接。")

    if not extract_episode_synopsis(project_dir, episode_num):
        warnings.append(f"docs/分集梗概.md 中未找到第{episode_num}集有效小节，将只使用 linenew.md 核心事件。")

    return blockers, warnings


def render_catalog(title: str, catalog: list[dict[str, Any]]) -> None:
    print(title)
    for item in catalog:
        if "group" in item:
            print(f"\n[{item['group']}]")
            for command in item["commands"]:
                print(f"- {command}")
            continue
        display_title = item.get("title", item["id"])
        print(f"\n- {item['id']}: {display_title}")
        sources = item.get("sources")
        if sources:
            print(f"  来源: {', '.join(sources)}")
        steps = item.get("steps")
        if steps:
            print(f"  步骤: {' -> '.join(steps)}")
        print(f"  说明: {item['summary']}")


def command_init(args: argparse.Namespace) -> int:
    project_dir = create_drama_project(args.project_name, Path(args.path).resolve())
    print(project_dir)
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    missing = find_missing_files(project_dir)
    blockers = collect_preflight_blockers(project_dir) if not missing else []
    warnings = collect_preflight_warnings(project_dir) if not missing else []
    if missing:
        print("Preflight 失败，缺少以下文件：")
        for item in missing:
            print(f"- {item}")
        return 1
    if blockers:
        print("Preflight 失败，以下内容仍是空壳或模板占位：")
        for item in blockers:
            print(f"- {item}")
        if warnings:
            print("\n提醒：")
            for item in warnings:
                print(f"- {item}")
        return 1
    print("Preflight 通过")
    print(f"项目目录：{project_dir}")
    print("核心配置、状态文件和最小内容约束已通过。")
    if warnings:
        print("\n提醒：")
        for item in warnings:
            print(f"- {item}")
    return 0


def command_resume(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    missing = find_missing_files(project_dir)
    blockers = collect_preflight_blockers(project_dir) if not missing else []
    warnings = collect_preflight_warnings(project_dir) if not missing else []
    if missing:
        print("Resume 失败，缺少以下文件：")
        for item in missing:
            print(f"- {item}")
        return 1
    if blockers:
        print("Resume 失败，以下内容仍需先补齐：")
        for item in blockers:
            print(f"- {item}")
        return 1

    task_log = read_text(project_dir / "task_log.md")
    role_state = read_text(project_dir / "state" / "角色状态.md")
    hook_state = read_text(project_dir / "state" / "伏笔列表.md")
    history_text = read_text(project_dir / "state" / "剧集历史.md")
    history_rows = parse_history_rows(history_text)
    recent_rows = recent_completed_rows(history_rows, limit=3)
    latest = recent_rows[-1] if recent_rows else None

    next_episode_num = None
    for line in read_text(project_dir / "linenew.md").splitlines():
        number_match = re.match(r"^\s*(?:第\s*)?(\d+)", line)
        if not number_match:
            continue
        number = int(number_match.group(1))
        if not any(row["episode"] == str(number) and row["status"] in COMPLETED_STATUSES for row in history_rows):
            next_episode_num = number
            break

    print("项目恢复摘要")
    print(f"- 项目目录：{project_dir}")
    print(f"- 创作阶段：{extract_task_field(task_log, '创作阶段')}")
    print(f"- 最新完成集：{extract_task_field(task_log, '最新完成集')}")
    print(f"- 当前处理集：{extract_task_field(task_log, '当前处理集')}")
    if latest:
        print(f"- 最近完成摘要：第{latest['episode']}集《{latest['title']}》 / {latest['summary']}")
    if next_episode_num is not None:
        title, core_event = lookup_episode_outline(project_dir, next_episode_num)
        print(f"- 下一集建议：第{next_episode_num}集《{title or '待命名'}》")
        if core_event:
            print(f"- 下一集核心事件：{core_event}")

    print("\n最近 2-3 集摘要：")
    if recent_rows:
        for row in recent_rows:
            print(f"- 第{row['episode']}集《{row['title']}》：{row['summary']}")
    else:
        print("- 暂无已完成剧集摘要")

    print("\n角色状态摘录：")
    for line in role_state.splitlines()[:12]:
        print(line)

    print("\n活跃伏笔摘录：")
    for line in hook_state.splitlines()[:12]:
        print(line)

    if warnings:
        print("\n提醒：")
        for item in warnings:
            print(f"- {item}")
    return 0


def build_plan_text(
    episode_num: int,
    title: str,
    core_event: str,
    target_duration: str,
    scene_count: int,
) -> str:
    scene_templates: list[tuple[str, str, str, str]] = []
    for index in range(1, scene_count + 1):
        if index == 1:
            scene_templates.append(
                (
                    "35-45秒",
                    "主角先撞见异常、先吃亏，或拿到危险道具，3 秒内入冲突",
                    "不能只寒暄，必须当场出现风险、误会、偷听、撞破或可疑行为",
                    "开场钩子",
                )
            )
            continue
        if index == scene_count:
            scene_templates.append(
                (
                    "35-45秒",
                    "主角带着新判断主动追击、试探、交易或逃脱",
                    "必须落地成强后果卡点：身份暴露、证据反噬、被包围、抓错人、计划翻车",
                    "强卡点",
                )
            )
            continue
        if index == scene_count - 1 and scene_count >= 4:
            scene_templates.append(
                (
                    "35-45秒",
                    "正面对撞、设局、逼问、偷录、截胡或反打",
                    "至少给一次可见爽点：打脸、压制、拿到证据、反杀、逼出真话",
                    "中段爽点",
                )
            )
            continue
        if index == 2:
            scene_templates.append(
                (
                    "40-50秒",
                    "追线索、试探对手或验证猜测，不许坐着复述背景",
                    "必须有信息升级和第一次反压，最好附带一个错误判断或代价",
                    "信息升级",
                )
            )
            continue
        scene_templates.append(
            (
                "35-45秒",
                "局势继续抬高，关系、利益或危险必须更近一步",
                "至少发生一次翻转：有人失手、站队变化、真相加码、实证到手或风险贴脸",
                "反转/代价",
            )
        )

    lines = [
        f"# 第{episode_num}集 创作计划",
        "",
        "## 输入",
        f"- 标题：{title}",
        f"- 核心事件：{core_event or '待补充'}",
        f"- 目标时长：{target_duration}",
        f"- 目标场景数：{scene_count}",
        "",
        "## 硬约束",
        "- 3 秒内进入冲突",
        "- 默认 4-5 个场景",
        "- 独立地点切换不超过 3 次",
        "- 至少 3 个爽点",
        "- 结尾必须留卡点",
        "- 首场景写主角完整外貌，后续只写服装变化",
        "",
        "## 填表提醒",
        "- 每场至少完成“目标 -> 阻碍 -> 变化”三步，不允许整场只解释信息。",
        "- 每场至少安排 2 次有效推进：试探、反压、偷录、打脸、拿证据、交易、逃脱、暴露风险等任选其二。",
        "- 宁可压缩光影/画质形容词，也不要把剧情写成一问一答的瘦场景。",
        "",
        "## 场景节奏卡",
        "| 场景 | 目标秒数 | 入场局势 | 必须发生的升级 | 爽点/代价/卡点 |",
        "|------|----------|----------|------------------|----------------|",
    ]
    for index, (seconds, entry_state, escalation, payoff) in enumerate(scene_templates, start=1):
        lines.append(f"| {index} | {seconds} | {entry_state} | {escalation} | {payoff} |")
    lines.extend(
        [
            "",
            "## 风险排查",
            "- 哪个角色最容易越权说出不该知道的信息？",
            "- 哪个场景最像小说描写而不是镜头？",
            "- 本集的 3 个爽点分别是什么？",
            "- 哪一场承担硬信息揭示，哪一场承担正面对撞，哪一场承担强卡点？",
        ]
    )
    return "\n".join(lines)


def resolve_episode_meta(project_dir: Path, episode_num: int, title: str | None, core_event: str | None) -> tuple[str, str]:
    outline_title, outline_event = lookup_episode_outline(project_dir, episode_num)
    resolved_title = title or outline_title or f"第{episode_num}集"
    resolved_event = core_event or outline_event or ""
    return resolved_title, resolved_event


def command_plan(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    title, core_event = resolve_episode_meta(project_dir, args.episode_num, args.title, args.core_event)
    runtime_path = plan_path_for_episode(project_dir, args.episode_num)
    runtime_path.write_text(
        build_plan_text(
            args.episode_num,
            title,
            core_event,
            args.target_duration,
            args.scene_count,
        ),
        encoding="utf-8",
    )
    update_task_log_status(project_dir, args.episode_num, title, "场景规划中")
    print(runtime_path)
    return 0


def build_prompt_pack(project_dir: Path, episode_num: int, title: str, core_event: str, target_duration: str) -> str:
    sections = []
    for filename in REQUIRED_CORE_FILES:
        path = project_dir / filename
        sections.append(f"[{filename}]\n{read_text(path).strip()}")

    task_log = read_text(project_dir / "task_log.md").strip()
    role_state = read_text(project_dir / "state" / "角色状态.md").strip()
    hook_state = read_text(project_dir / "state" / "伏笔列表.md").strip()
    history_rows = parse_history_rows(read_text(project_dir / "state" / "剧集历史.md"))
    recent_rows = recent_completed_rows(history_rows, before_episode=episode_num, limit=3)
    recent_summary_lines = (
        [f"- 第{row['episode']}集《{row['title']}》：{row['summary']}" for row in recent_rows]
        if recent_rows
        else ["- 暂无已完成剧集摘要"]
    )
    plan_text = read_text(plan_path_for_episode(project_dir, episode_num)).strip()
    synopsis_text = extract_episode_synopsis(project_dir, episode_num)
    previous_script_path = find_episode_script(project_dir, episode_num - 1) if episode_num > 1 else None
    previous_script_excerpt = tail_excerpt(read_text(previous_script_path)) if previous_script_path else ""

    prompt_lines = [
        "你正在续写平台向微短剧。先核对恢复摘要和场景卡；若出现冲突，以状态文件 > 场景计划 > 历史摘要 > 上一集剧本为准。",
        "",
        "## 核心配置",
        *sections,
        "",
        "## 当前任务",
        f"- 当前要写：第{episode_num}集《{title}》",
        f"- 本集核心事件：{core_event or '待补充'}",
        f"- 目标时长：{target_duration}",
        "",
        "## 恢复摘要",
        "[task_log.md]",
        task_log,
        "",
        "最近 2-3 集摘要：",
        *recent_summary_lines,
        "",
        "[state/角色状态.md]",
        role_state,
        "",
        "[state/伏笔列表.md]",
        hook_state,
        "",
        f"[{plan_path_for_episode(project_dir, episode_num).relative_to(project_dir)}]",
        plan_text,
        "",
        "## 剧情密度要求",
        "- 每个场景至少完成“目标 -> 阻碍 -> 变化”三步，不能只停在聊天和说明信息。",
        "- 每个场景至少做出 2 次有效推进：试探、反压、拿证据、交易、拆穿、逃脱、反打、暴露风险等任选其二。",
        "- 默认每个场景 3-6 句有效对白；若对白更少，必须用动作结果补足推进，不能变成空镜+一句结论。",
        "- 本集至少落地 1 个硬信息揭示、1 个正面对撞、1 个主动反制、1 个强后果卡点。",
        "- 爽点必须表现为当场占优、拆穿、截胡、证据到手、身份压制、局势翻转之一，不能只是“知道了一个消息”。",
        "- 宁可缩短 `(光影)/(镜头)/(画质)` 修饰词，也不要牺牲冲突、反转和对白密度。",
    ]

    if synopsis_text:
        prompt_lines.extend(
            [
                "",
                f"[docs/分集梗概.md / 第{episode_num}集]",
                synopsis_text,
            ]
        )

    if previous_script_path and previous_script_excerpt:
        prompt_lines.extend(
            [
                "",
                f"[上一集剧本尾段: {previous_script_path.relative_to(project_dir)}]",
                previous_script_excerpt,
            ]
        )

    prompt_lines.extend(
        [
            "",
            "## 输出要求",
        "1. 总字符数≤3000；优先压缩视觉修饰词，不要把剧情推进压没。",
        "2. 默认分 4-5 个场景，独立地点切换不超过 3 次。",
        "3. 开场 3 秒内就要出事，不要先写校园日常、寒暄和背景介绍。",
        "4. 每个场景都要有中段升级和出场变化，不能只完成“发现线索”。",
        "5. 每个场景使用以下结构：",
        "   场景X: 地点(起始秒-结束秒)",
        "   【环境空镜Xs】描述",
        "   (主体)角色外貌(首场景写全，后续只写服装变化)",
        "   (环境)...",
        "   (动作)...",
        "   (光影)...",
        "   (镜头)...",
        "   (画质)...",
        "   台词:",
        "   【停顿Xs】",
        '   角色名:"对话"',
        "6. 台词不含动作和语速说明；默认每场至少 3 句有效对白。",
        "7. 本集至少 3 个爽点，且至少 1 次真实代价或翻车。",
        "8. 禁止心理描写、环境抒情、流水账过程和无效水词。",
        "9. 不要空行，不要 --- 分隔符。",
        "10. 结尾必须留卡点，且不能让角色越权说出不该知道的信息。",
        "",
        "## 生成前自检",
        "- 最近 2-3 集摘要、角色知情状态、活跃伏笔与本集场景卡是否一致？",
        "- 首场景是否写清主角完整外貌，后续场景是否只写服装/造型变化？",
        "- 哪 3 个瞬间承担本集爽点？哪一场承担硬信息揭示、正面对撞、主动反制？",
        "- 如果删掉本场 1/2 的镜头修饰词，剧情推进是否反而更清楚？",
        "- 最后一个场景的卡点是否已经带出明确后果，而不是泛泛悬念？",
        ]
    )
    return "\n".join(prompt_lines).rstrip() + "\n"


def build_scene_plan_excerpt(scene_rows: list[dict[str, str]], scene_num: int) -> list[str]:
    selected_rows = [
        row for row in scene_rows if abs(int(row["scene"]) - scene_num) <= 1
    ]
    lines = [
        "| 场景 | 目标秒数 | 入场局势 | 必须发生的升级 | 爽点/代价/卡点 |",
        "|------|----------|----------|------------------|----------------|",
    ]
    for row in selected_rows:
        scene_label = row["scene"]
        marker = " <- 当前场" if int(scene_label) == scene_num else ""
        lines.append(
            f"| {scene_label} | {row['target_seconds']} | {row['entry_state']} | {row['escalation']} | {row['payoff']}{marker} |"
        )
    return lines


def build_scene_prompt_pack(
    project_dir: Path,
    episode_num: int,
    scene_num: int,
    title: str,
    core_event: str,
    target_duration: str,
    shot_seconds: int,
) -> str:
    sections = []
    for filename in REQUIRED_CORE_FILES:
        path = project_dir / filename
        sections.append(f"[{filename}]\n{read_text(path).strip()}")

    task_log = read_text(project_dir / "task_log.md").strip()
    role_state = read_text(project_dir / "state" / "角色状态.md").strip()
    hook_state = read_text(project_dir / "state" / "伏笔列表.md").strip()
    history_rows = parse_history_rows(read_text(project_dir / "state" / "剧集历史.md"))
    recent_rows = recent_completed_rows(history_rows, before_episode=episode_num, limit=3)
    recent_summary_lines = (
        [f"- 第{row['episode']}集《{row['title']}》：{row['summary']}" for row in recent_rows]
        if recent_rows
        else ["- 暂无已完成剧集摘要"]
    )
    plan_text = read_text(plan_path_for_episode(project_dir, episode_num)).strip()
    scene_rows = parse_scene_plan_rows(plan_text)
    current_row = next((row for row in scene_rows if int(row["scene"]) == scene_num), None)
    if not current_row:
        raise ValueError(f"未在场景卡中找到场景{scene_num}")

    synopsis_text = extract_episode_synopsis(project_dir, episode_num)
    previous_episode_script_path = find_episode_script(project_dir, episode_num - 1) if episode_num > 1 else None
    previous_episode_excerpt = (
        tail_excerpt(read_text(previous_episode_script_path))
        if previous_episode_script_path
        else ""
    )
    current_scene_outputs = {scene: path for scene, path in find_scene_output_files(project_dir, episode_num)}
    previous_scene_path = current_scene_outputs.get(scene_num - 1)
    previous_scene_excerpt = tail_excerpt(read_text(previous_scene_path), max_chars=1200) if previous_scene_path else ""
    scene_count = len(scene_rows)
    video_unit_count = estimate_video_unit_count(current_row["target_seconds"], shot_seconds)
    bridge_hint = "直接把强卡点压到观众脸上。" if scene_num == scene_count else f"结尾必须把悬念和压力明确交给场景{scene_num + 1}。"

    prompt_lines = [
        "你正在分场续写平台向微短剧。当前工具一次只处理一个场景，目标是把整集拆成多个可连续生成的场景包。",
        "",
        "## 核心配置",
        *sections,
        "",
        "## 当前任务",
        f"- 当前只写：第{episode_num}集《{title}》的场景{scene_num}",
        f"- 本集核心事件：{core_event or '待补充'}",
        f"- 本集目标时长：{target_duration}",
        f"- 当前场目标秒数：{current_row['target_seconds']}",
        f"- 当前场入场局势：{current_row['entry_state']}",
        f"- 当前场必须升级：{current_row['escalation']}",
        f"- 当前场结果类型：{current_row['payoff']}",
        f"- 当前场建议拆成约 {video_unit_count} 个 {shot_seconds} 秒视频单元",
        "",
        "## 恢复摘要",
        "[task_log.md]",
        task_log,
        "",
        "最近 2-3 集摘要：",
        *recent_summary_lines,
        "",
        "[state/角色状态.md]",
        role_state,
        "",
        "[state/伏笔列表.md]",
        hook_state,
        "",
        "## 邻近场景卡",
        *build_scene_plan_excerpt(scene_rows, scene_num),
    ]

    if synopsis_text:
        prompt_lines.extend(
            [
                "",
                f"[docs/分集梗概.md / 第{episode_num}集]",
                synopsis_text,
            ]
        )

    if previous_episode_excerpt:
        prompt_lines.extend(
            [
                "",
                f"[上一集剧本尾段: {previous_episode_script_path.relative_to(project_dir)}]",
                previous_episode_excerpt,
            ]
        )

    if previous_scene_excerpt:
        prompt_lines.extend(
            [
                "",
                f"[本集上一场尾段: {previous_scene_path.relative_to(project_dir)}]",
                previous_scene_excerpt,
            ]
        )

    prompt_lines.extend(
        [
            "",
            "## 分场要求",
            "- 只输出当前这一场，不要把后续场景提前写出来。",
            "- 本场内部也要完成“目标 -> 阻碍 -> 变化”三步，不能只做信息复述。",
            "- 本场至少出现 2 次有效推进：试探、反压、拿证据、交易、拆穿、逃脱、反打、暴露风险等任选其二。",
            "- 本场对白要短狠有信息量，默认至少 3 句有效对白。",
            f"- 本场结尾：{bridge_hint}",
            "- 宁可缩短 `(光影)/(镜头)/(画质)` 修饰词，也不要把动作、反转和对白压没。",
            "",
            "## 输出格式",
            f"1. 先只输出 `场景{scene_num}:` 这一场的完整剧本块。",
            "2. 剧本块格式仍保持：场景标题 / 环境空镜 / 主体 / 环境 / 动作 / 光影 / 镜头 / 画质 / 台词。",
            "3. 剧本块后追加 `## 5秒镜头单元表`。",
            f"4. `## 5秒镜头单元表` 必须拆成约 {video_unit_count} 行，每行约 {shot_seconds} 秒。",
            "5. 单元表列建议：镜头 | 秒数 | 画面目标 | 人物/动作 | 台词/口型 | 承上启下。",
            "6. 每个镜头单元都要能直接喂给 5 秒视频工具，不要写成抽象总结。",
            "7. 不要输出其他场景，不要输出解释说明。",
            "",
            "## 生成前自检",
            "- 当前场是否真的发生了升级，而不是停在“发现线索”？",
            "- 当前场的爽点/压制/反打是否能在画面里直接看出来？",
            "- 镜头单元表是否能覆盖当前场的完整剧情，不会出现中间断档？",
        ]
    )
    return "\n".join(prompt_lines).rstrip() + "\n"


def command_compose(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    title, core_event = resolve_episode_meta(project_dir, args.episode_num, args.title, args.core_event)
    blockers, warnings = collect_episode_context_issues(project_dir, args.episode_num, title, core_event)
    if blockers:
        print("Compose 失败：")
        for item in blockers:
            print(f"- {item}")
        return 1
    if warnings:
        print("Compose 提醒：")
        for item in warnings:
            print(f"- {item}")
    prompt_path = prompt_path_for_episode(project_dir, args.episode_num)
    update_task_log_status(project_dir, args.episode_num, title, "单集创作中")
    prompt_path.write_text(
        build_prompt_pack(project_dir, args.episode_num, title, core_event, args.target_duration),
        encoding="utf-8",
    )
    print(prompt_path)
    return 0


def command_compose_scenes(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    title, core_event = resolve_episode_meta(project_dir, args.episode_num, args.title, args.core_event)
    blockers, warnings = collect_episode_context_issues(project_dir, args.episode_num, title, core_event)
    if blockers:
        print("Compose-scenes 失败：")
        for item in blockers:
            print(f"- {item}")
        return 1
    if warnings:
        print("Compose-scenes 提醒：")
        for item in warnings:
            print(f"- {item}")

    plan_text = read_text(plan_path_for_episode(project_dir, args.episode_num))
    scene_rows = parse_scene_plan_rows(plan_text)
    if not scene_rows:
        print("Compose-scenes 失败：当前场景卡缺少可解析的 `场景节奏卡` 表格。")
        return 1

    available_scene_nums = [int(row["scene"]) for row in scene_rows]
    if args.scene_num is not None and args.scene_num not in available_scene_nums:
        print(f"Compose-scenes 失败：场景{args.scene_num} 不在当前场景卡里。")
        return 1

    target_scene_nums = [args.scene_num] if args.scene_num else available_scene_nums
    generated_paths: list[Path] = []
    update_task_log_status(project_dir, args.episode_num, title, "分场创作中")
    for scene_num in target_scene_nums:
        prompt_path = scene_prompt_path_for_episode(project_dir, args.episode_num, scene_num)
        prompt_path.write_text(
            build_scene_prompt_pack(
                project_dir,
                args.episode_num,
                scene_num,
                title,
                core_event,
                args.target_duration,
                args.shot_seconds,
            ),
            encoding="utf-8",
        )
        generated_paths.append(prompt_path)

    for path in generated_paths:
        print(path)
    return 0


def command_stitch_scenes(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    scene_files = find_scene_output_files(project_dir, args.episode_num)
    if not scene_files:
        print("Stitch-scenes 失败：未找到任何分场正文文件。")
        print("请把每场结果保存成 `runtime/episode-XXXX.scene-YY.md` 或 `.txt`。")
        return 1

    plan_rows = parse_scene_plan_rows(read_text(plan_path_for_episode(project_dir, args.episode_num)))
    expected_count = len(plan_rows) if plan_rows else None
    available_scene_nums = [scene_num for scene_num, _ in scene_files]
    if expected_count is not None:
        missing_scene_nums = [scene_num for scene_num in range(1, expected_count + 1) if scene_num not in available_scene_nums]
        if missing_scene_nums:
            print("Stitch-scenes 失败：缺少以下场景正文文件：")
            for scene_num in missing_scene_nums:
                print(f"- scene-{scene_num:02d}")
            return 1

    stitched_parts = []
    for _, path in scene_files:
        content = read_text(path).strip()
        if content:
            stitched_parts.append(content)
    if not stitched_parts:
        print("Stitch-scenes 失败：找到文件，但内容为空。")
        return 1

    output_path = Path(args.output).resolve() if args.output else stitched_scene_path_for_episode(project_dir, args.episode_num)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(stitched_parts).rstrip() + "\n", encoding="utf-8")

    print(output_path)
    for scene_num, path in scene_files:
        print(f"- scene-{scene_num:02d}: {path}")
    return 0


def count_effective_chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def count_dialogue_lines(text: str) -> int:
    return len(DIALOGUE_LINE_PATTERN.findall(text))


def split_scene_blocks(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^场景\d+:\s*.*$", text))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((match.group(0), text[start:end]))
    return blocks


def detect_location_changes(headers: list[str]) -> tuple[int, list[str]]:
    locations: list[str] = []
    for header in headers:
        match = re.match(r"^场景\d+:\s*(.*?)\s*\(", header.strip())
        if match:
            locations.append(match.group(1).strip())
    changes = 0
    previous = None
    for location in locations:
        if previous is None:
            previous = location
            continue
        if location != previous:
            changes += 1
            previous = location
    return changes, locations


def command_check(args: argparse.Namespace) -> int:
    script_path = Path(args.script_path).resolve()
    if not script_path.exists():
        print(f"文件不存在：{script_path}")
        return 1

    text = read_text(script_path)
    effective_chars = count_effective_chars(text)
    blank_line_count = sum(1 for line in text.splitlines() if not line.strip())
    separator_count = text.count("---")
    scene_blocks = split_scene_blocks(text)
    headers = [header for header, _ in scene_blocks]
    location_changes, locations = detect_location_changes(headers)
    dialogue_counts = [
        count_dialogue_lines(block.split("台词:", 1)[1] if "台词:" in block else "")
        for _, block in scene_blocks
    ]
    total_dialogue_lines = sum(dialogue_counts)

    print(f"检查文件：{script_path}")
    print(f"- 有效字符数：{effective_chars}")
    print(f"- 场景数：{len(scene_blocks)}")
    print(f"- 地点切换次数：{location_changes}")
    if locations:
        print(f"- 场景地点：{' / '.join(locations)}")
    print(f"- 有效对白数：{total_dialogue_lines}")
    if dialogue_counts:
        print(f"- 单场对白数：{' / '.join(str(count) for count in dialogue_counts)}")
    print(f"- 空行数：{blank_line_count}")
    print(f"- --- 分隔符数量：{separator_count}")

    errors: list[str] = []
    warnings: list[str] = []

    if effective_chars > args.max_chars:
        errors.append(f"字符数超标：{effective_chars} > {args.max_chars}")
    if not scene_blocks:
        errors.append("未检测到任何 `场景X:` 场景块。")
    if not 4 <= len(scene_blocks) <= 5:
        warnings.append("默认建议 4-5 个场景，当前不在建议范围内。")
    if location_changes > 3:
        warnings.append("独立地点切换超过 3 次。")
    if effective_chars < MIN_EFFECTIVE_SCRIPT_CHARS:
        warnings.append(
            f"正文偏短：{effective_chars} < {MIN_EFFECTIVE_SCRIPT_CHARS}，容易导致爽点不足和剧情推进偏瘦。"
        )
    if total_dialogue_lines < max(MIN_DIALOGUE_LINES_TOTAL, len(scene_blocks) * MIN_DIALOGUE_LINES_PER_SCENE):
        warnings.append(
            "有效对白偏少，当前场景更像提纲复述；优先补正面对撞、试探、反压和结果。"
        )
    if blank_line_count > 0:
        warnings.append("存在空行，可能浪费字数。")
    if separator_count > 0:
        warnings.append("存在 --- 分隔符，建议删除。")

    required_markers = ("【环境空镜", "(主体)", "(动作)", "(光影)", "(镜头)", "(画质)", "台词:")
    for header, block in scene_blocks:
        if not re.search(r"\(\d+\s*-\s*\d+\s*(?:s|S|秒)?\)", header):
            errors.append(f"{header} 缺少合法时长范围。")
        missing_markers = [marker for marker in required_markers if marker not in block]
        if missing_markers:
            errors.append(f"{header} 缺少字段：{', '.join(missing_markers)}")
        if "台词:" in block and not re.search(r"(?m)^[^:\n：]+[:：]", block.split("台词:", 1)[1]):
            warnings.append(f"{header} 的 `台词:` 后未检测到有效对白行。")

    for header, dialogue_count in zip(headers, dialogue_counts):
        if dialogue_count < MIN_DIALOGUE_LINES_PER_SCENE:
            warnings.append(
                f"{header} 有效对白少于 {MIN_DIALOGUE_LINES_PER_SCENE} 句；若不是纯动作场，说明推进可能过瘦。"
            )

    for keyword in BANNED_RISK_WORDS:
        count = text.count(keyword)
        if count:
            warnings.append(f"检测到风险词 `{keyword}` {count} 次。")

    dialogue_action_matches = re.findall(
        r"(?m)^[^:\n：]+[（(][^)\n]*(动作|语速)[^)\n]*[)）]\s*[:：]",
        text,
    )
    if dialogue_action_matches:
        warnings.append("检测到台词行内含动作或语速说明。")

    if errors:
        print("\n错误：")
        for item in errors:
            print(f"- {item}")
    if warnings:
        print("\n警告：")
        for item in warnings:
            print(f"- {item}")

    if not errors and not warnings:
        print("\n检查通过。")
    return 1 if errors else 0


def upsert_history_row(
    text: str,
    episode_num: int,
    title: str,
    status: str,
    core_event: str,
    summary: str,
) -> str:
    header = "| 集数 | 标题 | 状态 | 核心事件 | 摘要 |"
    divider = "|------|------|------|----------|------|"
    lines = [line for line in text.splitlines() if line.strip()]
    data_rows = [line for line in lines if line.startswith("|") and line not in {header, divider}]
    target_prefix = f"| {episode_num} |"
    new_row = f"| {episode_num} | {title} | {status} | {core_event or '待补充'} | {summary} |"
    updated_rows = [row for row in data_rows if not row.startswith(target_prefix)]
    updated_rows.append(new_row)

    def episode_sort_key(row: str) -> int:
        match = re.match(r"^\|\s*(\d+)\s*\|", row)
        return int(match.group(1)) if match else 0

    updated_rows.sort(key=episode_sort_key)
    return "\n".join(["# 剧集历史", "", header, divider, *updated_rows]) + "\n"


def update_recent_summaries(task_log: str, episode_num: int, title: str, summary: str) -> str:
    new_line = f"- 第{episode_num}集《{title}》：{summary}"
    match = re.search(r"(?ms)^## 最近三集摘要\n(.*?)(?=^## |\Z)", task_log)
    lines: list[str] = []
    if match:
        lines = [line.strip() for line in match.group(1).splitlines() if line.strip() and line.strip() != "- 暂无"]
    filtered = [line for line in lines if not line.startswith(f"- 第{episode_num}集《{title}》：")]
    return replace_section(task_log, "最近三集摘要", [new_line, *filtered[:2]])


def command_finish(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    script_path = Path(args.script_path).resolve()
    if not script_path.exists():
        print(f"剧本文件不存在：{script_path}")
        return 1
    archived_script_path = persist_episode_script(project_dir, args.episode_num, script_path)

    title, core_event = resolve_episode_meta(project_dir, args.episode_num, args.title, args.core_event)

    task_log_path = project_dir / "task_log.md"
    task_log = read_text(task_log_path)
    task_log = replace_task_field(task_log, "创作阶段", f"已完成第{args.episode_num}集")
    task_log = replace_task_field(task_log, "最新完成集", f"第{args.episode_num}集《{title}》")
    task_log = replace_task_field(task_log, "当前处理集", "无")
    task_log = replace_task_field(task_log, "最近交付文件", archived_script_path.name)
    next_title, next_core_event = lookup_episode_outline(project_dir, args.episode_num + 1)
    if next_title:
        next_target = f"第{args.episode_num + 1}集《{next_title}》"
        if next_core_event:
            next_target += f" / {next_core_event}"
        task_log = replace_task_field(task_log, "下一集目标", next_target)
    task_log = update_recent_summaries(task_log, args.episode_num, title, args.summary)
    task_log_path.write_text(task_log, encoding="utf-8")

    history_path = project_dir / "state" / "剧集历史.md"
    history_text = read_text(history_path)
    history_text = upsert_history_row(history_text, args.episode_num, title, "已完成", core_event, args.summary)
    history_path.write_text(history_text, encoding="utf-8")

    role_state_path = project_dir / "state" / "角色状态.md"
    role_state_text = read_text(role_state_path)
    role_state_note = f"- 第{args.episode_num}集《{title}》：根据已交付剧本确认角色知情、关系与造型变化。摘要：{args.summary}"
    role_state_text = prepend_section_note(role_state_text, "待确认回写", role_state_note)
    role_state_path.write_text(role_state_text, encoding="utf-8")

    hook_state_path = project_dir / "state" / "伏笔列表.md"
    hook_state_text = read_text(hook_state_path)
    hook_state_note = f"- 第{args.episode_num}集《{title}》：根据已交付剧本确认伏笔新增、推进或回收。摘要：{args.summary}"
    hook_state_text = prepend_section_note(hook_state_text, "待确认回写", hook_state_note)
    hook_state_path.write_text(hook_state_text, encoding="utf-8")

    print("已更新：")
    print(f"- 归档剧本：{archived_script_path}")
    print(f"- {task_log_path}")
    print(f"- {history_path}")
    print(f"- {role_state_path}")
    print(f"- {hook_state_path}")
    return 0


def command_next_episode(args: argparse.Namespace) -> int:
    preflight_status = command_preflight(argparse.Namespace(project_dir=args.project_dir))
    if preflight_status != 0:
        return preflight_status

    resume_status = command_resume(argparse.Namespace(project_dir=args.project_dir))
    if resume_status != 0:
        return resume_status

    plan_status = command_plan(
        argparse.Namespace(
            project_dir=args.project_dir,
            episode_num=args.episode_num,
            title=args.title,
            core_event=args.core_event,
            target_duration=args.target_duration,
            scene_count=args.scene_count,
        )
    )
    if plan_status != 0:
        return plan_status

    return command_compose(
        argparse.Namespace(
            project_dir=args.project_dir,
            episode_num=args.episode_num,
            title=args.title,
            core_event=args.core_event,
            target_duration=args.target_duration,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="微短剧项目统一入口")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("rules")
    subparsers.add_parser("workflows")
    subparsers.add_parser("commands")

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("project_name")
    init_parser.add_argument("--path", default=".")

    init_project_parser = subparsers.add_parser("init-project")
    init_project_parser.add_argument("project_name")
    init_project_parser.add_argument("--path", default=".")

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("project_dir")

    resume_parser = subparsers.add_parser("resume")
    resume_parser.add_argument("project_dir")

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("project_dir")
    plan_parser.add_argument("--episode-num", type=int, required=True)
    plan_parser.add_argument("--title")
    plan_parser.add_argument("--core-event")
    plan_parser.add_argument("--target-duration", default="3-5分钟")
    plan_parser.add_argument("--scene-count", type=int, default=4)

    compose_parser = subparsers.add_parser("compose")
    compose_parser.add_argument("project_dir")
    compose_parser.add_argument("--episode-num", type=int, required=True)
    compose_parser.add_argument("--title")
    compose_parser.add_argument("--core-event")
    compose_parser.add_argument("--target-duration", default="3-5分钟")

    compose_scenes_parser = subparsers.add_parser("compose-scenes")
    compose_scenes_parser.add_argument("project_dir")
    compose_scenes_parser.add_argument("--episode-num", type=int, required=True)
    compose_scenes_parser.add_argument("--title")
    compose_scenes_parser.add_argument("--core-event")
    compose_scenes_parser.add_argument("--target-duration", default="3-5分钟")
    compose_scenes_parser.add_argument("--scene-num", type=int)
    compose_scenes_parser.add_argument("--shot-seconds", type=int, default=5)

    stitch_scenes_parser = subparsers.add_parser("stitch-scenes")
    stitch_scenes_parser.add_argument("project_dir")
    stitch_scenes_parser.add_argument("--episode-num", type=int, required=True)
    stitch_scenes_parser.add_argument("--output")

    next_episode_parser = subparsers.add_parser("next-episode")
    next_episode_parser.add_argument("project_dir")
    next_episode_parser.add_argument("--episode-num", type=int, required=True)
    next_episode_parser.add_argument("--title")
    next_episode_parser.add_argument("--core-event")
    next_episode_parser.add_argument("--target-duration", default="3-5分钟")
    next_episode_parser.add_argument("--scene-count", type=int, default=4)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("script_path")
    check_parser.add_argument("--max-chars", type=int, default=3000)

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("script_path")
    review_parser.add_argument("--max-chars", type=int, default=3000)

    finish_parser = subparsers.add_parser("finish")
    finish_parser.add_argument("project_dir")
    finish_parser.add_argument("episode_num", type=int)
    finish_parser.add_argument("script_path")
    finish_parser.add_argument("--title")
    finish_parser.add_argument("--core-event")
    finish_parser.add_argument("--summary", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "rules":
        render_catalog("Rule Catalog", RULE_LAYER_CATALOG)
        return 0
    if args.command == "workflows":
        render_catalog("Workflow Catalog", WORKFLOW_LAYER_CATALOG)
        return 0
    if args.command == "commands":
        render_catalog("Command Catalog", COMMAND_LAYER_CATALOG)
        return 0
    if args.command == "init":
        return command_init(args)
    if args.command == "init-project":
        return command_init(args)
    if args.command == "preflight":
        return command_preflight(args)
    if args.command == "resume":
        return command_resume(args)
    if args.command == "plan":
        return command_plan(args)
    if args.command == "compose":
        return command_compose(args)
    if args.command == "compose-scenes":
        return command_compose_scenes(args)
    if args.command == "stitch-scenes":
        return command_stitch_scenes(args)
    if args.command == "next-episode":
        return command_next_episode(args)
    if args.command in {"check", "review"}:
        return command_check(args)
    if args.command == "finish":
        return command_finish(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
