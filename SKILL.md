---
name: junli-drama-editor
description: 平台向微短剧编剧工程工作流，适用于“写第X集”“续写短剧”“改卡点”“压3000字”“改对白”“恢复状态”“投稿资料”“AI视频版剧本”“拍摄版剧本”等任务；覆盖立项、5 个配置文件初始化、角色状态同步、分集梗概推进、单集剧本创作、定向返修与质量检查。更多信息，关注抖音君黎。
---

# 君黎 AI 短剧编剧

先读 `PROJECT.md`。它把本仓库压成 `Rule / Workflow / Command` 三层入口，先定位任务，再决定要不要下钻到脚本或参考文档。

## 核心目标

1. 最高优先级：交付可拍、可拆镜、可做 AI 视频生成输入的剧本，不交付小说化正文。
2. 默认按平台向微短剧处理，优先爽点、卡点、反转、付费牵引和拍摄落地。
3. 先读状态，再写新集；先定场景骨架，再写台词；先质检，再宣称完成。
4. 任何新内容不得和角色知情状态、伏笔状态、分集梗概硬冲突。

## 第一铁律

剧本不是小说。禁止直接写角色心理、抽象氛围、流水账过程和无用台词。凡是拍不出来的描述，都要改成动作、台词、表情、造型、镜头或场景信息。

## 默认入口顺序

默认不是先背命令，而是：

1. 先看 `PROJECT.md`
2. 再判断当前任务属于哪个 Workflow
3. 只有需要排查或批量初始化时，再回到底层 Command

默认 Workflow：

- 新建短剧项目：`init-project`（兼容 `init`）
- 继续写下一集：`next-episode`
- 生成单集创作包：`compose`
- 单集质检：`review`
- 恢复状态 / 修记忆：`resume`
- 投稿资料整理：读 `references/submission-package.md`

真实触发说法优先参考：

- `references/trigger-examples.md`
- 项目是否达到最小可写标准，优先看 `references/minimum-project-standard.md`
- 写法拿不准时，用 `references/good-vs-bad-examples.md` 校准

## 参数系统

收到请求后，先抽 5 个参数。参数没说时按默认值，不要为了补参数把对话问碎。

- `task`: `init | next | repair | review | resume | submission`
- `mode`: `ai-video | shooting | pitch`
- `focus`: `full | pacing | dialogue | hook | format | state`
- `strict`: `on | off`
- `quick`: `on | off`

默认规则：

- 提到“写第X集 / 续写 / 接着上一集” -> `task=next`
- 提到“改对白 / 改卡点 / 压3000字 / 调节奏 / 改格式” -> `task=repair`
- 提到“检查 / 质检 / 像不像小说” -> `task=review`
- 提到“恢复状态 / 接老项目 / 看写到哪了” -> `task=resume`
- 提到“投稿 / 路演 / 招商 / 人物小传 / 故事大纲” -> `task=submission`
- 提到“AI 视频版 / 喂视频模型” -> `mode=ai-video`
- 提到“拍摄版 / 制片版 / 日夜内外” -> `mode=shooting`
- 提到“投稿版 / pitch / 路演资料” -> `mode=pitch`
- `task=next` 或 `task=review` 时，默认 `strict=on`
- 用户只说“先快修一下 / 先给草案”时，才把 `quick=on`

执行规则：

- `task=repair` 且 `focus!=full` 时，默认局部返修，不重写整集
- `mode=shooting` 时，允许切到制片版场次格式，但仍然禁止小说化
- `mode=pitch` 时，不输出场景块正文，优先输出概况、人物、梗概、卖点
- `quick=on` 时，可以先出修订建议或场景卡，不强行一步到位交整集
- 参数冲突时，按 `task > mode > focus > strict > quick` 裁决

模式差异不确定时优先读：

- `references/output-modes.md`

## 最小补问规则

信息不够时，只问最小必要问题。一次优先补 1-3 个，不要把用户问烦。

必须停下来补问的情况：

