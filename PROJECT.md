# 君黎 AI 短剧编剧项目索引

这是本仓库的总入口。先看这里，再去看分散文档。

如果你希望代理把本仓库当作真正的本地 skill 来发现，而不是只在当前目录里读文件，先运行：

```bash
python3 scripts/install_skill.py
```

本项目按 3 层暴露能力：

1. Rule：定义什么不能错，尤其是“剧本不是小说”和“角色知情状态不能乱”。
2. Workflow：把短剧高频任务打包成可直接执行的工作流。
3. Command：保留底层原子命令，给初始化、排查和批量整理时使用。

默认顺序不是先记命令，而是：

1. 先判定当前任务属于哪个 Workflow。
2. 再确认会受哪些 Rule 约束。
3. 只有需要拆开排查时，才回到底层 Command。

## Rule

### 1. 核心配置层

项目每次创作默认先读这 5 个文件：

- `series-bible.md`
- `character-design.md`
- `visual-bible.md`
- `narrative-style.md`
- `linenew.md`

最小可写标准优先读：

- `references/minimum-project-standard.md`

### 2. 状态记忆层

这些文件约束“谁知道什么、哪些伏笔已埋、现在写到哪一集”：

- `state/角色状态.md`
- `state/伏笔列表.md`
- `state/剧集历史.md`
- `task_log.md`

### 3. 投稿与补充文档层

这些文件用于平台资料、故事总控和系列介绍：

- `docs/短剧概况.md`
- `docs/故事大纲.md`
- `docs/人物小传.md`
- `docs/分集梗概.md`

投稿资料是否齐全，优先看：

- `references/submission-checklist.md`

优先级固定：

`核心配置层 > 状态记忆层 > 当前集临时计划 > 剧集历史 / 上一集剧本 > 单集正文`

查看 Rule 层索引：

```bash
python3 scripts/episode_pipeline.py rules
```

## Workflow

### 1. 新建短剧项目

默认入口：

```bash
python3 scripts/episode_pipeline.py init-project "项目名" --path <输出目录> --seed-file examples/minimum-seed.json
# 或
python3 scripts/episode_pipeline.py init-project "项目名" --path <输出目录>
python3 scripts/episode_pipeline.py init "项目名" --path <输出目录>
```

会创建：

- 5 个核心配置文件
- 状态目录
- 投稿基础文档
- `episodes/` 与 `runtime/`

说明：

- 如果你已经拿到了最小可写标准里的核心信息，优先用 `--seed-file` 一次性把项目初始化成可过 `preflight` 的状态
- 如果你只传项目名，当前命令只会生成骨架项目，不会假装已经可写
- 如果旧版已经创建过空壳项目，现在想补 seed，直接在原命令后加 `--force` 覆盖标准文件；覆盖前会先留 `.bak` 备份

### 2. 继续写下一集

默认入口：

```bash
python3 scripts/episode_pipeline.py next-episode <项目目录> --episode-num <集数>
```

这个入口会串起：

`preflight -> resume -> plan -> compose-scenes`

它不会替你凭空跳过状态检查；任何缺文件、模板占位、缺状态、缺梗概的情况，都会先报阻塞。
从第 2 集开始，还会额外卡以下续写前置条件：

- 上一集历史记录存在且已完成
- 上一集正文文件存在
- 当前集在 `docs/分集梗概.md` 里有有效小节
- `state/伏笔列表.md` 里存在活跃伏笔
- `character-design.md` 里至少补齐 2 个关键反派 / 配角卡

现在即使你单独手动跑 `plan`、`compose-scenes` 或 `compose-shots`，也一样不能绕过 `preflight`。

### 3. 整集创作包生成（默认禁用）

默认入口：

```bash
python3 scripts/episode_pipeline.py compose <项目目录> --episode-num <集数> --allow-full-episode
```

它会把 5 个配置文件、`task_log.md`、最近 2-3 集摘要、上一集结束状态、活跃伏笔、当前场景卡、分集梗概补充和上一集剧本尾段编译成一份可直接喂给 AI 的 Prompt Pack。

注意：

- `compose` 默认禁用，防止误触发一次性整集生成；只有显式传 `--allow-full-episode` 才会执行
- `compose` 只生成 Prompt Pack，不会替你自动落正文文件
- Prompt Pack 会强制要求每场至少有“目标 -> 阻碍 -> 变化”的推进，不允许整场只解释线索
- 如果 AI 生成完正文，交给 `finish` 时会自动归档成 `episodes/episode-XXXX.md`

如果你用的是输出长度偏紧的模型，或者下游视频工具只能吃 5 秒左右的镜头，不要硬让它一次写完整集，改用下面的“单集目录 -> 分场 -> 单镜头”工作流。

### 4. 分场 / 分镜头创作包

默认入口：

```bash
python3 scripts/episode_pipeline.py compose-scenes <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose-shots <项目目录> --episode-num <集数> --scene-num <场景号> --shot-num <镜头号>
```

如果不传 `--scene-num`，`compose-scenes` 也只会挑“下一个缺失场景”生成 1 个 prompt，不会批量生成整集所有场景。

如果不传 `--shot-num`，`compose-shots` 也只会挑“当前场下一个缺失镜头”生成 1 个 prompt，不会批量生成整个场的所有镜头。

