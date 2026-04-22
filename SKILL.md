---
name: junli-drama-editor
description: 平台向微短剧编剧工程工作流，适用于“写第X集”“续写短剧”“改卡点”“压3000字”“改对白”“恢复状态”“投稿资料”“AI视频版剧本”“拍摄版剧本”等任务；覆盖立项、5 个配置文件初始化、角色状态同步、分集梗概推进、单集剧本创作、定向返修与质量检查。
---

# 君黎 AI 短剧编剧

先读 `PROJECT.md`。它把本仓库压成 `Rule / Workflow / Command` 三层入口，先定位任务，再决定要不要下钻到脚本或参考文档。

这是通用 skill，不依赖特定宿主的安装、注册或发现机制。能直接读取本仓库文件时就能使用；`scripts/episode_pipeline.py` 只是仓库附带的可选自动化实现，不是 skill 的前置条件。

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

- 新建短剧项目：先补齐最小可写标准；仓库脚本可用时，对应 `init-project`（兼容 `init`）
- 继续写下一集：先恢复状态，再做分场规划；仓库脚本可用时，对应 `next-episode`
- 生成分场 / 分镜创作包：`compose-scenes` / `compose-shots`
- 生成整集创作包：`compose`，只在明确要求整集输出时用
- 单集质检：`review`
- 单集一致性检查：`consistency-check`
- 恢复状态 / 修记忆：`resume`
- 投稿资料整理：读 `references/submission-package.md`

真实触发说法优先参考：

- `references/trigger-examples.md`
- 项目是否达到最小可写标准，优先看 `references/minimum-project-standard.md`
- 写法拿不准时，用 `references/good-vs-bad-examples.md` 校准
- 想加强抓人度、回报感和钩子密度时，读 `references/story-attraction.md`

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
- 提到“知情越权 / 伏笔断裂 / 梗概冲突 / 写跑偏了” -> 额外跑 `consistency-check`
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

## 执行门槛

不同 `task` 的门槛不同，不要把整套链路硬套到所有请求上。

1. `task=init` 时，先补最小可写标准，再初始化项目：

```bash
python3 scripts/episode_pipeline.py init "项目名" --path <输出目录> --seed-file <seed.json>
```

如果当前环境没有 CLI，就按同样结构手动建立 5 个核心配置文件、状态目录和投稿基础文档。

如果用户只给了项目名、还没给到最小可写标准的关键项，也可以先生成骨架；但那只是骨架，不代表已经能开写。旧骨架项目补 seed 时，加 `--force` 覆盖标准文件；覆盖前会自动留 `.bak` 备份。

2. `task=next` 时，写新一集前必须先恢复上下文：

```bash
python3 scripts/episode_pipeline.py preflight <项目目录>
python3 scripts/episode_pipeline.py resume <项目目录>
```

如果当前环境没有 CLI，也要等价完成这两件事：确认项目不是空壳模板，并拉出最近 2-3 集摘要、当前角色知情状态、活跃伏笔、下一集目标。

3. `task=next` 的默认流程是分场规划，不是整集直写：

```bash
python3 scripts/episode_pipeline.py plan <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose-scenes <项目目录> --episode-num <集数>
```

默认不再直接走整集 `compose`。新一集先生成分场规划 prompt，再逐镜头生成。

如果你确实要手动触发整集输出，必须显式使用：

```bash
python3 scripts/episode_pipeline.py compose <项目目录> --episode-num <集数> --allow-full-episode
```

如果当前模型或视频工具一次吃不下整集，改用分场 / 分镜链路：

```bash
python3 scripts/episode_pipeline.py compose-scenes <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose-shots <项目目录> --episode-num <集数> --scene-num <场景号> --shot-num <镜头号>
```

`compose-scenes` 会在 `runtime/episode-XXXX/scene-YY/` 下生成单场 Prompt Pack，并要求当前场只输出“当前场摘要 + 严格按 `0-5秒 / 5-10秒 / 10-15秒` 连续切开的镜头单元表”，不准再写长场景正文。

即使不传 `--scene-num`，`compose-scenes` 也只能生成 1 个“下一个缺失场景”的 prompt，不会批量生成全场次。

`compose-shots` 会读取 `scene.md` 里的镜头单元表，再把单个镜头拆成独立 Prompt Pack；如果发现某行不是严格 5 秒，直接拒绝生成。推荐目录：

- `runtime/episode-XXXX/plan.md`
- `runtime/episode-XXXX/scene-01/scene.prompt.md`
- `runtime/episode-XXXX/scene-01/scene.md`
- `runtime/episode-XXXX/scene-01/shot-001.prompt.md`
- `runtime/episode-XXXX/scene-01/shot-001.md`

如果下游视频工具一次只能吃 5 秒镜头，默认就该走这条目录化流程，每次只生成一个镜头，不要让模型一口气写几十秒。`scene.md` 只是规划稿，不是最终场景正文。

即使不传 `--shot-num`，`compose-shots` 也只能生成 1 个“下一个缺失镜头”的 prompt，不会把整场镜头一次性吐完。

默认交付就停在 `runtime/episode-XXXX/scene-YY/` 目录下的 `scene.md / shot-001.md / shot-002.md ...`。只有老工具强制要求单文件时，才额外用 `stitch-scenes` 做兼容拼装。

4. `task=repair` 或 `task=review` 时，先做结构门，再决定改哪些块：

```bash
python3 scripts/episode_pipeline.py check <剧本文件路径>
python3 scripts/episode_pipeline.py review <剧本文件路径>
python3 scripts/episode_pipeline.py check-shot <镜头文件路径>
python3 scripts/episode_pipeline.py review-shot <镜头文件路径>
python3 scripts/episode_pipeline.py consistency-check <项目目录> --episode-num <集数> --script-path <剧本文件路径>
```