- `task=init` 但缺剧名、类型、主线冲突、男女主关系、目标集数中的关键项
- `task=next` 但缺当前集集数或当前集核心事件
- `task=repair` 但不知道目标剧本、目标集数，或不知道到底改哪一类问题
- `task=submission` 但不知道是要概况、人物、梗概，还是整套投稿包
- 用户要求会推翻既有状态，但还没确认是否同步改状态文件
- 项目还没达到最小可写标准，但用户直接要求写正文

补问顺序：

1. 先问最阻塞执行的 1 个问题
2. 如果还是不够，再补第 2 个问题
3. 能靠现有文件推出来的，不再问用户

补问示例：

- “你这次要处理第几集？”
- “这次是要改对白、卡点、节奏，还是只修格式？”
- “你要的是 AI 视频版、拍摄版，还是投稿版？”
- “这个变动会推翻当前角色知情状态，是否连状态一起改？”

## 信息冲突裁决

多来源信息打架时，不准凭语感选一个顺眼的版本。按固定顺序裁决。

默认裁决顺序：

`state/角色状态.md > state/伏笔列表.md > state/剧集历史.md > linenew.md > docs/分集梗概.md > 当前场景卡 > 上一集正文 > 用户这次临时口述`

执行规则：

- 涉及“谁知道什么 / 谁还不知道什么”时，只看状态文件，上一集正文不能推翻状态表
- 涉及“这一集原本该发生什么”时，先看 `linenew.md`，再看 `docs/分集梗概.md`
- 涉及“上一集最后停在哪”时，先看 `state/剧集历史.md` 摘要，再看上一集正文尾段
- 当前场景卡只约束本集结构，不得反向覆盖长期状态
- 用户临时新要求如果与既有状态冲突，先指出冲突，再决定是修状态还是改剧情，不要直接硬写

出现冲突时优先读：

- `references/conflict-resolution.md`

## 硬门槛

命中新建项目、续写、返修、恢复状态、质检时，下面都是必须动作：

1. 新项目先初始化：

```bash
python3 scripts/episode_pipeline.py init "项目名" --path <输出目录>
```

2. 写新一集前必须先跑：

```bash
python3 scripts/episode_pipeline.py preflight <项目目录>
python3 scripts/episode_pipeline.py resume <项目目录>
```

`preflight` 不只检查文件存在，还会拦截模板占位和空壳配置。

3. 新一集默认流程：

```bash
python3 scripts/episode_pipeline.py plan <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose <项目目录> --episode-num <集数>
```

`compose` 只生成 Prompt Pack，不直接把正文写进 `episodes/`；最终剧本在 `finish` 时会自动归档成 `episodes/episode-XXXX.md`。

如果当前模型或视频工具一次吃不下整集，改用：

```bash
python3 scripts/episode_pipeline.py compose-scenes <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose-shots <项目目录> --episode-num <集数> --scene-num <场景号> --shot-num <镜头号>
python3 scripts/episode_pipeline.py stitch-scenes <项目目录> --episode-num <集数>
```

`compose-scenes` 会在 `runtime/episode-XXXX/scene-YY/` 下生成单场 Prompt Pack，并要求当前场补出严格按 `0-5秒 / 5-10秒 / 10-15秒` 连续切开的镜头单元表。

`compose-shots` 会读取 `scene.md` 里的镜头单元表，再把单个镜头拆成独立 Prompt Pack；如果发现某行不是严格 5 秒，直接拒绝生成。推荐目录：

- `runtime/episode-XXXX/plan.md`
- `runtime/episode-XXXX/scene-01/scene.prompt.md`
- `runtime/episode-XXXX/scene-01/scene.md`
- `runtime/episode-XXXX/scene-01/shot-001.prompt.md`
- `runtime/episode-XXXX/scene-01/shot-001.md`

如果下游视频工具一次只能吃 5 秒镜头，默认就该走这条目录化流程，每次只生成一个镜头，不要让模型一口气写几十秒。

