#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""初始化微短剧项目结构。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
REFERENCES_DIR = ROOT_DIR / "references"


def load_template(filename: str, fallback: str) -> str:
    path = REFERENCES_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def safe_project_dirname(project_name: str) -> str:
    return re.sub(r"[\\/]+", "-", project_name).strip() or "短剧项目"


def write_if_missing(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content.rstrip() + "\n", encoding="utf-8")


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


def build_drama_overview(project_name: str) -> str:
    return f"""# 短剧概况

- 剧名：{project_name}
- 类型：
- 总集数：
- 单集时长：
- 目标平台：
- 目标受众：
- 付费卡点：
- 故事看点：

## 300 字梗概

待补充。
"""


def build_story_outline() -> str:
    return """# 故事大纲

## 背景

待补充。

## 切入点

待补充。

## 铺垫

待补充。

## 高潮

待补充。

## 结尾与后续钩子

待补充。
"""


def build_character_bios() -> str:
    return """# 人物小传

## 角色 1

- 基础信息：
- 外观造型：
- 性格特质：
- 身份设定：
- 技能 / 金手指：
- 情感线：
- 剧情主线：

## 角色 2

- 基础信息：
- 外观造型：
- 性格特质：
- 身份设定：
- 技能 / 金手指：
- 情感线：
- 剧情主线：
"""


def build_episode_synopsis() -> str:
    return """# 分集梗概

## 第 1 集

- 起因：
- 经过：
- 结果 / 卡点：
"""


def create_drama_project(project_name: str, output_dir: Path) -> Path:
    project_dir = output_dir / safe_project_dirname(project_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    for directory in ("docs", "episodes", "runtime", "state"):
        (project_dir / directory).mkdir(parents=True, exist_ok=True)

    write_if_missing(
        project_dir / "series-bible.md",
        load_template(
            "series-bible-template.md",
            "# 剧集基本信息\n\n剧名：\n类型：\n总集数：\n单集时长：\n",
        ),
    )
    write_if_missing(
        project_dir / "character-design.md",
        load_template("character-design-template.md", "# 角色设计\n"),
    )
    write_if_missing(
        project_dir / "visual-bible.md",
        load_template("visual-bible-template.md", "# 视觉规范\n"),
    )
    write_if_missing(
        project_dir / "narrative-style.md",
        load_template("narrative-style-template.md", "# 叙事风格\n"),
    )
    write_if_missing(
        project_dir / "linenew.md",
        load_template("linenew-template.md", "1:标题-核心事件\n"),
    )
    write_if_missing(
        project_dir / "state" / "角色状态.md",
        load_template("role-state-template.md", "# 角色状态\n"),
    )
    write_if_missing(project_dir / "state" / "伏笔列表.md", build_hooks_template())
    write_if_missing(project_dir / "state" / "剧集历史.md", build_history_template())
    write_if_missing(project_dir / "task_log.md", build_task_log(project_name))

    write_if_missing(project_dir / "docs" / "短剧概况.md", build_drama_overview(project_name))
    write_if_missing(project_dir / "docs" / "故事大纲.md", build_story_outline())
    write_if_missing(project_dir / "docs" / "人物小传.md", build_character_bios())
    write_if_missing(project_dir / "docs" / "分集梗概.md", build_episode_synopsis())

    return project_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化微短剧项目结构")
    parser.add_argument("project_name", help="项目名")
    parser.add_argument(
        "--path",
        default=".",
        help="输出目录，默认当前目录",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_dir = create_drama_project(args.project_name, Path(args.path).resolve())
    print(project_dir)


if __name__ == "__main__":
    main()