- `check / review` 负责结构门
- `check-shot / review-shot` 负责 5 秒单镜头结构门
- `consistency-check` 只在知情状态、伏笔、分集目标可能跑偏时追加
- 默认定向返修，不整集推倒重写
- `task=resume` 时只修上下文，不自动开写新一集
- `task=submission` 时只补投稿交付物，不强制跑单集创作链路

5. 如果要交付完整剧本，必须满足：
   - 交付的是剧本格式，不是小说段落
   - 默认 4-5 个场景
   - 独立地点切换默认不超过 3 次
   - 3 秒内进入冲突
   - 每集至少 3 个爽点
   - 每场至少完成“目标 -> 阻碍 -> 变化”三步，不得整场只解释信息
   - 如果下游视频工具只能生成 5 秒镜头，镜头表必须严格拆成连续 5 秒单元，不要把剧情绑死在单个长镜头里
   - 首场景写主角完整外貌，后续只写服装变化

6. `finish` / `apply-state-diff` 不是所有任务的默认收尾，只在下面两类情况执行：

- 用户明确要求“定稿 / 归档 / 回写状态 / 同步状态文件”
- 当前任务天然就是最终交付，且你已经确认要把这次变动持久化到长期状态

对应 CLI：

```bash
python3 scripts/episode_pipeline.py check <剧本文件路径>
python3 scripts/episode_pipeline.py finish <项目目录> <集数> <剧本文件路径> --summary "本集摘要"
python3 scripts/episode_pipeline.py apply-state-diff <项目目录> --episode-num <集数>
```

执行规则：

- 在草案、快修、单纯质检、状态梳理阶段，不自动持久化状态
- `finish` 会归档剧本、更新历史并生成 `state diff`
- `apply-state-diff` 会真的改写长期状态表；执行前必须确认是否要落盘
- 如果 `preflight` 失败，必须先补文件或替换模板占位；禁止假装已经恢复上下文
- 如果用户要求的是“拍摄版”而不是“AI 视频生成版”，优先遵守拍摄版场景经济性；如果用户要求的是“AI 视频生成版”，优先遵守结构化场景块和 3000 字符控制

## 违约信号

出现任一情况，视为未遵守本 skill：

- 没跑 `preflight` / `resume` 就直接续写下一集
- 输出成了小说、旁白散文或大段心理描写
- 角色说出了自己不该知道的秘密
- 每一句台词都不推动关系、冲突或信息
- 把仓库 CLI 当成 skill 的前置条件
- 把 `finish` / `apply-state-diff` 当成任意任务的默认收尾
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
- 把这些信息整理进 seed JSON，再初始化项目
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
- 先做场景卡，再生成分场规划 prompt，不要默认直接整集输出

### C. 单集返修 / 格式化 / 质检

触发：
- 改某一集对白
- 压 3000 字
- 增加爽点 / 卡点
- 检查是否像小说
- 检查知情越权、伏笔断裂或梗概偏离

必须动作：
- 读取目标剧本
- 至少补读上一集或相关状态文件
- 默认做定向返修
- 先跑 `check`，再决定改哪些块
- 涉及知情状态、活跃伏笔或本集目标是否跑偏时，再跑 `consistency-check`
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
2. 如果当前任务是严格 5 秒单镜头交付，切换成：
   - `镜头X: 地点(0-5秒)`
   - `(主体) / (环境) / (动作) / (光影) / (镜头) / (画质)`
   - `台词:`
3. 严格 5 秒单镜头模式下，不要再输出 `场景X: 地点(0-45秒)` 这种整场标题。
4. 台词只保留对话和停顿，不夹动作和语速说明。
5. `VO` 只在人物出现在画面中时使用；`OS` 只在人物不在画面中但有声音时使用。
6. 默认去掉空行和 `---` 分隔符，优先让剧本适配 3000 字符限制。
7. 如果用户明确要传统拍摄剧本，可切换到“场次号 + 日/夜 + 内/外 + 出场人物”的制片版，但仍然禁止小说化描写。

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

## 可选命令

```bash
python3 scripts/episode_pipeline.py rules
python3 scripts/episode_pipeline.py workflows
python3 scripts/episode_pipeline.py commands
python3 scripts/episode_pipeline.py init-project "项目名" --path <输出目录>
python3 scripts/episode_pipeline.py init "项目名" --path <输出目录>
python3 scripts/episode_pipeline.py preflight <项目目录>
python3 scripts/episode_pipeline.py resume <项目目录>
python3 scripts/episode_pipeline.py plan <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose <项目目录> --episode-num <集数> --allow-full-episode
python3 scripts/episode_pipeline.py compose-scenes <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py compose-shots <项目目录> --episode-num <集数> --scene-num <场景号> --shot-num <镜头号>
python3 scripts/episode_pipeline.py next-episode <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py check <剧本文件路径>
python3 scripts/episode_pipeline.py check-shot <镜头文件路径>
python3 scripts/episode_pipeline.py consistency-check <项目目录> --episode-num <集数> --script-path <剧本文件路径>
python3 scripts/episode_pipeline.py finish <项目目录> <集数> <剧本文件路径> --summary "本集摘要"
python3 scripts/episode_pipeline.py apply-state-diff <项目目录> --episode-num <集数>
python3 scripts/episode_pipeline.py review <剧本文件路径>
python3 scripts/episode_pipeline.py review-shot <镜头文件路径>
```

如果老工具强制要求单文件，再额外使用：

```bash
python3 scripts/episode_pipeline.py stitch-scenes <项目目录> --episode-num <集数>
```
