# 君黎 AI 短剧编剧工程

面向平台向微短剧创作的工程化工作流仓库，用来统一管理项目初始化、状态恢复、分集创作、结构质检和状态回写。

这个仓库同时提供两种用法：

- 作为本地 Codex skill 包安装后触发 `SKILL.md`
- 作为 CLI 工具直接运行 `scripts/episode_pipeline.py`

默认入口不是直接背命令，而是先看 [PROJECT.md](PROJECT.md)，再按 `Rule / Workflow / Command` 三层结构执行。

## 适用场景

- 新建短剧项目骨架
- 继续写第 X 集
- 生成可直接喂给 AI 的单集创作包
- 生成单场 / 单镜头 Prompt Pack，适配 5 秒视频工具
- 检查剧本是否小说化、格式是否合规
- 回写剧集历史、角色状态和伏笔状态

## 安装成 Skill

仓库里有 `SKILL.md`，但单独把仓库 clone 下来并不会自动注册成 skill。要让代理真正发现它，先安装到本地 skills 目录：

```bash
python3 scripts/install_skill.py
python3 scripts/install_skill.py --check
```

默认会安装到 `$CODEX_HOME/skills`；如果没有设置 `CODEX_HOME`，则使用 `~/.codex/skills`。默认是软链接安装，便于你在当前仓库继续迭代。

仓库主入口：

```bash
python3 scripts/episode_pipeline.py --help
```

常用命令：

```bash
# 查看工作流索引
python3 scripts/episode_pipeline.py workflows

# 初始化一个真正可开写的新项目
python3 scripts/episode_pipeline.py init-project "项目名" --path ./output --seed-file examples/minimum-seed.json

# 只创建骨架项目（不会自动通过 preflight）
python3 scripts/episode_pipeline.py init-project "项目名" --path ./output

# 旧骨架项目补 seed 时，允许覆盖标准文件（覆盖前会写 .bak 备份）
python3 scripts/episode_pipeline.py init-project "项目名" --path ./output --seed-file examples/minimum-seed.json --force

# 继续写下一集
python3 scripts/episode_pipeline.py next-episode <项目目录> --episode-num <集数>

# 先分场，再拆单镜头
python3 scripts/episode_pipeline.py compose-scenes <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose-shots <项目目录> --episode-num <集数> --scene-num <场景号> --shot-num <镜头号>

# 只有明确要整集输出时，才允许这样做
python3 scripts/episode_pipeline.py compose <项目目录> --episode-num <集数> --allow-full-episode

# 结构化质检
python3 scripts/episode_pipeline.py review <剧本文件路径>

# 完成后回写状态
python3 scripts/episode_pipeline.py finish <项目目录> <集数> <剧本文件路径> --summary "本集摘要"
```

不传 `--scene-num` 或 `--shot-num` 时，命令也只会生成“下一个缺失项”各 1 个 prompt，不会批量生成。
`plan / compose / compose-scenes / compose-shots / finish` 现在都会先卡 `preflight`，不会再把空模板项目直接推进到 prompt 生成或状态回写。

## 目录结构

```text
.
├── PROJECT.md
├── SKILL.md
├── examples/
│   └── minimum-seed.json
├── references/
│   ├── minimum-project-standard.md
│   ├── quality-checklist.md
│   ├── screenplay-format.md
│   └── ...
└── scripts/
    ├── install_skill.py
    ├── episode_pipeline.py
    └── new_project.py
```

## 使用建议

1. 先读 `PROJECT.md`，确认当前任务属于哪个 Workflow。
2. 新项目如果已经知道最小设定，优先用 `--seed-file` 初始化；裸 `init-project` 只会生成骨架。已有旧骨架时，用 `--force` 重刷标准文件，旧内容会先留 `.bak`。
3. 开写新一集前，先做 `preflight` 和 `resume`。
4. 如果下游工具只能吃 5 秒镜头，默认走 `compose-scenes -> compose-shots`，每次只生成一个镜头；`scene.md` 只保留场景摘要和镜头表，不再写成长场景正文，镜头表不是严格 5 秒时，`compose-shots` 会直接报错。
5. 交付正文前，先做 `review`，再结合 `references/quality-checklist.md` 人工复核。
6. `finish` 会再次执行结构检查；有错误就拒绝回写状态。

## 运行环境

- Python 3.10+
- 当前脚本使用标准库，无额外第三方依赖

## 参考文档

- [PROJECT.md](PROJECT.md)：仓库总入口
- [SKILL.md](SKILL.md)：面向代理执行的规则说明
- [references/minimum-project-standard.md](references/minimum-project-standard.md)：最小可写标准
- [references/quality-checklist.md](references/quality-checklist.md)：质检清单
