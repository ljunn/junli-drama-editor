#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把当前仓库安装为本地 Codex skill。"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "junli-drama-editor"


def default_skill_home() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return codex_home / "skills"


def install_target(skill_home: Path) -> Path:
    return skill_home / SKILL_NAME


def remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.exists():
        shutil.rmtree(path)


def ignored_copy_entries(_: str, names: list[str]) -> set[str]:
    ignored = {".git", ".cc-connect", "__pycache__", ".pytest_cache"}
    return {name for name in names if name in ignored}


def check_install(path: Path) -> int:
    if not path.exists():
        print(f"未安装：{path}")
        return 1
    if path.is_symlink():
        print(f"已安装（软链接）：{path} -> {path.resolve()}")
    else:
        print(f"已安装（目录复制）：{path}")
    skill_file = path / "SKILL.md"
    print(f"入口文件：{skill_file}")
    return 0


def install_skill(target: Path, *, copy_mode: bool, force: bool) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if not force:
            print(f"目标已存在：{target}")
            print("如需覆盖，请加 `--force`。")
            return 1
        remove_existing(target)

    if copy_mode:
        shutil.copytree(REPO_ROOT, target, ignore=ignored_copy_entries)
        print(f"已复制安装到：{target}")
    else:
        target.symlink_to(REPO_ROOT, target_is_directory=True)
        print(f"已软链接安装到：{target} -> {REPO_ROOT}")

    print("如果当前代理会话还看不到该 skill，重新打开会话或刷新 skill 列表。")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="安装 junli-drama-editor skill 到本地 Codex skills 目录")
    parser.add_argument("--skill-home", default=str(default_skill_home()), help="skills 目录，默认 $CODEX_HOME/skills 或 ~/.codex/skills")
    parser.add_argument("--copy", action="store_true", help="复制目录而不是建立软链接")
    parser.add_argument("--force", action="store_true", help="若目标已存在则覆盖")
    parser.add_argument("--check", action="store_true", help="只检查安装状态，不执行安装")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = install_target(Path(args.skill_home).expanduser().resolve())
    if args.check:
        return check_install(target)
    return install_skill(target, copy_mode=args.copy, force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