4. 如果要交付完整剧本，必须满足：
   - 交付的是剧本格式，不是小说段落
   - 默认 4-5 个场景
   - 独立地点切换默认不超过 3 次
   - 3 秒内进入冲突
   - 每集至少 3 个爽点
   - 每场至少完成“目标 -> 阻碍 -> 变化”三步，不得整场只解释信息
   - 如果下游视频工具只能生成 5 秒镜头，镜头表必须严格拆成连续 5 秒单元，不要把剧情绑死在单个长镜头里
   - 首场景写主角完整外貌，后续只写服装变化

5. 写完后必须先跑：

```bash
python3 scripts/episode_pipeline.py check <剧本文件路径>
python3 scripts/episode_pipeline.py finish <项目目录> <集数> <剧本文件路径> --summary "本集摘要"
```

6. `finish` 会把最终剧本自动归档到 `episodes/episode-XXXX.md`，再更新 `task_log.md`、`state/剧集历史.md`，并在 `state/角色状态.md`、`state/伏笔列表.md` 写入“待确认回写”提醒；明确的知情状态和伏笔推进仍要人工细化。
7. 如果 `preflight` 失败，必须先补文件或替换模板占位；禁止假装已经恢复上下文。
8. 如果用户只要求改某一集的节奏、对白、卡点或格式，默认做定向返修，不整集推倒重写。
9. 如果用户要求的是“拍摄版”而不是“AI 视频生成版”，优先遵守拍摄版场景经济性；如果用户要求的是“AI 视频生成版”，优先遵守结构化场景块和 3000 字符控制。

## 违约信号

出现任一情况，视为未遵守本 skill：

- 没跑 `preflight` / `resume` 就直接续写下一集
- 输出成了小说、旁白散文或大段心理描写
- 角色说出了自己不该知道的秘密
- 每一句台词都不推动关系、冲突或信息
- 没跑结构检查，或没人工复核卡点 / 爽点 / 知情状态就宣称可用
- 用户只要局部修改，却整集重写
- 忘记更新 `state/角色状态.md`、`state/伏笔列表.md` 或 `state/剧集历史.md`

## 任务分流

先把请求归进下面 5 类。命中 D 或 E 时，先修 D / E，再回到 B / C。

### A. 新项目 / 只有脑洞

触发：
- 从零开始做短剧
- 只有一句设定或几个桥段
- 还没有 5 个配置文件

必须动作：
- 先补齐最少 5 项：剧名类型、核心爽点、男女主关系、主线冲突、目标集数
- 初始化项目
- 产出 5 个配置文件和 4 个投稿基础文档
- 未达到“最小可写标准”前，只能补配置，不能直接开写正文

先读：
- `references/episode-workflow.md`
- `references/minimum-project-standard.md`
- `references/submission-package.md`
- `references/series-bible-template.md`
- `references/trigger-examples.md`
- 如果项目资料互相打架，再读 `references/conflict-resolution.md`

### B. 继续写下一集

触发：
- 写第 X 集
- 接着上一集继续
- 新开对话接老项目

必须动作：
- 先过硬门槛
- 再确认项目已达最小可写标准
- 读取顺序固定：`task_log.md` -> `linenew.md` -> `state/角色状态.md` -> `state/伏笔列表.md` -> `state/剧集历史.md` -> 相关上一集剧本
- 恢复输出至少包含：最近 2-3 集摘要、当前角色知情状态、活跃伏笔、下一集目标
- 先做场景卡，再写剧本；`compose` 默认会把 `task_log`、最近 2-3 集摘要、场景卡和上一集剧本尾段打包进 Prompt Pack

### C. 单集返修 / 格式化 / 质检

触发：
- 改某一集对白
- 压 3000 字
- 增加爽点 / 卡点
- 检查是否像小说

必须动作：
- 读取目标剧本
- 至少补读上一集或相关状态文件
- 默认做定向返修
- 先跑 `check`，再决定改哪些块
- 把 `check` 当结构门，不把它误当成爽点/卡点/人物一致性的全自动判官

