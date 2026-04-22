#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微短剧项目统一入口。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from new_project import create_drama_project, load_seed
except ModuleNotFoundError:
    from scripts.new_project import create_drama_project, load_seed


REPO_ROOT = Path(__file__).resolve().parents[1]


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
        "steps": ["preflight", "resume", "plan", "compose-scenes"],
        "summary": "进入新一集前的标准准备链，默认只生成分场规划 prompt，不再直接生成整集剧本。",
    },
    {
        "id": "review",
        "title": "单集结构化质检",
        "steps": ["check"],
        "summary": "检查字数、场景块、格式和小说化风险；不替代人工爽点/卡点复核。",
    },
    {
        "id": "consistency-check",
        "title": "项目上下文一致性检查",
        "steps": ["consistency-check"],
        "summary": "结合状态文件、分集梗概、上一集和当前剧本，提示知情越权、伏笔断裂和剧情偏航风险。",
    },
    {
        "id": "compose-scenes",
        "title": "分场创作包",
        "steps": ["compose-scenes", "compose-shots", "stitch-scenes"],
        "summary": "把整集拆成单集目录、单场 Prompt Pack 和单镜头 Prompt Pack，适合 5 秒视频镜头工作流。",
    },
    {
        "id": "finish",
        "title": "完结回写",
        "steps": ["finish", "apply-state-diff"],
        "summary": "回写最近完成集、剧集历史，生成 state diff，并可把确认后的 diff 应用回 Markdown 状态表。",
    },
]

