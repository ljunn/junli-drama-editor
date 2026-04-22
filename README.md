# 君黎 AI 短剧编剧工程

面向平台向微短剧创作的通用 skill 仓库，附带一个可选 CLI，用来统一管理项目初始化、状态恢复、分集创作、结构质检和状态回写。

这个仓库提供两层能力：

- 通用 skill：直接读取 `SKILL.md` 和 `PROJECT.md`
- 可选 CLI：运行 `scripts/episode_pipeline.py`

默认入口不是直接背命令，而是先看 [PROJECT.md](PROJECT.md)，再按 `Rule / Workflow / Command` 三层结构执行。

## 适用场景

- 新建短剧项目骨架
- 继续写第 X 集
- 生成可直接喂给 AI 的单集创作包
- 生成单场 / 单镜头 Prompt Pack，适配 5 秒视频工具
- 检查剧本是否小说化、格式是否合规
- 检查知情越权、伏笔断裂和分集梗概偏航风险
- 回写剧集历史、角色状态和伏笔状态

## 使用方式

这是通用 skill，不依赖特定平台的安装、注册或发现机制。能直接读取本仓库文件时就可以使用。

如果当前环境能运行 Python，可以把仓库附带的 CLI 当自动化层；如果没有脚本环境，也可以仅按 `SKILL.md` 和 `PROJECT.md` 的流程手动执行。

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

# 单镜头结构化质检
python3 scripts/episode_pipeline.py review-shot <镜头文件路径>

# 结合项目上下文做一致性检查
python3 scripts/episode_pipeline.py consistency-check <项目目录> --episode-num <集数> --script-path <剧本文件路径>

# 完成后回写状态
python3 scripts/episode_pipeline.py finish <项目目录> <集数> <剧本文件路径> --summary "本集摘要"

# 确认/编辑 diff 后，应用回 Markdown 状态表
python3 scripts/episode_pipeline.py apply-state-diff <项目目录> --episode-num <集数>
```

不传 `--scene-num` 或 `--shot-num` 时，命令也只会生成“下一个缺失项”各 1 个 prompt，不会批量生成。
`plan / compose / compose-scenes / compose-shots / finish` 现在都会先卡 `preflight`，不会再把空模板项目直接推进到 prompt 生成或状态回写。
从第 2 集开始，`plan / compose / compose-scenes / compose-shots` 还会额外阻断“上一集正文缺失 / 当前集梗概缺失 / 活跃伏笔为空 / 关键反派配角仍是占位”的续写请求。
`finish / apply-state-diff` 不是所有任务的默认收尾，只在明确要定稿、归档或持久化状态时才执行。

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
    ├── episode_pipeline.py
    └── new_project.py
```

## 使用建议

1. 先读 `PROJECT.md`，确认当前任务属于哪个 Workflow。
2. 先把仓库当通用 skill 使用，不要把任何宿主安装步骤当成前置条件。
3. 有脚本环境时再调用 CLI；没有时，就按同样文件职责和流程手动执行。
4. 新项目如果已经知道最小设定，优先用 `--seed-file` 初始化；裸 `init-project` 只会生成骨架。已有旧骨架时，用 `--force` 重刷标准文件，旧内容会先留 `.bak`。
5. 开写新一集前，先做 `preflight` 和 `resume`，或者手动完成等价的状态恢复。
6. 如果下游工具只能吃 5 秒镜头，默认走 `compose-scenes -> compose-shots`，每次只生成一个镜头；`scene.md` 只保留场景摘要和镜头表，不再写成长场景正文，镜头表不是严格 5 秒时，`compose-shots` 会直接报错。
7. Prompt Pack 现在会自动注入 `references/good-vs-bad-examples.md`、`references/repair-strategies.md` 和 `references/story-attraction.md` 的关键规则，别再只靠抽象规则硬写。
8. 整集或场景块正文交付前，先做 `review`；单镜头交付前，先做 `review-shot`。如果要看知情越权、活跃伏笔是否写丢、和分集梗概是否跑偏，再补 `consistency-check`。
9. `finish` 会再次执行结构检查，并在 `state/pending/episode-XXXX.state-diff.json` 产出可编辑的状态 diff；确认或补完后，再用 `apply-state-diff` 把内容写回 Markdown 状态表。严重质量警告仍会阻断回写。只有你明确接受风险时，才用 `--allow-quality-warnings` 强制归档。

## 运行环境

- Python 3.10+
- 当前脚本使用标准库，无额外第三方依赖

## 参考文档

- [PROJECT.md](PROJECT.md)：仓库总入口
- [SKILL.md](SKILL.md)：面向代理执行的规则说明
- [references/minimum-project-standard.md](references/minimum-project-standard.md)：最小可写标准
- [references/quality-checklist.md](references/quality-checklist.md)：质检清单
- [references/story-attraction.md](references/story-attraction.md)：抓人度、回报感和钩子密度规则