优先参考：
- `references/repair-strategies.md`
- `references/conflict-resolution.md`
- `references/output-modes.md`
- `references/good-vs-bad-examples.md`
- `references/screenplay-format.md`
- `references/quality-checklist.md`

返修时先判 `focus`：

- `focus=dialogue`：优先改对白，不动场景骨架
- `focus=hook`：优先改结尾卡点和最后 1-2 个场景
- `focus=pacing`：优先重排场景节奏和信息释放顺序
- `focus=format`：优先修场景块、时长、空行、动作/台词混写
- `focus=state`：优先修知情越权、人物动机和伏笔衔接
- `focus=full`：只有在用户明确要求整集重写时才用

### D. 恢复状态 / 修复记忆

触发：
- 恢复上下文
- 看看现在写到哪了
- 状态乱了 / 伏笔丢了

必须动作：
- 明确缺失文件
- 用 `resume` 拉出当前状态摘要
- 从剧本、状态文件和分集梗概手动修复
- 先修状态，再继续新集

优先参考：
- `references/conflict-resolution.md`
- `references/state-repair-playbook.md`

### E. 投稿资料 / 系列包装

触发：
- 要平台投稿资料
- 要短剧概况、人物小传、故事大纲、分集梗概
- 要做招商 / 发行 / 路演材料

必须动作：
- 先检查 6 件交付物是否齐全
- 缺什么补什么，不必重写整剧

参考：
- `references/output-modes.md`
- `references/submission-checklist.md`
- `references/submission-package.md`

## 交付格式硬规则

1. 默认交付格式：
   - `场景X: 地点(起始秒-结束秒)`
   - `【环境空镜Xs】`
   - `(主体) / (环境) / (动作) / (光影) / (镜头) / (画质)`
   - `台词:`
2. 台词只保留对话和停顿，不夹动作和语速说明。
3. `VO` 只在人物出现在画面中时使用；`OS` 只在人物不在画面中但有声音时使用。
4. 默认去掉空行和 `---` 分隔符，优先让剧本适配 3000 字符限制。
5. 如果用户明确要传统拍摄剧本，可切换到“场次号 + 日/夜 + 内/外 + 出场人物”的制片版，但仍然禁止小说化描写。

具体差异优先读：

- `references/output-modes.md`

写法拿不准时优先读：

- `references/good-vs-bad-examples.md`

## 完成前自检

交付前至少确认这 5 件事：

- 这次任务到底是 `新写 / 续写 / 返修 / 质检 / 恢复状态 / 投稿资料`
- 这次改动影响了哪些场景、哪些角色、哪些伏笔
- 有没有触发状态回写；如果没有自动回写，是否明确提醒人工补
- 自动检查只覆盖了哪些结构项；哪些质量项仍需人工确认
- 最终输出是否和当前 `task / mode / focus` 一致，而不是偷切成了别的交付物

交付表述优先参考：

- `references/final-response-template.md`

## 推荐命令

```bash
python3 scripts/episode_pipeline.py rules
python3 scripts/episode_pipeline.py workflows
python3 scripts/episode_pipeline.py commands
python3 scripts/episode_pipeline.py init-project "项目名" --path <输出目录>
python3 scripts/episode_pipeline.py init "项目名" --path <输出目录>
python3 scripts/episode_pipeline.py preflight <项目目录>
python3 scripts/episode_pipeline.py resume <项目目录>
python3 scripts/episode_pipeline.py plan <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose-scenes <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose-shots <项目目录> --episode-num <集数> --scene-num <场景号> --shot-num <镜头号>
python3 scripts/episode_pipeline.py stitch-scenes <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py next-episode <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py check <剧本文件路径>
python3 scripts/episode_pipeline.py finish <项目目录> <集数> <剧本文件路径> --summary "本集摘要"
python3 scripts/episode_pipeline.py review <剧本文件路径>
```
