# 君黎 AI 短剧编剧工程

面向平台向微短剧创作的工程化工作流仓库，用来统一管理项目初始化、状态恢复、分集创作、结构质检和状态回写。

默认入口不是直接背命令，而是先看 [PROJECT.md](PROJECT.md)，再按 `Rule / Workflow / Command` 三层结构执行。

## 适用场景

- 新建短剧项目骨架
- 继续写第 X 集
- 生成可直接喂给 AI 的单集创作包
- 检查剧本是否小说化、格式是否合规
- 回写剧集历史、角色状态和伏笔状态

## 核心能力

仓库主入口：

```bash
python3 scripts/episode_pipeline.py --help
```

常用命令：

```bash
# 查看工作流索引
python3 scripts/episode_pipeline.py workflows

# 初始化一个新项目
python3 scripts/episode_pipeline.py init-project "项目名" --path ./output

# 继续写下一集
python3 scripts/episode_pipeline.py next-episode <项目目录> --episode-num <集数>

# 生成单集 Prompt Pack
python3 scripts/episode_pipeline.py compose <项目目录> --episode-num <集数>

# 结构化质检
python3 scripts/episode_pipeline.py review <剧本文件路径>

# 完成后回写状态
python3 scripts/episode_pipeline.py finish <项目目录> <集数> <剧本文件路径> --summary "本集摘要"
```

## 目录结构

```text
.
├── PROJECT.md
├── SKILL.md
├── references/
│   ├── minimum-project-standard.md
│   ├── quality-checklist.md
│   ├── screenplay-format.md
│   └── ...
└── scripts/
    ├── episode_pipeline.py
    └── new_project.py
```

## 使用建议

1. 先读 `PROJECT.md`，确认当前任务属于哪个 Workflow。
2. 开写新一集前，先做 `preflight` 和 `resume`。
3. 交付正文前，先做 `review`，再结合 `references/quality-checklist.md` 人工复核。
4. 写完后执行 `finish`，把历史与状态文件补齐。

## 运行环境

- Python 3.10+
- 当前脚本使用标准库，无额外第三方依赖

## 参考文档

- [PROJECT.md](PROJECT.md)：仓库总入口
- [SKILL.md](SKILL.md)：面向代理执行的规则说明
- [references/minimum-project-standard.md](references/minimum-project-standard.md)：最小可写标准
- [references/quality-checklist.md](references/quality-checklist.md)：质检清单