它会按当前 `场景节奏卡` 在单集目录下生成多个 Prompt Pack：

- `runtime/episode-XXXX/plan.md`
- `runtime/episode-XXXX/scene-01/scene.prompt.md`
- `runtime/episode-XXXX/scene-02/scene.prompt.md`
- ...

`compose-scenes` 先要求模型只处理一个场景的规划稿，只输出“当前场摘要 + 严格连续的 5 秒镜头单元表”，例如 `0-5秒 / 5-10秒 / 10-15秒`，不再输出 `场景1(0-40秒)` 这种长正文。

分场结果建议保存为：

- `runtime/episode-XXXX/scene-01/scene.md`
- `runtime/episode-XXXX/scene-02/scene.md`

这里的 `scene.md` 现在是规划文件，不是完整场景剧本。

然后用 `compose-shots` 从单场结果里继续拆出单镜头 Prompt Pack：

- `runtime/episode-XXXX/scene-01/shot-001.prompt.md`
- `runtime/episode-XXXX/scene-01/shot-002.prompt.md`
- `runtime/episode-XXXX/scene-01/shot-001.md`

这条链路的目标是：每次只生成一个镜头，宁可拆细，不要几十秒一块糊过去。

`compose-shots` 会先校验镜头表。如果某一行不是严格 5 秒，或者时间段不连续，它会直接失败，不再继续生成长镜头文件。

`stitch-scenes` 现在优先拼 `shot-001.md` 这类镜头文件，不再默认把 `scene.md` 当最终场景正文来拼。

写完后可用：

```bash
python3 scripts/episode_pipeline.py stitch-scenes <项目目录> --episode-num <集数>
```

把所有分场正文拼成：

- `runtime/episode-XXXX/assembled.md`

### 5. 单集结构化质检

默认入口：

```bash
python3 scripts/episode_pipeline.py review <剧本文件路径>
```

它会合并：

- 字数检查
- 场景块完整性检查
- 空行 / 分隔符检查
- 小说化风险词检查
- 对话格式检查
- 正文过短 / 对白稀少预警

它主要是结构门。爽点、卡点、人物一致性和知情状态，仍要结合 `references/quality-checklist.md` 做人工复核。

### 6. 状态回写

默认入口：

```bash
python3 scripts/episode_pipeline.py finish <项目目录> <集数> <剧本文件路径> --summary "本集摘要"
```

它会更新：

- `episodes/episode-XXXX.md` 归档剧本
- `task_log.md`
- `state/剧集历史.md`
- `state/角色状态.md` 的“待确认回写”提醒
- `state/伏笔列表.md` 的“待确认回写”提醒

在真正回写前，`finish` 还会先跑一次结构检查；如果剧本仍有硬错误，会直接拒绝归档和回写。
现在 `finish` 还会拦截“正文明显偏短 / 对白明显偏少 / 风险词过多”这类会污染后续状态的结果；如确实要带警告归档，必须显式传 `--allow-quality-warnings`。

角色状态和伏笔内容是否变化，仍建议人工确认后再细化回写，以免自动误判剧情。

如果状态已经乱了，不要硬接着写，先按：

- `references/state-repair-playbook.md`

查看 Workflow 层索引：

```bash
python3 scripts/episode_pipeline.py workflows
```

## Command

底层原子命令：

- `rules`
- `workflows`
- `commands`
- `init`
- `preflight`
- `resume`
- `plan`
- `compose`
- `compose-scenes`
- `compose-shots`
- `stitch-scenes`
- `check`
- `review`
- `finish`
- `next-episode`

查看 Command 层索引：

```bash
python3 scripts/episode_pipeline.py commands
```

## 初始化后项目结构

```text
[项目目录]/
├── docs/
│   ├── 短剧概况.md
│   ├── 故事大纲.md
│   ├── 人物小传.md
│   └── 分集梗概.md
├── episodes/
├── runtime/
│   └── episode-0001/
│       ├── plan.md
│       ├── prompt.md
│       ├── assembled.md
│       └── scene-01/
│           ├── scene.prompt.md
│           ├── scene.md
│           ├── shot-001.prompt.md
│           └── shot-001.md
├── state/
│   ├── 角色状态.md
│   ├── 伏笔列表.md
│   └── 剧集历史.md
├── series-bible.md
├── character-design.md
├── visual-bible.md
├── narrative-style.md
├── linenew.md
└── task_log.md
```

## 推荐用法

- 不知道从哪里进：先跑 `python3 scripts/episode_pipeline.py workflows`
- 要继续写下一集：优先用 `next-episode`
- 要生成给 AI 的整集 Prompt：只在你明确要整集输出时，才用 `compose --allow-full-episode`
- 模型一次写不完整集，或下游工具只能生成 5 秒左右镜头：先用 `compose-scenes`，再用 `compose-shots`
- 要把多个分场结果拼回整集：用 `stitch-scenes`
- 要把 AI 生成好的最终剧本归档到项目里：用 `finish`
- 要检查剧本格式和字数：优先用 `review`，再配合 `references/quality-checklist.md` 做人工复核
- 要做投稿资料：先对照 `references/submission-checklist.md`，再读 `references/submission-package.md`
- 要判断写法是不是跑偏：读 `references/good-vs-bad-examples.md`