COMMAND_LAYER_CATALOG: list[dict[str, Any]] = [
    {"group": "Layer", "commands": ["rules", "workflows", "commands"]},
    {
        "group": "Workflow",
        "commands": ["init-project", "next-episode", "compose-scenes", "compose-shots", "review", "consistency-check", "finish", "apply-state-diff"],
    },
    {
        "group": "Primitive",
        "commands": [
            "init",
            "preflight",
            "resume",
            "plan",
            "compose",
            "compose-scenes",
            "compose-shots",
            "stitch-scenes",
            "check",
            "consistency-check",
            "finish",
            "apply-state-diff",
        ],
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
FINISH_BLOCKING_RISK_WORD_THRESHOLD = 3
SIGNIFICANT_TERM_STOPWORDS = {
    "当前",
    "状态",
    "角色",
    "知道",
    "知道什么",
    "绝对不知道什么",
    "当前已知信息",
    "当前服装",
    "造型",
    "当前状态",
    "备注",
    "核心秘密",
    "任务",
    "主线任务",
    "公开目标",
    "隐藏目标",
    "表面身份",
    "隐藏身份",
    "剧情",
    "剧本",
    "场景",
    "第",
    "集",
    "起因",
    "经过",
    "结果",
    "卡点",
    "摘要",
    "最新",
    "完成",
    "处理",
    "内容",
    "信息",
    "目标",
    "计划",
    "线索",
}

DIALOGUE_LINE_PATTERN = re.compile(
    r"(?m)^(?!场景\d+[:：])(?!台词[:：])(?![【(（\-#])[^:\n：]{1,20}[:：]\s*(?!$)"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def normalize_value(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def stringify_value(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return default


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


def extract_section_by_heading_query(text: str, heading_query: str) -> str:
    matches = list(re.finditer(r"(?m)^## .*$", text))
    for index, match in enumerate(matches):
        heading = match.group(0)
        if heading_query not in heading:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return text[start:end].strip()
    return ""


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


def extract_bullet_mapping(text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*-\s*([^:：]+)[:：]\s*(.*)$", line)
        if not match:
            continue
        mapping[match.group(1).strip()] = match.group(2).strip()
    return mapping


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


def is_markdown_divider_cells(cells: tuple[str, ...] | list[str]) -> bool:
    normalized = [cell.replace(" ", "") for cell in cells]
    return bool(normalized) and all(cell and set(cell) <= {"-", ":"} for cell in normalized)


def backup_file(path: Path) -> Path:
    backup_path = path.with_suffix(path.suffix + ".bak")
    counter = 1
    while backup_path.exists():
        backup_path = path.with_suffix(path.suffix + f".bak{counter}")
        counter += 1
    backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path


def find_missing_files(project_dir: Path) -> list[str]:
    missing = []
    for relative_path in REQUIRED_CORE_FILES + REQUIRED_STATE_FILES:
        if not (project_dir / relative_path).exists():
            missing.append(relative_path)
    return missing


def collect_preflight_report(project_dir: Path) -> tuple[list[str], list[str], list[str]]:
    missing = find_missing_files(project_dir)
    blockers = collect_preflight_blockers(project_dir) if not missing else []
    warnings = collect_preflight_warnings(project_dir) if not missing else []
    return missing, blockers, warnings


def ensure_preflight_ready(project_dir: Path, command_name: str) -> tuple[bool, list[str]]:
    missing, blockers, warnings = collect_preflight_report(project_dir)
    if missing:
        print(f"{command_name} 失败：项目尚未通过 preflight。")
        print("缺少以下文件：")
        for item in missing:
            print(f"- {item}")
        return False, warnings
    if blockers:
        print(f"{command_name} 失败：项目尚未通过 preflight。")
        print("以下内容仍是空壳或模板占位：")
        for item in blockers:
            print(f"- {item}")
        if warnings:
            print("\n提醒：")
            for item in warnings:
                print(f"- {item}")
        return False, warnings
    return True, warnings


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


def supporting_role_cards(character_text: str) -> list[tuple[str, str]]:
    section = extract_section(character_text, "反派 / 关键配角")
    if not section:
        return []
    matches = re.finditer(r"(?ms)^###\s+(.+?)\n(.*?)(?=^### |\Z)", section)
    return [(match.group(1).strip(), match.group(2).strip()) for match in matches]


def supporting_role_context_issues(character_text: str) -> list[str]:
    section = extract_section(character_text, "反派 / 关键配角")
    if not section:
        return ["character-design.md 缺少 `## 反派 / 关键配角` 小节。"]
    if "按同样结构补齐" in section or "至少补 2 个关键反派/配角" in section:
        return ["character-design.md 仍是关键配角占位说明，至少补 2 个可驱动对手戏的角色卡。"]

    cards = supporting_role_cards(character_text)
    if len(cards) < 2:
        return ["character-design.md 至少补齐 2 个关键反派/配角卡，否则续写时容易失去对手戏压力。"]

    issues: list[str] = []
    for title, body in cards:
        for label in ("姓名", "表面身份", "公开目标", "隐藏目标", "主线任务"):
            value = extract_labeled_value(body, label)
            if is_placeholder_value(value):
                issues.append(f"character-design.md 的 `{title}/{label}` 未补齐。")
    return issues


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


def episode_runtime_dir(project_dir: Path, episode_num: int) -> Path:
    return project_dir / "runtime" / f"episode-{episode_num:04d}"


def episode_runtime_output_dir(project_dir: Path, episode_num: int) -> Path:
    runtime_dir = episode_runtime_dir(project_dir, episode_num)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def legacy_plan_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    return project_dir / "runtime" / f"episode-{episode_num:04d}.plan.md"


def legacy_prompt_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    return project_dir / "runtime" / f"episode-{episode_num:04d}.prompt.md"


def legacy_scene_prompt_path_for_episode(project_dir: Path, episode_num: int, scene_num: int) -> Path:
    return project_dir / "runtime" / f"episode-{episode_num:04d}.scene-{scene_num:02d}.prompt.md"


def legacy_scene_output_path_for_episode(project_dir: Path, episode_num: int, scene_num: int, extension: str = ".md") -> Path:
    return project_dir / "runtime" / f"episode-{episode_num:04d}.scene-{scene_num:02d}{extension}"


def legacy_stitched_scene_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    return project_dir / "runtime" / f"episode-{episode_num:04d}.assembled.md"


def scene_runtime_dir(project_dir: Path, episode_num: int, scene_num: int) -> Path:
    return episode_runtime_dir(project_dir, episode_num) / f"scene-{scene_num:02d}"


def scene_runtime_output_dir(project_dir: Path, episode_num: int, scene_num: int) -> Path:
    runtime_dir = scene_runtime_dir(project_dir, episode_num, scene_num)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def plan_output_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    return episode_runtime_output_dir(project_dir, episode_num) / "plan.md"


def plan_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    preferred_path = episode_runtime_dir(project_dir, episode_num) / "plan.md"
    legacy_path = legacy_plan_path_for_episode(project_dir, episode_num)
    return preferred_path if preferred_path.exists() or not legacy_path.exists() else legacy_path


def prompt_output_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    return episode_runtime_output_dir(project_dir, episode_num) / "prompt.md"


def prompt_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    preferred_path = episode_runtime_dir(project_dir, episode_num) / "prompt.md"
    legacy_path = legacy_prompt_path_for_episode(project_dir, episode_num)
    return preferred_path if preferred_path.exists() or not legacy_path.exists() else legacy_path


def scene_prompt_output_path_for_episode(project_dir: Path, episode_num: int, scene_num: int) -> Path:
    return scene_runtime_output_dir(project_dir, episode_num, scene_num) / "scene.prompt.md"


def scene_prompt_path_for_episode(project_dir: Path, episode_num: int, scene_num: int) -> Path:
    preferred_path = scene_runtime_dir(project_dir, episode_num, scene_num) / "scene.prompt.md"
    legacy_path = legacy_scene_prompt_path_for_episode(project_dir, episode_num, scene_num)
    return preferred_path if preferred_path.exists() or not legacy_path.exists() else legacy_path


def scene_output_path_for_episode(project_dir: Path, episode_num: int, scene_num: int, extension: str = ".md") -> Path:
    return scene_runtime_output_dir(project_dir, episode_num, scene_num) / f"scene{extension}"


def shot_prompt_output_path_for_episode(project_dir: Path, episode_num: int, scene_num: int, shot_num: int) -> Path:
    return scene_runtime_output_dir(project_dir, episode_num, scene_num) / f"shot-{shot_num:03d}.prompt.md"


def shot_output_path_for_episode(project_dir: Path, episode_num: int, scene_num: int, shot_num: int, extension: str = ".md") -> Path:
    return scene_runtime_output_dir(project_dir, episode_num, scene_num) / f"shot-{shot_num:03d}{extension}"


def scene_output_candidates(project_dir: Path, episode_num: int, scene_num: int) -> list[Path]:
    candidates = [
        scene_output_path_for_episode(project_dir, episode_num, scene_num, ".md"),
        scene_output_path_for_episode(project_dir, episode_num, scene_num, ".txt"),
        legacy_scene_output_path_for_episode(project_dir, episode_num, scene_num, ".md"),
        legacy_scene_output_path_for_episode(project_dir, episode_num, scene_num, ".txt"),
    ]
    scene_dir = scene_runtime_dir(project_dir, episode_num, scene_num)
    if scene_dir.exists():
        for path in episode_script_candidates(scene_dir):
            if path.name.endswith(".prompt.md") or path.name.startswith("shot-"):
                continue
            if path not in candidates:
                candidates.append(path)
    return candidates


def find_scene_output_file(project_dir: Path, episode_num: int, scene_num: int) -> Path | None:
    for path in scene_output_candidates(project_dir, episode_num, scene_num):
        if path.exists():
            return path
    return None


def scene_prompt_exists(project_dir: Path, episode_num: int, scene_num: int) -> bool:
    return (
        scene_prompt_output_path_for_episode(project_dir, episode_num, scene_num).exists()
        or legacy_scene_prompt_path_for_episode(project_dir, episode_num, scene_num).exists()
    )


def shot_output_candidates(project_dir: Path, episode_num: int, scene_num: int, shot_num: int) -> list[Path]:
    candidates = [
        shot_output_path_for_episode(project_dir, episode_num, scene_num, shot_num, ".md"),
        shot_output_path_for_episode(project_dir, episode_num, scene_num, shot_num, ".txt"),
    ]
    scene_dir = scene_runtime_dir(project_dir, episode_num, scene_num)
    if scene_dir.exists():
        for path in episode_script_candidates(scene_dir):
            if path.name.endswith(".prompt.md"):
                continue
            match = re.match(rf"^shot-{shot_num:03d}(?:\.[^.]+)?\.(md|txt)$", path.name)
            if match and path not in candidates:
                candidates.append(path)
    return candidates


def find_shot_output_files(project_dir: Path, episode_num: int, scene_num: int) -> list[tuple[int, Path]]:
    scene_dir = scene_runtime_dir(project_dir, episode_num, scene_num)
    if not scene_dir.exists():
        return []

    shot_files: dict[int, Path] = {}
    for path in episode_script_candidates(scene_dir):
        if path.name.endswith(".prompt.md"):
            continue
        match = re.match(r"^shot-(\d+)(?:\.[^.]+)?\.(md|txt)$", path.name)
        if not match:
            continue
        shot_num = int(match.group(1))
        if shot_num not in shot_files:
            shot_files[shot_num] = path
    return sorted(shot_files.items(), key=lambda item: item[0])


def shot_output_exists(project_dir: Path, episode_num: int, scene_num: int, shot_num: int) -> bool:
    return any(path.exists() for path in shot_output_candidates(project_dir, episode_num, scene_num, shot_num))


def next_missing_scene_num(project_dir: Path, episode_num: int, available_scene_nums: list[int]) -> int:
    for scene_num in available_scene_nums:
        if not find_scene_output_file(project_dir, episode_num, scene_num):
            return scene_num
    for scene_num in available_scene_nums:
        if not scene_prompt_exists(project_dir, episode_num, scene_num):
            return scene_num
    return available_scene_nums[0]


def next_missing_shot_num(project_dir: Path, episode_num: int, scene_num: int, available_shot_nums: list[int]) -> int:
    for shot_num in available_shot_nums:
        if not shot_output_exists(project_dir, episode_num, scene_num, shot_num):
            return shot_num
    return available_shot_nums[0]


def stitched_scene_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    preferred_path = episode_runtime_dir(project_dir, episode_num) / "assembled.md"
    legacy_path = legacy_stitched_scene_path_for_episode(project_dir, episode_num)
    return preferred_path if preferred_path.exists() or not legacy_path.exists() else legacy_path


def stitched_scene_output_path_for_episode(project_dir: Path, episode_num: int) -> Path:
    return episode_runtime_output_dir(project_dir, episode_num) / "assembled.md"


def canonical_episode_script_path(project_dir: Path, episode_num: int) -> Path:
    return project_dir / "episodes" / f"episode-{episode_num:04d}.md"


def episode_script_candidates(base_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for extension in TEXT_SCRIPT_EXTENSIONS:
        candidates.extend(sorted(base_dir.rglob(f"*{extension}")))
    return candidates


def episode_file_matches(path: Path, episode_num: int) -> bool:
    candidates = (
        path.stem,
        path.name,
        "/".join(path.parts[-3:]),
    )
    patterns = (
        rf"第\s*{episode_num}\s*集",
        rf"(?:^|[^0-9]){episode_num:04d}(?:[^0-9]|$)",
        rf"(?:^|[^0-9]){episode_num:03d}(?:[^0-9]|$)",
        rf"(?:^|[^0-9]){episode_num:02d}(?:[^0-9]|$)",
        rf"(?:^|[^0-9]){episode_num}(?:[^0-9]|$)",
    )
    return any(re.search(pattern, candidate) for candidate in candidates for pattern in patterns)


def find_episode_script(project_dir: Path, episode_num: int) -> Path | None:
    candidates: list[Path] = []
    for directory in ("episodes", "runtime"):
        base_dir = project_dir / directory
        if not base_dir.exists():
            continue
        for path in episode_script_candidates(base_dir):
            if path.name.endswith(".plan.md") or path.name.endswith(".prompt.md"):
                continue
            if path.name in {"plan.md", "prompt.md"}:
                continue
            if any(part.startswith("scene-") for part in path.parts):
                continue
            if path.name.startswith("shot-"):
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
    episode_dir = episode_runtime_dir(project_dir, episode_num)
    if episode_dir.exists():
        for scene_dir in sorted(episode_dir.glob("scene-*")):
            if not scene_dir.is_dir():
                continue
            match = re.match(r"^scene-(\d+)$", scene_dir.name)
            if not match:
                continue
            scene_num = int(match.group(1))
            scene_path = find_scene_output_file(project_dir, episode_num, scene_num)
            if scene_path and scene_num not in scene_files:
                scene_files[scene_num] = scene_path

    legacy_pattern = re.compile(rf"^episode-{episode_num:04d}\.scene-(\d+)(?:\.[^.]+)?\.(md|txt)$")
    for path in episode_script_candidates(runtime_dir):
        if path.name.endswith(".prompt.md"):
            continue
        match = legacy_pattern.match(path.name)
        if not match:
            continue
        scene_num = int(match.group(1))
        if scene_num not in scene_files:
            scene_files[scene_num] = path
    return sorted(scene_files.items(), key=lambda item: item[0])


def assemble_scene_from_shot_files(project_dir: Path, episode_num: int, scene_num: int) -> str:
    shot_files = find_shot_output_files(project_dir, episode_num, scene_num)
    if not shot_files:
        return ""

    stitched_parts: list[str] = []
    for _, path in shot_files:
        content = read_text(path).strip()
        if content:
            stitched_parts.append(content)
    return "\n\n".join(stitched_parts).rstrip()


def parse_markdown_table_rows(text: str, header_patterns: tuple[str, ...]) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    table_started = False
    for line in text.splitlines():
        stripped = line.strip()
        if not table_started and any(stripped.startswith(pattern) for pattern in header_patterns):
            table_started = True
            continue
        if not table_started:
            continue
        if stripped.startswith("|---") or stripped.startswith("|------"):
            continue
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        cells = tuple(cell.strip() for cell in stripped.strip("|").split("|"))
        if is_markdown_divider_cells(cells):
            continue
        if cells:
            rows.append(cells)
    return rows


def unique_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def extract_role_state_current_states(role_state_text: str) -> dict[str, str]:
    return extract_bullet_mapping(extract_section(role_state_text, "当前集后状态"))


def extract_role_state_wardrobe(role_state_text: str) -> dict[str, str]:
    return extract_bullet_mapping(extract_section(role_state_text, "当前服装与造型"))


def extract_role_state_knowledge_rows(role_state_text: str) -> list[dict[str, str]]:
    section = extract_section(role_state_text, "知情状态表")
    rows = parse_markdown_table_rows(section, header_patterns=("| 角色 |",))
    parsed_rows: list[dict[str, str]] = []
    for cells in rows:
        if len(cells) < 4 or is_placeholder_value(cells[0], ("暂无", "无", "未记录")):
            continue
        parsed_rows.append(
            {
                "role": cells[0],
                "known": cells[1],
                "unknown": cells[2],
                "note": cells[3],
            }
        )
    return parsed_rows


def extract_active_hook_rows(hook_text: str) -> list[dict[str, str]]:
    section = extract_section(hook_text, "活跃伏笔")
    rows = parse_markdown_table_rows(section, header_patterns=("| 伏笔名称 |",))
    parsed_rows: list[dict[str, str]] = []
    for cells in rows:
        if len(cells) < 4 or is_placeholder_value(cells[0], ("暂无", "无", "未记录")):
            continue
        parsed_rows.append(
            {
                "name": cells[0],
                "status": cells[1],
                "first_appearance": cells[2],
                "note": cells[3],
            }
        )
    return parsed_rows


def extract_resolved_hook_rows(hook_text: str) -> list[dict[str, str]]:
    section = extract_section(hook_text, "已回收伏笔")
    rows = parse_markdown_table_rows(section, header_patterns=("| 伏笔名称 |",))
    parsed_rows: list[dict[str, str]] = []
    for cells in rows:
        if len(cells) < 3 or is_placeholder_value(cells[0], ("暂无", "无", "未记录")):
            continue
        parsed_rows.append(
            {
                "name": cells[0],
                "episode": cells[1],
                "note": cells[2],
            }
        )
    return parsed_rows


def normalize_role_value_items(value: Any) -> list[dict[str, str]]:
    items = value if isinstance(value, list) else []
    normalized_items: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        role = stringify_value(item.get("role")).strip()
        entry_value = stringify_value(item.get("value")).strip()
        if not role:
            continue
        normalized_items.append({"role": role, "value": entry_value})
    return normalized_items


def normalize_knowledge_rows(value: Any) -> list[dict[str, str]]:
    items = value if isinstance(value, list) else []
    rows: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        role = stringify_value(item.get("role")).strip()
        if not role:
            continue
        rows.append(
            {
                "role": role,
                "known": stringify_value(item.get("known")).strip(),
                "unknown": stringify_value(item.get("unknown")).strip(),
                "note": stringify_value(item.get("note")).strip(),
            }
        )
    return rows


def normalize_active_hook_rows(value: Any) -> list[dict[str, str]]:
    items = value if isinstance(value, list) else []
    rows: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = stringify_value(item.get("name")).strip()
        if not name:
            continue
        rows.append(
            {
                "name": name,
                "status": stringify_value(item.get("status")).strip(),
                "first_appearance": stringify_value(item.get("first_appearance")).strip(),
                "note": stringify_value(item.get("note")).strip(),
            }
        )
    return rows


def normalize_resolved_hook_rows(value: Any) -> list[dict[str, str]]:
    items = value if isinstance(value, list) else []
    rows: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = stringify_value(item.get("name")).strip()
        if not name:
            continue
        rows.append(
            {
                "name": name,
                "episode": stringify_value(item.get("episode")).strip(),
                "note": stringify_value(item.get("note")).strip(),
            }
        )
    return rows


def render_role_value_lines(items: list[dict[str, str]]) -> list[str]:
    if not items:
        return ["- 暂无：待确认"]
    return [f"- {item['role']}：{item['value'] or '待确认'}" for item in items]


def render_markdown_table_section(headers: list[str], rows: list[list[str]], empty_row: list[str] | None = None) -> list[str]:
    header_line = "| " + " | ".join(headers) + " |"
    divider_line = "| " + " | ".join("-" * len(header) for header in headers) + " |"
    rendered = [header_line, divider_line]
    if rows:
        rendered.extend("| " + " | ".join(cell for cell in row) + " |" for row in rows)
        return rendered
    if empty_row:
        rendered.append("| " + " | ".join(empty_row) + " |")
    return rendered


def remove_section_note(text: str, header: str, note: str, empty_placeholder: str = "- 暂无") -> str:
    existing = extract_section(text, header)
    lines = [line.strip() for line in existing.splitlines() if line.strip()]
    filtered = [line for line in lines if line != note]
    return replace_section(text, header, filtered or [empty_placeholder])


def load_state_diff(diff_path: Path) -> dict[str, Any]:
    if not diff_path.exists():
        raise FileNotFoundError(f"state diff 不存在：{diff_path}")
    try:
        payload = json.loads(diff_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"state diff 不是合法 JSON：{diff_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("state diff 根节点必须是 JSON object。")
    return payload


def collect_known_character_names(project_dir: Path) -> list[str]:
    names: list[str] = []
    character_text = read_text(project_dir / "character-design.md")
    for section_name in ("女主", "男主"):
        section_text = extract_section(character_text, section_name)
        name = extract_labeled_value(section_text, "姓名")
        if not is_placeholder_value(name):
            names.append(name)
    for title, body in supporting_role_cards(character_text):
        role_name = extract_labeled_value(body, "姓名", title)
        if not is_placeholder_value(role_name):
            names.append(role_name)

    role_state_text = read_text(project_dir / "state" / "角色状态.md")
    names.extend(extract_role_state_current_states(role_state_text).keys())
    names.extend(row["role"] for row in extract_role_state_knowledge_rows(role_state_text))
    return unique_preserving_order([name for name in names if not is_placeholder_value(name, ("女主", "男主"))])


def collect_script_speakers(script_text: str) -> list[str]:
    speakers: list[str] = []
    for line in script_text.splitlines():
        match = re.match(r"^\s*([^:\n：]{1,20})[:：]\s*(.+)$", line)
        if not match:
            continue
        speaker = match.group(1).strip().strip("\"' ")
        if speaker == "台词" or speaker.startswith("场景"):
            continue
        if speaker.startswith(("【", "(", "（", "#", "-")):
            continue
        speakers.append(speaker)
    return unique_preserving_order(speakers)


def collect_role_context_lines(script_text: str, role_names: list[str]) -> dict[str, list[str]]:
    contexts = {role_name: [] for role_name in role_names}
    for line in script_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        speaker_match = re.match(r"^\s*([^:\n：]{1,20})[:：]\s*(.+)$", stripped)
        if speaker_match:
            speaker = speaker_match.group(1).strip().strip("\"' ")
            if speaker in contexts:
                contexts[speaker].append(stripped)
        for role_name in role_names:
            if role_name in stripped and stripped not in contexts[role_name]:
                contexts[role_name].append(stripped)
    return contexts


def extract_significant_terms(text: str) -> list[str]:
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    raw_parts = re.split(
        r"\s+|知道什么|绝对不知道什么|当前已知信息|当前服装/造型|当前服装与造型|当前状态|以及|还有|并且|或者|但是|如果|因为|所以|已经|当前|真正|只是|仍然|同时|然后|这个|那个|一个|一些|不会|不能|不要|需要|应该|正在|可能|自己|他们|她们|你们|我们|是|的|了|着|和|与|及|并|在|对|从|将|把|被|让|给",
        normalized,
    )

    terms: list[str] = []
    for raw_part in raw_parts:
        candidate = raw_part.strip()
        if len(candidate) < 2:
            continue
        if candidate.isdigit():
            continue
        if candidate in SIGNIFICANT_TERM_STOPWORDS:
            continue
        if len(candidate) > 12:
            terms.extend(
                piece
                for piece in re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z0-9_-]{2,}", candidate)
                if piece not in SIGNIFICANT_TERM_STOPWORDS
            )
            continue
        terms.append(candidate)
    return unique_preserving_order(terms)


def build_script_consistency_signals(
    script_text: str,
    *,
    title: str,
    core_event: str,
    synopsis_text: str,
    role_state_text: str,
    hook_text: str,
    known_character_names: list[str],
) -> tuple[list[str], dict[str, Any]]:
    warnings: list[str] = []
    knowledge_rows = extract_role_state_knowledge_rows(role_state_text)
    active_hook_rows = extract_active_hook_rows(hook_text)
    active_hook_names = [row["name"] for row in active_hook_rows]
    speakers = collect_script_speakers(script_text)
    unknown_speakers = [speaker for speaker in speakers if speaker not in known_character_names]
    if unknown_speakers:
        warnings.append(f"剧本里出现未登记说话角色：{', '.join(unknown_speakers)}。")

    role_contexts = collect_role_context_lines(script_text, known_character_names)
    knowledge_risks: list[dict[str, Any]] = []
    for row in knowledge_rows:
        role_name = row["role"]
        unknown_text = row["unknown"]
        if is_placeholder_value(unknown_text, ("无", "暂无", "未记录")):
            continue
        role_context = "\n".join(role_contexts.get(role_name, []))
        if not role_context:
            continue
        matched_terms = [term for term in extract_significant_terms(unknown_text) if term in role_context]
        phrase_risk = len(unknown_text) >= 6 and unknown_text in role_context
        if phrase_risk or len(set(matched_terms)) >= 2:
            matched = unique_preserving_order(matched_terms)
            knowledge_risks.append(
                {
                    "role": role_name,
                    "unknown": unknown_text,
                    "matched_terms": matched,
                }
            )

    if knowledge_risks:
        for item in knowledge_risks:
            match_summary = f"；命中词：{', '.join(item['matched_terms'])}" if item["matched_terms"] else ""
            warnings.append(
                f"知情越权风险：{item['role']} 在剧本里触及其“绝对不知道什么”里的内容：{item['unknown']}{match_summary}。"
            )

    mentioned_hooks = [hook_name for hook_name in active_hook_names if hook_name and hook_name in script_text]
    if active_hook_names and not mentioned_hooks:
        warnings.append("当前剧本没有直接提到任何活跃伏笔名称，注意检查是否把长期钩子写丢了。")

    target_terms = extract_significant_terms(" ".join(item for item in [title, core_event, synopsis_text] if item))
    matched_target_terms = [term for term in target_terms if term in script_text]
    if target_terms and len(set(matched_target_terms)) < min(2, len(set(target_terms))):
        warnings.append("当前剧本与本集标题 / 核心事件 / 分集梗概的显式重合很低，注意检查是否已经偏离本集目标。")

    mentioned_roles = [role_name for role_name in known_character_names if role_name in script_text]

    return warnings, {
        "scene_headers": [header for header, _ in split_scene_blocks(script_text)],
        "speakers": speakers,
        "unknown_speakers": unknown_speakers,
        "mentioned_roles": mentioned_roles,
        "active_hook_names": active_hook_names,
        "mentioned_active_hooks": mentioned_hooks,
        "target_terms": target_terms,
        "matched_target_terms": unique_preserving_order(matched_target_terms),
        "knowledge_risks": knowledge_risks,
    }


def build_consistency_report(
    project_dir: Path,
    episode_num: int,
    title: str,
    core_event: str,
    *,
    script_text: str = "",
) -> dict[str, Any]:
    blockers, warnings = collect_episode_context_issues(
        project_dir,
        episode_num,
        title,
        core_event,
        require_plan=False,
    )

    role_state_text = read_text(project_dir / "state" / "角色状态.md")
    hook_text = read_text(project_dir / "state" / "伏笔列表.md")
    synopsis_text = extract_episode_synopsis(project_dir, episode_num)
    known_character_names = collect_known_character_names(project_dir)

    script_warnings: list[str] = []
    script_signals: dict[str, Any] = {
        "scene_headers": [],
        "speakers": [],
        "unknown_speakers": [],
        "mentioned_roles": [],
        "active_hook_names": [row["name"] for row in extract_active_hook_rows(hook_text)],
        "mentioned_active_hooks": [],
        "target_terms": [],
        "matched_target_terms": [],
        "knowledge_risks": [],
    }
    if script_text:
        script_warnings, script_signals = build_script_consistency_signals(
            script_text,
            title=title,
            core_event=core_event,
            synopsis_text=synopsis_text,
            role_state_text=role_state_text,
            hook_text=hook_text,
            known_character_names=known_character_names,
        )

    return {
        "episode_num": episode_num,
        "title": title,
        "core_event": core_event,
        "errors": blockers,
        "warnings": [*warnings, *script_warnings],
        "context": {
            "known_characters": known_character_names,
            "active_hooks": extract_active_hook_rows(hook_text),
            "knowledge_rows": extract_role_state_knowledge_rows(role_state_text),
            "synopsis_excerpt": synopsis_text,
        },
        "script_signals": script_signals,
    }


def print_consistency_report(
    project_dir: Path,
    script_path: Path | None,
    report: dict[str, Any],
) -> None:
    print(f"检查项目：{project_dir}")
    print(f"- 当前集：第{report['episode_num']}集《{report['title']}》")
    if report["core_event"]:
        print(f"- 核心事件：{report['core_event']}")
    if script_path:
        print(f"- 剧本文件：{script_path}")

    known_characters = report["context"]["known_characters"]
    if known_characters:
        print(f"- 已登记角色：{', '.join(known_characters)}")

    active_hook_names = [row["name"] for row in report["context"]["active_hooks"]]
    if active_hook_names:
        print(f"- 活跃伏笔：{', '.join(active_hook_names)}")

    speakers = report["script_signals"]["speakers"]
    if speakers:
        print(f"- 剧本说话角色：{', '.join(speakers)}")

    mentioned_hooks = report["script_signals"]["mentioned_active_hooks"]
    if mentioned_hooks:
        print(f"- 剧本命中的活跃伏笔：{', '.join(mentioned_hooks)}")

    if report["errors"]:
        print("\n错误：")
        for item in report["errors"]:
            print(f"- {item}")
    if report["warnings"]:
        print("\n警告：")
        for item in report["warnings"]:
            print(f"- {item}")

    if not report["errors"] and not report["warnings"]:
        print("\n检查通过。")


def build_state_diff_payload(
    project_dir: Path,
    episode_num: int,
    archived_script_path: Path,
    *,
    title: str,
    core_event: str,
    summary: str,
    quality_report: dict[str, Any],
    consistency_report: dict[str, Any],
) -> dict[str, Any]:
    task_log = read_text(project_dir / "task_log.md")
    next_title, next_core_event = lookup_episode_outline(project_dir, episode_num + 1)
    next_target = ""
    if next_title:
        next_target = f"第{episode_num + 1}集《{next_title}》"
        if next_core_event:
            next_target += f" / {next_core_event}"

    role_state_note = f"- 第{episode_num}集《{title}》：根据已交付剧本确认角色知情、关系与造型变化。摘要：{summary}"
    hook_state_note = f"- 第{episode_num}集《{title}》：根据已交付剧本确认伏笔新增、推进或回收。摘要：{summary}"
    active_hook_names = [row["name"] for row in consistency_report["context"]["active_hooks"]]
    mentioned_active_hooks = consistency_report["script_signals"]["mentioned_active_hooks"]
    manual_review_items = [
        "核对知情越权风险，确认是否真有角色说出了不该知道的信息。",
        "根据剧本实际结果，手动更新 `state/角色状态.md` 的知情、关系与造型字段。",
        "根据剧本实际结果，手动更新 `state/伏笔列表.md` 的新增 / 推进 / 回收状态。",
    ]
    if active_hook_names:
        if mentioned_active_hooks:
            manual_review_items.append(f"优先复核这些已命中的活跃伏笔：{', '.join(mentioned_active_hooks)}。")
        else:
            manual_review_items.append("本集没有直接命中活跃伏笔名称，确认是否存在隐性推进或遗漏回收。")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "episode_num": episode_num,
        "title": title,
        "core_event": core_event,
        "summary": summary,
        "archived_script": str(archived_script_path.relative_to(project_dir)),
        "script_signals": {
            "scene_headers": consistency_report["script_signals"]["scene_headers"],
            "speakers": consistency_report["script_signals"]["speakers"],
            "mentioned_roles": consistency_report["script_signals"]["mentioned_roles"],
            "active_hook_names": active_hook_names,
            "mentioned_active_hooks": mentioned_active_hooks,
            "unknown_speakers": consistency_report["script_signals"]["unknown_speakers"],
            "knowledge_risks": consistency_report["script_signals"]["knowledge_risks"],
            "quality": {
                "effective_chars": quality_report["effective_chars"],
                "scene_count": len(quality_report["scene_blocks"]),
                "total_dialogue_lines": quality_report["total_dialogue_lines"],
                "dialogue_counts": quality_report["dialogue_counts"],
                "risk_word_counts": quality_report["risk_word_counts"],
            },
        },
        "consistency_report": {
            "errors": consistency_report["errors"],
            "warnings": consistency_report["warnings"],
        },
        "proposed_updates": {
            "task_log": {
                "创作阶段": f"已完成第{episode_num}集",
                "最新完成集": f"第{episode_num}集《{title}》",
                "当前处理集": "无",
                "最近交付文件": archived_script_path.name,
                "下一集目标": next_target or extract_task_field(task_log, "下一集目标"),
            },
            "history_row": {
                "episode": episode_num,
                "title": title,
                "status": "已完成",
                "core_event": core_event or "待补充",
                "summary": summary,
            },
            "pending_notes": {
                "role_state": role_state_note,
                "hook_state": hook_state_note,
            },
        },
        "editable_updates": {
            "role_state": {
                "current_states": [
                    {"role": role, "value": value}
                    for role, value in extract_role_state_current_states(read_text(project_dir / "state" / "角色状态.md")).items()
                ],
                "knowledge_rows": extract_role_state_knowledge_rows(read_text(project_dir / "state" / "角色状态.md")),
                "wardrobe": [
                    {"role": role, "value": value}
                    for role, value in extract_role_state_wardrobe(read_text(project_dir / "state" / "角色状态.md")).items()
                ],
            },
            "hook_state": {
                "active_hooks": extract_active_hook_rows(read_text(project_dir / "state" / "伏笔列表.md")),
                "resolved_hooks": extract_resolved_hook_rows(read_text(project_dir / "state" / "伏笔列表.md")),
            },
            "pending_notes": {
                "remove_role_state_note": True,
                "remove_hook_state_note": True,
            },
        },
        "manual_review": {
            "checklist": manual_review_items,
        },
    }


def state_diff_output_path(project_dir: Path, episode_num: int) -> Path:
    return project_dir / "state" / "pending" / f"episode-{episode_num:04d}.state-diff.json"


def write_state_diff(project_dir: Path, episode_num: int, payload: dict[str, Any]) -> Path:
    output_path = state_diff_output_path(project_dir, episode_num)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def command_apply_state_diff(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    diff_path = Path(args.diff_file).resolve() if args.diff_file else state_diff_output_path(project_dir, args.episode_num)
    try:
        payload = load_state_diff(diff_path)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return 1

    if int(payload.get("episode_num", 0)) != args.episode_num:
        print(f"Apply-state-diff 失败：diff 集数与命令参数不一致。diff={payload.get('episode_num')}，命令={args.episode_num}")
        return 1

    editable_updates = payload.get("editable_updates")
    proposed_updates = payload.get("proposed_updates")
    if not isinstance(editable_updates, dict) or not isinstance(proposed_updates, dict):
        print("Apply-state-diff 失败：diff 缺少 `editable_updates` 或 `proposed_updates`。")
        return 1

    role_state_updates = editable_updates.get("role_state") if isinstance(editable_updates.get("role_state"), dict) else {}
    hook_state_updates = editable_updates.get("hook_state") if isinstance(editable_updates.get("hook_state"), dict) else {}
    pending_notes_updates = editable_updates.get("pending_notes") if isinstance(editable_updates.get("pending_notes"), dict) else {}
    pending_notes = proposed_updates.get("pending_notes") if isinstance(proposed_updates.get("pending_notes"), dict) else {}

    role_state_path = project_dir / "state" / "角色状态.md"
    hook_state_path = project_dir / "state" / "伏笔列表.md"
    if not role_state_path.exists() or not hook_state_path.exists():
        print("Apply-state-diff 失败：缺少状态文件。")
        return 1

    role_state_text = read_text(role_state_path)
    hook_state_text = read_text(hook_state_path)

    current_state_items = normalize_role_value_items(role_state_updates.get("current_states"))
    knowledge_rows = normalize_knowledge_rows(role_state_updates.get("knowledge_rows"))
    wardrobe_items = normalize_role_value_items(role_state_updates.get("wardrobe"))
    active_hook_rows = normalize_active_hook_rows(hook_state_updates.get("active_hooks"))
    resolved_hook_rows = normalize_resolved_hook_rows(hook_state_updates.get("resolved_hooks"))

    role_state_text = replace_section(role_state_text, "当前集后状态", render_role_value_lines(current_state_items))
    role_state_text = replace_section(
        role_state_text,
        "知情状态表",
        render_markdown_table_section(
            ["角色", "知道什么", "绝对不知道什么", "备注"],
            [[row["role"], row["known"], row["unknown"], row["note"]] for row in knowledge_rows],
            empty_row=["", "", "", ""],
        ),
    )
    role_state_text = replace_section(role_state_text, "当前服装与造型", render_role_value_lines(wardrobe_items))

    hook_state_text = replace_section(
        hook_state_text,
        "活跃伏笔",
        render_markdown_table_section(
            ["伏笔名称", "当前状态", "首次出现", "备注"],
            [[row["name"], row["status"], row["first_appearance"], row["note"]] for row in active_hook_rows],
        ),
    )
    hook_state_text = replace_section(
        hook_state_text,
        "已回收伏笔",
        render_markdown_table_section(
            ["伏笔名称", "回收集数", "备注"],
            [[row["name"], row["episode"], row["note"]] for row in resolved_hook_rows],
        ),
    )

    if pending_notes_updates.get("remove_role_state_note") and pending_notes.get("role_state"):
        role_state_text = remove_section_note(role_state_text, "待确认回写", stringify_value(pending_notes.get("role_state")))
    if pending_notes_updates.get("remove_hook_state_note") and pending_notes.get("hook_state"):
        hook_state_text = remove_section_note(hook_state_text, "待确认回写", stringify_value(pending_notes.get("hook_state")))

    role_state_backup = backup_file(role_state_path)
    hook_state_backup = backup_file(hook_state_path)
    role_state_path.write_text(role_state_text, encoding="utf-8")
    hook_state_path.write_text(hook_state_text, encoding="utf-8")

    print("已应用 state diff：")
    print(f"- diff：{diff_path}")
    print(f"- {role_state_path}")
    print(f"- {hook_state_path}")
    print("已备份：")
    print(f"- {role_state_backup}")
    print(f"- {hook_state_backup}")
    return 0


def extract_shot_table_section(text: str) -> str:
    match = re.search(r"(?ms)^## (?:5秒镜头单元表|镜头拆分表)\n(.*?)(?=^## |\Z)", text)
    return match.group(1).strip() if match else ""


def extract_scene_body_without_shot_table(text: str) -> str:
    return re.sub(r"(?ms)\n## (?:5秒镜头单元表|镜头拆分表)\n.*$", "", text).strip()


def extract_scene_brief_text(text: str) -> str:
    brief_section = extract_section(text, "当前场摘要")
    if brief_section:
        return brief_section.strip()
    return extract_scene_body_without_shot_table(text)


def parse_shot_index(value: str) -> int | None:
    match = re.search(r"(\d+)", value)
    return int(match.group(1)) if match else None


def parse_shot_plan_rows(scene_text: str) -> list[dict[str, str]]:
    section = extract_shot_table_section(scene_text)
    if not section:
        return []

    rows = parse_markdown_table_rows(
        section,
        header_patterns=("| 镜头 |", "| 分镜 |", "| Shot |"),
    )
    parsed_rows: list[dict[str, str]] = []
    for cells in rows:
        if len(cells) < 6:
            continue
        shot_num = parse_shot_index(cells[0])
        if shot_num is None:
            continue
        parsed_rows.append(
            {
                "shot": str(shot_num),
                "seconds": cells[1],
                "goal": cells[2],
                "action": cells[3],
                "dialogue": cells[4],
                "bridge": cells[5],
            }
        )
    return parsed_rows


def parse_time_span_seconds(value: str) -> tuple[int | None, int | None, int | None]:
    normalized = value.strip()
    range_match = re.search(r"(\d+)\s*-\s*(\d+)\s*(?:秒|s|S)?", normalized)
    if range_match:
        start_second = int(range_match.group(1))
        end_second = int(range_match.group(2))
        return start_second, end_second, max(0, end_second - start_second)

    point_match = re.fullmatch(r"(\d+)\s*(?:秒|s|S)", normalized)
    if point_match:
        duration_second = int(point_match.group(1))
        return 0, duration_second, duration_second

    return None, None, None


def validate_shot_plan_rows(shot_rows: list[dict[str, str]], shot_seconds: int) -> list[str]:
    issues: list[str] = []
    if not shot_rows:
        return ["镜头拆分表为空。"]

    expected_shot_num = 1
    expected_start_second = 0
    for row in shot_rows:
        shot_num = int(row["shot"])
        if shot_num != expected_shot_num:
            issues.append(f"镜头编号不连续：期望镜头{expected_shot_num}，实际是镜头{shot_num}。")
            expected_shot_num = shot_num

        start_second, end_second, duration_second = parse_time_span_seconds(row["seconds"])
        if start_second is None or end_second is None or duration_second is None:
            issues.append(
                f"镜头{shot_num} 的秒数格式不合法：`{row['seconds']}`。必须写成 `0-5秒 / 5-10秒` 这种连续区间。"
            )
        else:
            if start_second != expected_start_second:
                issues.append(
                    f"镜头{shot_num} 起始秒不连续：期望从 {expected_start_second} 秒开始，实际是 {start_second} 秒。"
                )
            if duration_second != shot_seconds:
                issues.append(
                    f"镜头{shot_num} 不是严格 {shot_seconds} 秒：当前是 `{row['seconds']}`。"
                )
            expected_start_second = end_second

        expected_shot_num += 1

    return issues


def validate_scene_brief_text(scene_text: str) -> list[str]:
    issues: list[str] = []
    if "## 当前场摘要" not in scene_text:
        issues.append("缺少 `## 当前场摘要` 小节。")

    brief_text = extract_scene_brief_text(scene_text)
    brief_lines = [line.strip() for line in brief_text.splitlines() if line.strip()]
    if len(brief_lines) < 4:
        issues.append("当前场摘要过短，至少保留 4 行短条目。")
    if len(brief_lines) > 8:
        issues.append("当前场摘要过长，说明你又在往长场景正文方向滑。")

    forbidden_patterns = (
        (r"(?m)^场景\d+:\s*", "摘要里出现了 `场景X:` 长场景标题。"),
        (r"(?m)^\(主体\)", "摘要里出现了 `(主体)`，说明混入了镜头正文。"),
        (r"(?m)^\(环境\)", "摘要里出现了 `(环境)`，说明混入了镜头正文。"),
        (r"(?m)^\(动作\)", "摘要里出现了 `(动作)`，说明混入了镜头正文。"),
        (r"(?m)^\(光影\)", "摘要里出现了 `(光影)`，说明混入了镜头正文。"),
        (r"(?m)^\(镜头\)", "摘要里出现了 `(镜头)`，说明混入了镜头正文。"),
        (r"(?m)^\(画质\)", "摘要里出现了 `(画质)`，说明混入了镜头正文。"),
        (r"(?m)^台词:\s*$", "摘要里出现了 `台词:`，说明混入了长场景对白。"),
        (r"(?m)^【环境空镜", "摘要里出现了 `【环境空镜】`，说明混入了长场景正文。"),
    )
    for pattern, message in forbidden_patterns:
        if re.search(pattern, brief_text):
            issues.append(message)

    dialogue_line_count = len(DIALOGUE_LINE_PATTERN.findall(brief_text))
    if dialogue_line_count > 0:
        issues.append("当前场摘要里出现了角色对白行，说明你写成了场景正文。")

    return issues


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
    *,
    require_plan: bool = True,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if is_placeholder_value(title):
        blockers.append("当前集标题为空，请在 linenew.md 或 `--title` 中补齐。")
    if is_placeholder_value(core_event):
        blockers.append("当前集核心事件为空，请在 linenew.md 或 `--core-event` 中补齐。")

    plan_path = plan_path_for_episode(project_dir, episode_num)
    if require_plan and not plan_path.exists():
        blockers.append(f"未找到场景卡：{plan_path.relative_to(project_dir)}。请先运行 `plan`。")

    history_rows = parse_history_rows(read_text(project_dir / "state" / "剧集历史.md"))
    previous_row = find_history_row(history_rows, episode_num - 1) if episode_num > 1 else None
    if episode_num > 1 and not previous_row:
        blockers.append(f"state/剧集历史.md 还没有第{episode_num - 1}集记录，无法稳定续写第{episode_num}集。")
    if previous_row and previous_row["status"] not in COMPLETED_STATUSES:
        blockers.append(f"第{episode_num - 1}集尚未标记为已完成，先别直接续写第{episode_num}集。")
    if episode_num > 1 and not find_episode_script(project_dir, episode_num - 1):
        blockers.append(f"未找到第{episode_num - 1}集剧本文件，不能只靠历史摘要硬续写第{episode_num}集。")

    synopsis_text = extract_episode_synopsis(project_dir, episode_num)
    if episode_num > 1 and not synopsis_text:
        blockers.append(f"docs/分集梗概.md 中未找到第{episode_num}集有效小节，先补分集梗概再续写。")
    elif not synopsis_text:
        warnings.append(f"docs/分集梗概.md 中未找到第{episode_num}集有效小节，将只使用 linenew.md 核心事件。")

    hook_text = read_text(project_dir / "state" / "伏笔列表.md")
    has_active_hooks = has_nonempty_table_rows(extract_section(hook_text, "活跃伏笔"))
    if episode_num > 1 and not has_active_hooks:
        blockers.append("state/伏笔列表.md 暂无活跃伏笔记录，第 2 集后不能在空钩子状态下硬续写。")
    elif not has_active_hooks:
        warnings.append("state/伏笔列表.md 暂无活跃伏笔记录。首轮创作后建议尽快补齐。")

    if episode_num > 1:
        blockers.extend(supporting_role_context_issues(read_text(project_dir / "character-design.md")))

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
    project_dir = create_drama_project(
        args.project_name,
        Path(args.path).resolve(),
        seed_data=args.seed_data,
        overwrite=args.force,
    )
    print(project_dir)
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    missing, blockers, warnings = collect_preflight_report(project_dir)
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
    ready, warnings = ensure_preflight_ready(project_dir, "Resume")
    if not ready:
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
    ready, _ = ensure_preflight_ready(project_dir, "Plan")
    if not ready:
        return 1
    title, core_event = resolve_episode_meta(project_dir, args.episode_num, args.title, args.core_event)
    blockers, warnings = collect_episode_context_issues(
        project_dir,
        args.episode_num,
        title,
        core_event,
        require_plan=False,
    )
    if blockers:
        print("Plan 失败：")
        for item in blockers:
            print(f"- {item}")
        return 1
    if warnings:
        print("Plan 提醒：")
        for item in warnings:
            print(f"- {item}")
    runtime_path = plan_output_path_for_episode(project_dir, args.episode_num)
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


def build_reference_excerpt(project_dir: Path, relative_path: str, heading_queries: tuple[str, ...]) -> list[str]:
    reference_path = project_dir / relative_path
    if not reference_path.exists():
        reference_path = REPO_ROOT / relative_path
    text = read_text(reference_path)
    if not text:
        return []

    lines: list[str] = []
    for heading_query in heading_queries:
        section = extract_section_by_heading_query(text, heading_query)
        if not section:
            continue
        lines.extend(
            [
                f"[{relative_path} / {heading_query}]",
                section,
                "",
            ]
        )
    return lines[:-1] if lines else []


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
    few_shot_lines = build_reference_excerpt(
        project_dir,
        "references/good-vs-bad-examples.md",
        ("小说化 vs 可拍", "无效对白 vs 有功能对白", "软卡点 vs 狠卡点"),
    )
    repair_lines = build_reference_excerpt(
        project_dir,
        "references/repair-strategies.md",
        ("对白弱", "卡点软", "小说化"),
    )

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

    if few_shot_lines:
        prompt_lines.extend(
            [
                "",
                "## Few-shot 对照",
                *few_shot_lines,
            ]
        )

    if repair_lines:
        prompt_lines.extend(
            [
                "",
                "## 定向返修策略",
                *repair_lines,
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
    few_shot_lines = build_reference_excerpt(
        project_dir,
        "references/good-vs-bad-examples.md",
        ("小说化 vs 可拍", "软卡点 vs 狠卡点"),
    )
    repair_lines = build_reference_excerpt(
        project_dir,
        "references/repair-strategies.md",
        ("节奏拖", "小说化"),
    )

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

    if few_shot_lines:
        prompt_lines.extend(
            [
                "",
                "## Few-shot 对照",
                *few_shot_lines,
            ]
        )

    if repair_lines:
        prompt_lines.extend(
            [
                "",
                "## 定向返修策略",
                *repair_lines,
            ]
        )

    prompt_lines.extend(
        [
            "",
            "## 分场要求",
            "- 只输出当前这一场的规划稿，不要写完整场景剧本，不要把后续场景提前写出来。",
            "- 这一层只负责产出“当前场摘要 + 严格 5 秒镜头表”，不负责写 40 秒、60 秒的长场景正文。",
            "- 当前场摘要只保留地点、人物、目标、冲突、出场变化，必须短，不能写成长块对白和动作。",
            "- 本场内部也要完成“目标 -> 阻碍 -> 变化”三步，但要拆进镜头表里，不要堆成一个长场景块。",
            f"- 本场结尾：{bridge_hint}",
            f"- 每个镜头单元必须严格等于 {shot_seconds} 秒，不是“大约 {shot_seconds} 秒”。",
            "- 镜头表必须写成连续时间段：`0-5秒`、`5-10秒`、`10-15秒`……不允许 `0-8秒`、`约5秒`、`5秒左右` 这种写法。",
            "- 每个镜头单元只允许 1 个主要动作节拍 + 最多 1 句台词；如果要连续做两件关键事，就拆成两个镜头文件。",
            "- 宁可缩短 `(光影)/(镜头)/(画质)` 修饰词，也不要把动作、反转和对白压没。",
            "- 禁止输出 `场景1: 地点(0-40秒)` 这种长场景正文；一旦写出这种东西，视为失败。",
            "",
            "## 输出格式",
            f"1. 先输出 `## 当前场摘要`，只写 4-6 行短条目。",
            "2. `## 当前场摘要` 建议字段：地点 / 人物 / 入场状态 / 当前场目标 / 当前场冲突 / 出场变化。",
            "3. 然后输出 `## 5秒镜头单元表`。",
            f"4. `## 5秒镜头单元表` 必须拆成约 {video_unit_count} 行，且每行必须严格 {shot_seconds} 秒。",
            "5. 单元表列建议：镜头 | 秒数 | 画面目标 | 人物/动作 | 台词/口型 | 承上启下。",
            "6. 每个镜头单元都要能直接喂给 5 秒视频工具，不要写成抽象总结；每行都要写清具体起点动作、画面结果和口型内容。",
            "7. 一行里如果出现两个以上并列动作，视为拆分失败，必须继续拆细。",
            f"8. 生成结果默认保存到 `runtime/episode-{episode_num:04d}/scene-{scene_num:02d}/scene.md`。",
            "9. 不要输出完整场景剧本，不要输出 `场景X:` 长正文，不要输出解释说明。",
            "10. 如果你发现自己开始写 `(主体)/(动作)/台词:` 这种完整场景块，立刻停下，删掉，改回摘要条目。",
            "",
            "## 唯一允许骨架",
            "```md",
            "## 当前场摘要",
            "- 地点：",
            "- 人物：",
            "- 入场状态：",
            "- 当前场目标：",
            "- 当前场冲突：",
            "- 出场变化：",
            "",
            "## 5秒镜头单元表",
            "| 镜头 | 秒数 | 画面目标 | 人物/动作 | 台词/口型 | 承上启下 |",
            "|------|------|----------|-----------|-----------|----------|",
            f"| 1 | 0-{shot_seconds}秒 | ... | ... | ... | ... |",
            "```",
            "",
            "## 错误示例",
            "下面这种输出是错的，禁止出现：",
            "```md",
            "场景1: 食堂(0-40秒)",
            "【环境空镜3s】...",
            "(主体)...",
            "台词:",
            "角色A:\"...\"",
            "```",
            "",
            "## 生成前自检",
            "- 当前场是否真的发生了升级，而不是停在“发现线索”？",
            "- 你有没有误写成长场景正文？如果有，删掉，只保留摘要和镜头表。",
            f"- 镜头单元表是否严格是 `{shot_seconds}` 秒一格的连续切片，不会出现 8 秒、10 秒这种长镜头？",
        ]
    )
    return "\n".join(prompt_lines).rstrip() + "\n"


def build_shot_plan_excerpt(shot_rows: list[dict[str, str]], shot_num: int) -> list[str]:
    selected_rows = [
        row for row in shot_rows if abs(int(row["shot"]) - shot_num) <= 1
    ]
    lines = [
        "| 镜头 | 秒数 | 画面目标 | 人物/动作 | 台词/口型 | 承上启下 |",
        "|------|------|----------|-----------|-----------|----------|",
    ]
    for row in selected_rows:
        marker = " <- 当前镜头" if int(row["shot"]) == shot_num else ""
        lines.append(
            f"| {row['shot']} | {row['seconds']} | {row['goal']} | {row['action']} | {row['dialogue']} | {row['bridge']}{marker} |"
        )
    return lines


def build_shot_prompt_pack(
    project_dir: Path,
    episode_num: int,
    scene_num: int,
    shot_num: int,
    title: str,
    core_event: str,
    scene_path: Path,
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
    current_scene_row = next((row for row in scene_rows if int(row["scene"]) == scene_num), None)
    if not current_scene_row:
        raise ValueError(f"未在场景卡中找到场景{scene_num}")

    scene_text = read_text(scene_path).strip()
    shot_rows = parse_shot_plan_rows(scene_text)
    current_shot_row = next((row for row in shot_rows if int(row["shot"]) == shot_num), None)
    if not current_shot_row:
        raise ValueError(f"未在 `{scene_path.name}` 中找到镜头{shot_num} 的拆分表行")

    scene_brief = extract_scene_brief_text(scene_text)
    try:
        scene_display_path = scene_path.relative_to(project_dir)
    except ValueError:
        scene_display_path = scene_path
    previous_scene_path = find_scene_output_file(project_dir, episode_num, scene_num - 1) if scene_num > 1 else None
    previous_scene_excerpt = tail_excerpt(read_text(previous_scene_path), max_chars=1000) if previous_scene_path else ""
    previous_shot_outputs = {current_num: path for current_num, path in find_shot_output_files(project_dir, episode_num, scene_num)}
    previous_shot_path = previous_shot_outputs.get(shot_num - 1)
    previous_shot_excerpt = tail_excerpt(read_text(previous_shot_path), max_chars=900) if previous_shot_path else ""
    few_shot_lines = build_reference_excerpt(
        project_dir,
        "references/good-vs-bad-examples.md",
        ("小说化 vs 可拍", "无效对白 vs 有功能对白"),
    )
    repair_lines = build_reference_excerpt(
        project_dir,
        "references/repair-strategies.md",
        ("对白弱", "小说化"),
    )

    scene_header = f"场景{scene_num}"
    scene_summary_lines = [line.strip() for line in scene_brief.splitlines() if line.strip()]
    scene_summary = " / ".join(scene_summary_lines[:3])
    bridge_hint = (
        "镜头结尾必须稳住本场强卡点，不要再额外发散。"
        if shot_num == len(shot_rows)
        else f"镜头结尾必须把压力明确交给镜头{shot_num + 1}。"
    )

    prompt_lines = [
        "你正在为平台向微短剧生成单镜头内容。当前工具一次只处理一个镜头，禁止把多个镜头糊成一个长段。",
        "",
        "## 核心配置",
        *sections,
        "",
        "## 当前任务",
        f"- 当前只写：第{episode_num}集《{title}》 / 场景{scene_num} / 镜头{shot_num}",
        f"- 本集核心事件：{core_event or '待补充'}",
        f"- 当前场目标秒数：{current_scene_row['target_seconds']}",
        f"- 当前场入场局势：{current_scene_row['entry_state']}",
        f"- 当前镜头秒数：{current_shot_row['seconds']}",
        f"- 当前镜头画面目标：{current_shot_row['goal']}",
        f"- 当前镜头人物/动作：{current_shot_row['action']}",
        f"- 当前镜头台词/口型：{current_shot_row['dialogue']}",
        f"- 当前镜头承接：{current_shot_row['bridge']}",
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
        "## 当前场景卡",
        *build_scene_plan_excerpt(scene_rows, scene_num),
        "",
        "## 邻近镜头拆分表",
        *build_shot_plan_excerpt(shot_rows, shot_num),
        "",
        f"- 当前场参考文件：{scene_display_path}",
        f"- 当前场标题：{scene_header or f'场景{scene_num}'}",
        f"- 当前场摘要：{scene_summary or '以当前镜头行和场景卡为准，不要扩成整场。'}",
    ]

    if previous_scene_excerpt:
        prompt_lines.extend(
            [
                "",
                f"[上一场尾段: {previous_scene_path.relative_to(project_dir)}]",
                previous_scene_excerpt,
            ]
        )

    if previous_shot_excerpt:
        prompt_lines.extend(
            [
                "",
                f"[上一镜头结果: {previous_shot_path.relative_to(project_dir)}]",
                previous_shot_excerpt,
            ]
        )

    if few_shot_lines:
        prompt_lines.extend(
            [
                "",
                "## Few-shot 对照",
                *few_shot_lines,
            ]
        )

    if repair_lines:
        prompt_lines.extend(
            [
                "",
                "## 定向返修策略",
                *repair_lines,
            ]
        )

    prompt_lines.extend(
        [
            "",
            "## 单镜头要求",
            "- 只覆盖当前这一镜头，不要偷写下一个镜头的动作结果。",
            "- 这是严格 5 秒镜头，只允许 1 个主要动作节拍；如果需要第二个关键动作，就说明上一层拆分失败，不能在这里硬塞。",
            "- 只细化当前镜头的表情、道具交互、机位、运动方式和口型，不要重新扩成整场或整集。",
            "- 当前镜头台词最多 1 句；如果需要第二句对白，拆到下一个镜头。",
            "- 如果当前镜头没有台词，也要明确口型为空、动作承担推进。",
            f"- {bridge_hint}",
            "- 宁可把一个动作拆细，也不要把两个节拍压进同一句抽象总结。",
            "- 输出文本总量控制在一个短镜头能承载的颗粒度，不要写成长段分镜小说。",
            "",
            "## 输出格式",
            f"1. 只输出 `镜头{shot_num}:` 这一镜头。",
            f"2. 标题建议：`镜头{shot_num}: {scene_header or f'场景{scene_num}'}({current_shot_row['seconds']})`。",
            "3. 正文结构：`(主体)` / `(环境)` / `(动作)` / `(光影)` / `(镜头)` / `(画质)` / `台词:`。",
            "4. `(动作)` 只写当前 5 秒内的起点动作和结束状态，不要写下一个镜头的结果。",
            "5. 台词只保留当前镜头真正会说出的 0-1 句，不要偷带后续镜头内容。",
            f"6. 生成结果默认保存到 `runtime/episode-{episode_num:04d}/scene-{scene_num:02d}/shot-{shot_num:03d}.md`。",
            "7. 不要输出解释，不要输出其他镜头。",
            "",
            "## 生成前自检",
            "- 这个镜头单独拿出来，观众能看懂它的动作目标和结果吗？",
            "- 这个镜头有没有偷偷吃掉下一个镜头的剧情？",
            "- 这个镜头的台词、表情、机位是否都服务于当前 5 秒，而不是泛泛补描写？",
            "- 这个镜头里是否只剩 1 个主要动作节拍，而不是 2-3 个节拍串在一起？",
        ]
    )
    return "\n".join(prompt_lines).rstrip() + "\n"


def command_compose(args: argparse.Namespace) -> int:
    if not getattr(args, "allow_full_episode", False):
        print("Compose 已默认禁用：当前工作流不再允许一次性生成整集剧本。")
        print("请改用以下链路：")
        print("- `plan` 生成场景卡")
        print("- `compose-scenes` 生成单场规划 prompt")
        print("- `compose-shots` 从单场规划里逐镜头生成 prompt")
        print("如果你确实要手动触发整集输出，必须显式传 `--allow-full-episode`。")
        return 1

    project_dir = ensure_project_dir(Path(args.project_dir))
    ready, _ = ensure_preflight_ready(project_dir, "Compose")
    if not ready:
        return 1
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
    prompt_path = prompt_output_path_for_episode(project_dir, args.episode_num)
    update_task_log_status(project_dir, args.episode_num, title, "单集创作中")
    prompt_path.write_text(
        build_prompt_pack(project_dir, args.episode_num, title, core_event, args.target_duration),
        encoding="utf-8",
    )
    print(prompt_path)
    return 0


def command_compose_scenes(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    ready, _ = ensure_preflight_ready(project_dir, "Compose-scenes")
    if not ready:
        return 1
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

    selected_scene_num = args.scene_num if args.scene_num is not None else next_missing_scene_num(project_dir, args.episode_num, available_scene_nums)
    generated_paths: list[Path] = []
    update_task_log_status(project_dir, args.episode_num, title, f"分场创作中 / 场景{selected_scene_num}")
    prompt_path = scene_prompt_output_path_for_episode(project_dir, args.episode_num, selected_scene_num)
    prompt_path.write_text(
        build_scene_prompt_pack(
            project_dir,
            args.episode_num,
            selected_scene_num,
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


def command_compose_shots(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    ready, _ = ensure_preflight_ready(project_dir, "Compose-shots")
    if not ready:
        return 1
    title, core_event = resolve_episode_meta(project_dir, args.episode_num, args.title, args.core_event)
    blockers, warnings = collect_episode_context_issues(project_dir, args.episode_num, title, core_event)
    if blockers:
        print("Compose-shots 失败：")
        for item in blockers:
            print(f"- {item}")
        return 1
    if warnings:
        print("Compose-shots 提醒：")
        for item in warnings:
            print(f"- {item}")

    scene_path = Path(args.scene_file).resolve() if args.scene_file else find_scene_output_file(project_dir, args.episode_num, args.scene_num)
    if not scene_path or not scene_path.exists():
        expected_path = scene_output_path_for_episode(project_dir, args.episode_num, args.scene_num)
        print("Compose-shots 失败：未找到当前场的正文文件。")
        print(f"请先生成并保存场景结果，例如：{expected_path}")
        return 1

    shot_rows = parse_shot_plan_rows(read_text(scene_path))
    if not shot_rows:
        print("Compose-shots 失败：当前场正文里没有可解析的 `## 5秒镜头单元表` 或 `## 镜头拆分表`。")
        return 1

    scene_brief_issues = validate_scene_brief_text(read_text(scene_path))
    if scene_brief_issues:
        print("Compose-shots 失败：当前场文件不是合格的场景规划稿，仍然混入了长场景正文。")
        for item in scene_brief_issues:
            print(f"- {item}")
        print("请把 `scene.md` 改成“当前场摘要 + 5秒镜头表”后再继续。")
        return 1

    shot_plan_issues = validate_shot_plan_rows(shot_rows, args.shot_seconds)
    if shot_plan_issues:
        print("Compose-shots 失败：当前场的镜头拆分表不满足严格 5 秒分镜规则。")
        for item in shot_plan_issues:
            print(f"- {item}")
        print("请先重写当前场的镜头拆分表，再继续生成单镜头文件。")
        return 1

    available_shot_nums = [int(row["shot"]) for row in shot_rows]
    if args.shot_num is not None and args.shot_num not in available_shot_nums:
        print(f"Compose-shots 失败：镜头{args.shot_num} 不在当前场的镜头拆分表里。")
        return 1

    selected_shot_num = args.shot_num if args.shot_num is not None else next_missing_shot_num(project_dir, args.episode_num, args.scene_num, available_shot_nums)
    generated_paths: list[Path] = []
    update_task_log_status(project_dir, args.episode_num, title, f"分镜头创作中 / 场景{args.scene_num}")
    prompt_path = shot_prompt_output_path_for_episode(project_dir, args.episode_num, args.scene_num, selected_shot_num)
    prompt_path.write_text(
        build_shot_prompt_pack(
            project_dir,
            args.episode_num,
            args.scene_num,
            selected_shot_num,
            title,
            core_event,
            scene_path,
        ),
        encoding="utf-8",
    )
    generated_paths.append(prompt_path)

    for path in generated_paths:
        print(path)
    return 0


def command_stitch_scenes(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    plan_rows = parse_scene_plan_rows(read_text(plan_path_for_episode(project_dir, args.episode_num)))
    if plan_rows:
        target_scene_nums = [int(row["scene"]) for row in plan_rows]
    else:
        scene_files = find_scene_output_files(project_dir, args.episode_num)
        target_scene_nums = [scene_num for scene_num, _ in scene_files]

    if not target_scene_nums:
        print("Stitch-scenes 失败：未找到可拼装的场景。")
        print("请先生成镜头文件 `shot-001.md`，或兼容旧路径的整场正文。")
        return 1

    stitched_parts: list[str] = []
    stitched_sources: list[str] = []
    missing_scene_nums: list[int] = []
    for scene_num in target_scene_nums:
        shot_assembled_text = assemble_scene_from_shot_files(project_dir, args.episode_num, scene_num)
        if shot_assembled_text:
            stitched_parts.append(shot_assembled_text)
            stitched_sources.append(f"- scene-{scene_num:02d}: 来自 shot 文件")
            continue

        legacy_scene_path = None
        for candidate in (
            legacy_scene_output_path_for_episode(project_dir, args.episode_num, scene_num, ".md"),
            legacy_scene_output_path_for_episode(project_dir, args.episode_num, scene_num, ".txt"),
        ):
            if candidate.exists():
                legacy_scene_path = candidate
                break

        if legacy_scene_path:
            content = read_text(legacy_scene_path).strip()
            if content:
                stitched_parts.append(content)
                stitched_sources.append(f"- scene-{scene_num:02d}: {legacy_scene_path}")
                continue

        missing_scene_nums.append(scene_num)

    if missing_scene_nums:
        print("Stitch-scenes 失败：缺少以下场景镜头文件或兼容旧版整场正文：")
        for scene_num in missing_scene_nums:
            print(f"- scene-{scene_num:02d}")
        return 1

    if not stitched_parts:
        print("Stitch-scenes 失败：找到文件，但内容为空。")
        return 1

    output_path = Path(args.output).resolve() if args.output else stitched_scene_output_path_for_episode(project_dir, args.episode_num)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(stitched_parts).rstrip() + "\n", encoding="utf-8")

    print(output_path)
    for item in stitched_sources:
        print(item)
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


def analyze_script_quality(text: str, max_chars: int) -> dict[str, Any]:
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

    errors: list[str] = []
    warnings: list[str] = []

    if effective_chars > max_chars:
        errors.append(f"字符数超标：{effective_chars} > {max_chars}")
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

    risk_word_counts = {keyword: text.count(keyword) for keyword in BANNED_RISK_WORDS if text.count(keyword)}

    return {
        "effective_chars": effective_chars,
        "scene_blocks": scene_blocks,
        "headers": headers,
        "location_changes": location_changes,
        "locations": locations,
        "dialogue_counts": dialogue_counts,
        "total_dialogue_lines": total_dialogue_lines,
        "blank_line_count": blank_line_count,
        "separator_count": separator_count,
        "errors": errors,
        "warnings": warnings,
        "risk_word_counts": risk_word_counts,
    }


def print_script_quality_report(script_path: Path, report: dict[str, Any]) -> None:
    print(f"检查文件：{script_path}")
    print(f"- 有效字符数：{report['effective_chars']}")
    print(f"- 场景数：{len(report['scene_blocks'])}")
    print(f"- 地点切换次数：{report['location_changes']}")
    if report["locations"]:
        print(f"- 场景地点：{' / '.join(report['locations'])}")
    print(f"- 有效对白数：{report['total_dialogue_lines']}")
    if report["dialogue_counts"]:
        print(f"- 单场对白数：{' / '.join(str(count) for count in report['dialogue_counts'])}")
    print(f"- 空行数：{report['blank_line_count']}")
    print(f"- --- 分隔符数量：{report['separator_count']}")

    if report["errors"]:
        print("\n错误：")
        for item in report["errors"]:
            print(f"- {item}")
    if report["warnings"]:
        print("\n警告：")
        for item in report["warnings"]:
            print(f"- {item}")

    if not report["errors"] and not report["warnings"]:
        print("\n检查通过。")


def collect_finish_quality_blockers(report: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    expected_dialogue_total = max(MIN_DIALOGUE_LINES_TOTAL, len(report["scene_blocks"]) * MIN_DIALOGUE_LINES_PER_SCENE)
    if report["effective_chars"] < MIN_EFFECTIVE_SCRIPT_CHARS:
        blockers.append(
            f"正文偏短：{report['effective_chars']} < {MIN_EFFECTIVE_SCRIPT_CHARS}，这类结果很容易只是结构合规的提纲。"
        )
    if report["total_dialogue_lines"] < expected_dialogue_total:
        blockers.append(
            f"有效对白偏少：{report['total_dialogue_lines']} < {expected_dialogue_total}，当前文本更像镜头提纲而不是可交付剧本。"
        )
    for header, dialogue_count in zip(report["headers"], report["dialogue_counts"]):
        if dialogue_count < MIN_DIALOGUE_LINES_PER_SCENE:
            blockers.append(f"{header} 的有效对白少于 {MIN_DIALOGUE_LINES_PER_SCENE} 句。")
    total_risk_word_hits = sum(report["risk_word_counts"].values())
    if total_risk_word_hits >= FINISH_BLOCKING_RISK_WORD_THRESHOLD:
        blockers.append(
            f"风险词累计出现 {total_risk_word_hits} 次，已超过回写阈值 {FINISH_BLOCKING_RISK_WORD_THRESHOLD}。"
        )
    return blockers


def command_check(args: argparse.Namespace) -> int:
    script_path = Path(args.script_path).resolve()
    if not script_path.exists():
        print(f"文件不存在：{script_path}")
        return 1

    report = analyze_script_quality(read_text(script_path), args.max_chars)
    print_script_quality_report(script_path, report)
    return 1 if report["errors"] else 0


def command_consistency_check(args: argparse.Namespace) -> int:
    project_dir = ensure_project_dir(Path(args.project_dir))
    title, core_event = resolve_episode_meta(project_dir, args.episode_num, args.title, args.core_event)
    script_path = Path(args.script_path).resolve() if args.script_path else find_episode_script(project_dir, args.episode_num)
    script_text = ""
    if script_path:
        if not script_path.exists():
            print(f"剧本文件不存在：{script_path}")
            return 1
        script_text = read_text(script_path)

    report = build_consistency_report(
        project_dir,
        args.episode_num,
        title,
        core_event,
        script_text=script_text,
    )
    print_consistency_report(project_dir, script_path, report)
    return 1 if report["errors"] else 0


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
    ready, _ = ensure_preflight_ready(project_dir, "Finish")
    if not ready:
        return 1
    script_path = Path(args.script_path).resolve()
    if not script_path.exists():
        print(f"剧本文件不存在：{script_path}")
        return 1
    script_text = read_text(script_path)
    report = analyze_script_quality(script_text, args.max_chars)
    print_script_quality_report(script_path, report)
    if report["errors"]:
        print("\nFinish 终止：请先修复 `check/review` 的错误项，再回写状态。")
        return 1
    quality_blockers = collect_finish_quality_blockers(report)
    if quality_blockers and not getattr(args, "allow_quality_warnings", False):
        print("\nFinish 终止：结构虽然过关，但以下质量风险仍会污染后续状态文件：")
        for item in quality_blockers:
            print(f"- {item}")
        print("如确认要带警告归档，显式传 `--allow-quality-warnings`。")
        return 1
    archived_script_path = persist_episode_script(project_dir, args.episode_num, script_path)

    title, core_event = resolve_episode_meta(project_dir, args.episode_num, args.title, args.core_event)
    consistency_report = build_consistency_report(
        project_dir,
        args.episode_num,
        title,
        core_event,
        script_text=script_text,
    )

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

    state_diff_path = write_state_diff(
        project_dir,
        args.episode_num,
        build_state_diff_payload(
            project_dir,
            args.episode_num,
            archived_script_path,
            title=title,
            core_event=core_event,
            summary=args.summary,
            quality_report=report,
            consistency_report=consistency_report,
        ),
    )

    print("已更新：")
    print(f"- 归档剧本：{archived_script_path}")
    print(f"- {task_log_path}")
    print(f"- {history_path}")
    print(f"- {role_state_path}")
    print(f"- {hook_state_path}")
    print(f"- {state_diff_path}")
    if consistency_report["warnings"]:
        print("\n一致性提醒：")
        for item in consistency_report["warnings"]:
            print(f"- {item}")
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

    return command_compose_scenes(
        argparse.Namespace(
            project_dir=args.project_dir,
            episode_num=args.episode_num,
            scene_num=None,
            title=args.title,
            core_event=args.core_event,
            target_duration=args.target_duration,
            shot_seconds=args.shot_seconds,
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
    init_parser.add_argument("--seed-file", help="可选 JSON 文件；用于直接初始化到最小可写标准。")
    init_parser.add_argument("--force", action="store_true", help="覆盖已有同名项目中的标准文件，并先写入 .bak 备份。")

    init_project_parser = subparsers.add_parser("init-project")
    init_project_parser.add_argument("project_name")
    init_project_parser.add_argument("--path", default=".")
    init_project_parser.add_argument("--seed-file", help="可选 JSON 文件；用于直接初始化到最小可写标准。")
    init_project_parser.add_argument("--force", action="store_true", help="覆盖已有同名项目中的标准文件，并先写入 .bak 备份。")

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
    compose_parser.add_argument("--allow-full-episode", action="store_true")

    compose_scenes_parser = subparsers.add_parser("compose-scenes")
    compose_scenes_parser.add_argument("project_dir")
    compose_scenes_parser.add_argument("--episode-num", type=int, required=True)
    compose_scenes_parser.add_argument("--title")
    compose_scenes_parser.add_argument("--core-event")
    compose_scenes_parser.add_argument("--target-duration", default="3-5分钟")
    compose_scenes_parser.add_argument("--scene-num", type=int)
    compose_scenes_parser.add_argument("--shot-seconds", type=int, default=5)

    compose_shots_parser = subparsers.add_parser("compose-shots")
    compose_shots_parser.add_argument("project_dir")
    compose_shots_parser.add_argument("--episode-num", type=int, required=True)
    compose_shots_parser.add_argument("--scene-num", type=int, required=True)
    compose_shots_parser.add_argument("--shot-num", type=int)
    compose_shots_parser.add_argument("--scene-file")
    compose_shots_parser.add_argument("--shot-seconds", type=int, default=5)
    compose_shots_parser.add_argument("--title")
    compose_shots_parser.add_argument("--core-event")

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
    next_episode_parser.add_argument("--shot-seconds", type=int, default=5)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("script_path")
    check_parser.add_argument("--max-chars", type=int, default=3000)

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("script_path")
    review_parser.add_argument("--max-chars", type=int, default=3000)

    consistency_parser = subparsers.add_parser("consistency-check")
    consistency_parser.add_argument("project_dir")
    consistency_parser.add_argument("--episode-num", type=int, required=True)
    consistency_parser.add_argument("--script-path")
    consistency_parser.add_argument("--title")
    consistency_parser.add_argument("--core-event")

    apply_state_diff_parser = subparsers.add_parser("apply-state-diff")
    apply_state_diff_parser.add_argument("project_dir")
    apply_state_diff_parser.add_argument("--episode-num", type=int, required=True)
    apply_state_diff_parser.add_argument("--diff-file")

    finish_parser = subparsers.add_parser("finish")
    finish_parser.add_argument("project_dir")
    finish_parser.add_argument("episode_num", type=int)
    finish_parser.add_argument("script_path")
    finish_parser.add_argument("--title")
    finish_parser.add_argument("--core-event")
    finish_parser.add_argument("--summary", required=True)
    finish_parser.add_argument("--max-chars", type=int, default=3000, help="回写前结构检查使用的最大字符数阈值。")
    finish_parser.add_argument(
        "--allow-quality-warnings",
        action="store_true",
        help="允许带严重质量警告归档剧本。默认会阻断偏短、对白偏少、风险词过多的结果。",
    )

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
        args.seed_data = load_seed(args.seed_file)
        return command_init(args)
    if args.command == "init-project":
        args.seed_data = load_seed(args.seed_file)
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
    if args.command == "compose-shots":
        return command_compose_shots(args)
    if args.command == "stitch-scenes":
        return command_stitch_scenes(args)
    if args.command == "next-episode":
        return command_next_episode(args)
    if args.command in {"check", "review"}:
        return command_check(args)
    if args.command == "consistency-check":
        return command_consistency_check(args)
    if args.command == "apply-state-diff":
        return command_apply_state_diff(args)
    if args.command == "finish":
        return command_finish(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
