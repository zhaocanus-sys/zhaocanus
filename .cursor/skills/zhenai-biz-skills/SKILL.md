---
name: zhenai-biz-skills
description: |
  珍爱网业务数据查询与分析的统一入口。当用户的问题涉及公司业务数据、
  业务流程或业务分析时，自动从云端 Skills 仓库匹配并加载对应的业务技能来执行。
  本 Skill 仅作路由网关，所有具体业务能力均托管在云端，随业务扩展持续增长。
---

# 珍爱业务数据网关

业务数据查询与分析的统一入口 — 自动识别意图、匹配云端技能、按需加载执行。

> **架构定位**：本 Skill 是路由层，不含任何具体业务逻辑。所有业务查询能力以独立 Skill 形式托管在云端，由本网关按需拉取和执行。
>
> **运行前提**：需要网络访问。默认路径依赖 `python3` 和 `curl`；若缺少 `python3`，先询问用户是否自动安装，若用户明确拒绝，再退回 `curl` 兼容模式。
>
> **云端 Skills 基地址**：`http://42.193.182.174:8090/skills/`
>
> **维护信息**：`author: zhenai-skills-team`，`version: 2.3`

### Skill 黑名单

以下云端 Skill **不参与匹配和使用**，在 Step 1 获取列表后自动过滤：

| Skill 名称 | 屏蔽原因 |
|-------------|----------|
| `compass-skills-service` | 已废弃，由更细粒度的专项 Skill 替代 |
| `zhenai-biz-skills` | 本网关自身，不应作为业务 Skill 被匹配 |

> 维护方式：需要新增或移除黑名单条目时，直接编辑此表格。

## 自动触发机制（核心）

> **原则：用户不需要知道"云端技能"的存在。当问题可能命中云端能力时，Agent 主动探测并应用。**

### 触发信号

**核心判断标准**：用户的问题是否涉及珍爱网的业务数据、业务流程或业务分析？

只要用户的意图指向**公司业务层面的数据获取、查询、统计或分析**，就应触发云端 Skill 探测。这包括但不限于：

- 查询或调取任何业务数据（无论哪个业务线、哪种数据类型）
- 对业务数据进行统计、分析、趋势观察或质量评估
- 涉及公司特定业务流程的操作或查询
- 用户明确要求使用云端技能

**不触发的情况**：纯技术编码、通用知识问答、本地文件编辑、已由超级工作台其他能力域覆盖的任务（邮件、Todo 等）。

**判断原则**：宁可多查一次列表（仅 ~2s 开销），不可错过匹配。不确定时，倾向于查。

### 自动触发流程

```
用户提问
  │
  ▼
判断：是否可能涉及业务数据查询/分析？
  │
  ├─ 否 → 正常回答（不触发云端查询）
  │
  └─ 是 → Step 1：获取云端 Skills 列表
           │
           ▼
         Step 2：匹配 skill 名称与用户意图
           │
           ├─ 无匹配 → 用 Agent 自身能力回答
           │
           └─ 有匹配 → Step 3：执行内部 apply 流程，应用该 skill
                        │
                        ▼
                     向用户回复任务结果
                        │
                        ▼
                     Step 4【必须执行】：网关自更新
                     先拉取远端 manifest.json 获取完整文件列表，
                     再调用 sync_required_files.py 同步所有文件
                     （详见"网关自更新"节的执行命令）
```

> ⚠️ **Step 4 是强制步骤，不得遗漏。** 每次成功执行 apply 并回复用户后，必须立即执行网关自更新命令，确保本地 SKILL.md 和同步脚本与云端保持一致。

### Step 1：快速获取 Skills 列表

```bash
python3 - <<'PY'
import re
import urllib.request

BLACKLIST = {'compass-skills-service', 'zhenai-biz-skills'}

html = urllib.request.urlopen('http://42.193.182.174:8090/skills/', timeout=30).read().decode('utf-8', 'ignore')
for name in sorted(set(re.findall(r'href="([^"]+)/"', html)) - {'..'}  - BLACKLIST):
    print(name)
PY
```

Windows PowerShell 可改用：

```powershell
$script = @'
import re
import urllib.request

BLACKLIST = {"compass-skills-service", "zhenai-biz-skills"}

html = urllib.request.urlopen("http://42.193.182.174:8090/skills/", timeout=30).read().decode("utf-8", "ignore")
for name in sorted(set(re.findall(r'href="([^"]+)/"', html)) - {".."}  - BLACKLIST):
    print(name)
'@
$script | python3 -
```

返回的是 Skill 目录名列表。优先使用 Python 标准库方式，避免依赖 `grep -P`、`rg` 等兼容性不稳定的外部命令。**不预设统一命名规范**，具体语义由 LLM 基于 skill 名称、description 和目录内容综合判断。

### Step 2：匹配 Skill

拿到 Skills 列表后，将用户问题的意图与列表中的 Skill 名称进行匹配。按优先级依次尝试：

1. **名称直接匹配**：用户明确说出 skill 名称 → 直接使用，无需进一步确认
2. **语义推断匹配**：将用户问题中的业务意图拆解为关键词，与 Skill 名称中的英文/中文语义对照，不要求名称遵循统一规范。例如用户问"电话录音"，列表中有一个 `telephone-record-skill`，大概率匹配
3. **读取 description 确认**：当名称推断不够确定时，获取候选 Skill 的 SKILL.md 首部 `description` 字段做二次确认：
   ```bash
   curl -s --connect-timeout 10 --max-time 15 http://42.193.182.174:8090/skills/{candidate_skill}/SKILL.md | head -20
   ```

**匹配结果处理**：
- **唯一匹配** → 直接进入 Step 3
- **多个候选** → 逐个读取 description，选最相关的；仍无法区分则列出候选让用户选择
- **无匹配** → 不强行使用云端 Skill，用 Agent 自身能力回答，或告知用户当前云端暂无对应能力

### Step 3：应用匹配的 Skill

确认匹配后，按下方内部 `apply` 流程执行。

### 不触发的情况

以下场景**不需要**查询云端 Skills 列表，避免无意义的网络开销：

- 纯编码任务（写代码、改 Bug、重构）
- 通用知识问答（技术概念解释、方案讨论）
- 文件操作（编辑本地文件、读取文档）
- 已由本地 Skill 或超级工作台其他能力域覆盖的任务（如邮件、Todo）

---

## 云端配置

- **云端 Skills 目录**: 见上方“云端 Skills 基地址”
- 每个子目录代表一个 skill，例如 `http://42.193.182.174:8090/skills/telephone-record-skill` 是电话录音相关技能

## 内部命令

以下命令是 **Skill 内部路由动作**，用于自动探测、匹配、读取和应用云端 skill，**不是要求用户显式输入的 CLI 命令**。

### 1. list - 列出云端可用的 Skills

| 命令 | 说明 |
|------|------|
| `list` | 内部调用：列出云端所有可用的 skills |
| `show <name>` | 内部调用：查看指定 skill 的详细内容 |
| `apply <name>` | 内部调用：应用云端 skill 执行任务 |
| `refs <name>` | 内部调用：查看 skill 的引用文件 |

**内部使用示例**：
- `list` → 列出云端 skills：`telephone-record-skill`、`user-profile-analysis-skill` ...
- `show telephone-record-skill` → 查看该 skill 的 `SKILL.md` 内容
- `apply telephone-record-skill` → 应用该 skill 处理用户任务
- `refs telephone-record-skill` → 查看该 skill 的 `references` 目录

### 2. show - 查看云端 Skill 详情

当内部路由需要了解某个云端 skill 的具体内容时：

1. 先获取该 skill 的 `manifest.json`，确认 `SKILL.md` 存在并作为当前版本的索引依据：

```bash
curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/{skill_name}/manifest.json
```

2. 如果 `manifest.json` 不存在或返回 404，则进入兼容模式，直接读取 `SKILL.md`

3. 再读取 `SKILL.md`：

```bash
curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/{skill_name}/SKILL.md
```

将 `{skill_name}` 替换为实际的 skill 名称（如 `telephone-record-skill`）。

### 3. apply - 应用云端 Skill

`apply <name>` 是内部执行动作，不要求用户显式输入。应用流程：

1. **获取目标 skill 的 `manifest.json`**（必须首先执行，作为该 skill 的文件索引和更新依据）：
   ```bash
   curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/{skill_name}/manifest.json
   ```

2. **获取 SKILL.md**：
   ```bash
   curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/{skill_name}/SKILL.md
   ```

3. 解析 `manifest.json` 和 `SKILL.md`，识别本次任务真正需要的引用文件（如 `references/`、`scripts/`、`config/`）

4. 先检查该 skill 在 `SKILL.md` 中是否声明了额外的认证要求（如 API Key、Token、本地凭证文件）。如有要求，先处理认证，再继续执行文件同步和任务调用

5. **默认使用本地 `sync_required_files.py`** 执行 `manifest.json` 校验、缓存复用和按需下载（使用绝对路径，避免工作目录不一致导致找不到脚本）：
   ```bash
   python3 ~/.cursor/skills/zhenai-biz-skills/scripts/sync_required_files.py \
     --skill-name {skill_name} \
     --base-url http://42.193.182.174:8090/skills \
     --local-dir /tmp/zhenai-skill-cache \
     --files SKILL.md references/REFERENCE.md scripts/handler.py
   ```

6. 如果目标 skill 的 `manifest.json` 不存在或返回 404，则进入兼容模式：读取 `SKILL.md` 后，只按需下载本次真正需要的文件

7. 在兼容模式下，如果 skill 引用了其他文件，**必须按需并行批量获取**：
   ```bash
   # 在同一轮并行 tool call 中只下载本次真正需要的文件，禁止逐个串行下载
   curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/{skill_name}/references/REFERENCE.md
   curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/{skill_name}/scripts/handler.py
   ```

8. **根据 Skill 类型选择执行方式**：
   - **文档型 Skill**（仅含 SKILL.md + references）：优先复用本地缓存；如云端 `manifest.json` 中对应文件的 hash 与本地 `manifest.json` 不一致，则仅更新本次需要的文件后执行
   - **脚本型 Skill**（含 scripts/ 目录）：优先复用 `/tmp/{skill_name}/` 下已缓存脚本；如云端 `manifest.json` 中对应文件的 hash 与本地 `manifest.json` 不一致，则仅更新变更文件后执行；入口文件、参数传递和结果判定由 LLM 结合 `manifest.json` 与 SKILL.md 自主判断

9. **【必须】完成用户任务回复后，立即执行网关自更新（Step 4）**：
   ```bash
   python3 - <<'PY'
   import json, subprocess, sys, urllib.request
   from pathlib import Path
   BASE = 'http://42.193.182.174:8090/skills'
   SKILL = 'zhenai-biz-skills'
   LOCAL_DIR = str(Path.home() / '.cursor/skills')
   SYNC = str(Path.home() / '.cursor/skills/zhenai-biz-skills/scripts/sync_required_files.py')
   try:
       manifest = json.loads(urllib.request.urlopen(f'{BASE}/{SKILL}/manifest.json', timeout=15).read())
       files = list(manifest['files'].keys())
   except Exception:
       files = ['SKILL.md']
   r = subprocess.run([sys.executable, SYNC, '--skill-name', SKILL,
       '--base-url', BASE, '--local-dir', LOCAL_DIR, '--files', *files],
       capture_output=True, text=True)
   print(r.stdout or r.stderr)
   PY
   ```
   - `downloaded` 为空 → 静默，不向用户提及
   - `downloaded` 非空 → 提示：「网关已更新，下次对话生效。」
   - 网络失败 → 静默跳过

### 4. refs - 查看云端 Skill 的引用文件

某些 skill 可能包含额外的参考文档：

```bash
# 先获取 skill 的 manifest.json，确认可用引用文件
curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/{skill_name}/manifest.json

# 再按需读取特定引用文件
curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/{skill_name}/references/{filename}
```

如果 `manifest.json` 不存在或返回 404，则进入兼容模式，仅按本次任务需要读取对应引用文件。只读取本次任务真正需要的引用文件，不因为存在 `references/` 目录而整体下载。

## 使用示例

### 示例 1：列出所有云端 skills

**用户输入**：
"云端有哪些技能？"

**内部动作**：
- 执行 `list`

**执行要点**：
```bash
python3 - <<'PY'
import re
import urllib.request

BLACKLIST = {'compass-skills-service', 'zhenai-biz-skills'}

html = urllib.request.urlopen('http://42.193.182.174:8090/skills/', timeout=30).read().decode('utf-8', 'ignore')
for name in sorted(set(re.findall(r'href="([^"]+)/"', html)) - {'..'}  - BLACKLIST):
    print(name)
PY
```

### 示例 2：自动匹配并应用 telephone-record-skill

**用户输入**：
"帮我查一下电话录音相关数据"

**内部动作**：
- 执行 `list`
- 语义匹配到 `telephone-record-skill`
- 执行 `apply telephone-record-skill`

**执行要点**：
1. 获取 skills 列表并完成语义匹配
2. 先获取 `telephone-record-skill` 的 `manifest.json`
3. 获取该 skill 的 `SKILL.md`
4. 默认调用 `scripts/sync_required_files.py` 完成按需同步；仅在 `manifest.json` 缺失时退回兼容模式
5. 按照 skill 中的指导完成电话录音相关查询或分析

### 示例 3：查看指定 skill 详情

**用户输入**：
"看看电话录音相关 skill 的内容"

**内部动作**：
- 语义匹配到 `telephone-record-skill`
- 执行 `show telephone-record-skill`

**执行要点**：
```bash
curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/telephone-record-skill/manifest.json
curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/telephone-record-skill/SKILL.md
```

## 性能优化

以下规则从实际使用中提炼，适用于所有云端 Skill 的加载与执行。

### curl 超时控制（强制）

**所有 curl 请求必须携带超时参数**，防止单个请求阻塞整个流程：

```bash
curl -s --connect-timeout 10 --max-time 30 <url>
```

- `--connect-timeout 10`：连接超时 10 秒，快速识别网络不通
- `--max-time 30`：总超时 30 秒，防止响应挂起导致分钟级阻塞

### 并行下载（强制）

当一个 Skill 包含多个文件时，**必须使用并行工具调用**同时下载，而非逐个串行：

```
✅ 正确：在同一轮 tool call 中并行发起 SKILL.md、config.py、handler.py 的下载
❌ 错误：先下载 SKILL.md → 等完成 → 再下载 config.py → 等完成 → 再下载 handler.py
```

典型场景：一个含 5 个文件的 Skill，串行下载需 ~10s，并行仅需 ~2s。

### manifest 校验优先（必须）

在读取或执行某个 skill 前，**必须先获取该 skill 的 `manifest.json`**，不要仅凭本地目录是否存在来判断缓存是否可直接复用：

```bash
curl -s --connect-timeout 10 --max-time 30 http://42.193.182.174:8090/skills/{skill_name}/manifest.json
```

用途：

- 确认该 skill 包含哪些文件
- 获取文件 hash、size 等元信息
- 判断本次需要使用的文件是否需要更新
- 作为云端版本记录，与本地 `manifest.json` 做对比

### 按需缓存策略

当 Skill 包含 `references/` 或 `scripts/` 文件时，按以下策略处理：

1. **首次使用**：先获取 `manifest.json` 和 `SKILL.md`，再按 SKILL.md 指引下载本次真正需要的文件到 `/tmp/{skill_name}/`

2. **重复使用**：再次获取远端 `manifest.json`，仅校验本次会使用的文件；hash 一致则直接复用，hash 不一致才重新下载
   - 这里的“校验”特指**比较云端 `manifest.json` 与本地 `manifest.json` 中对应条目的 hash**
   - 不需要重新计算本地文件内容 hash
   - 文件成功复用或成功更新后，需要同步更新本地 `manifest.json` 中对应条目
   - `sync_required_files.py` 内置按 skill 的 manifest 锁，避免并发任务写回本地 `manifest.json` 时互相覆盖

3. **未使用文件不下载**：不要因为某个 skill 目录下还存在其他文件，就提前全部拉取

4. **SKILL.md 默认实时获取**：Skill 定义文件默认每次从云端读取；如后续确认也纳入 `manifest.json` 管理，可按 hash 判断是否更新

> 脚本缓存可将重复调用的耗时从 ~60s 降至 ~5s（仅保留数据查询和 AI 分析时间）。

### 默认：使用本地同步脚本（生产）

对于支持 `manifest.json` 的 skill，默认使用本地脚本执行文件级缓存复用和按需下载：

```bash
python3 ~/.cursor/skills/zhenai-biz-skills/scripts/sync_required_files.py \
  --skill-name {skill_name} \
  --base-url http://42.193.182.174:8090/skills \
  --local-dir /tmp/zhenai-skill-cache \
  --files SKILL.md references/REFERENCE.md scripts/handler.py
```

该脚本会：

- 先下载目标 skill 的 `manifest.json`
- 只比较本次需要文件在“云端 manifest / 本地 manifest”中的 hash 是否变化
- 只下载缺失或变更的文件
- 以原子写入方式更新本地缓存
- 对成功复用或成功更新的文件，同步刷新本地 `manifest.json` 对应条目
- 返回结构化 JSON 结果，便于后续执行逻辑判断

如果远端 skill 尚未提供 `manifest.json`，再退回 `curl` 直读与按需下载模式。

### 依赖预检（推荐）

在执行脚本前，先检查 SKILL.md 中声明的依赖是否已安装，避免执行到一半才失败：

```bash
python3 -c "import pymysql" 2>/dev/null && echo "OK" || echo "MISSING"
```

如缺失，先安装再执行，不要跳过。

### `python3` 缺失时的处理

默认路径依赖 `python3`。执行本地同步脚本前，先检查 `python3` 是否可用：

```bash
python3 --version
```

处理规则如下：

1. **已安装 `python3`**：直接走默认路径，使用 `scripts/sync_required_files.py`
2. **未安装 `python3`**：先提示用户是否自动安装（推荐）
3. **用户同意安装**：由 Agent 自动完成安装；不要把安装步骤交给用户手动执行
4. **用户明确拒绝安装**：退回 `curl` 兼容模式，继续完成任务，但不使用本地同步脚本

安装时遵循以下原则：

- 优先使用系统原生命令或官方推荐方式自动安装
- macOS 与 Windows 分别按各自平台适配安装方式
- 安装完成后重新检查 `python3 --version`
- 若自动安装失败，再向用户报告，不要静默跳过

### 远端 Skill 鉴权与服务级缓存

每个远端 skill 都可以在自己的 `SKILL.md` 中声明认证要求，例如：

- API Key
- Token
- 本地凭证文件
- 特定环境变量

处理规则如下：

1. 执行目标 skill 前，先读取该 skill 的 `SKILL.md`，识别是否声明了认证要求
2. 如果需要认证，先检查本地是否已存在该服务的有效凭证
3. 如果同一后端服务下的多个 skill 共用同一种认证方式，应按**服务维度**复用凭证缓存，避免用户重复输入
4. 如果没有有效凭证，再向用户索取；不要在未认证通过时直接执行数据查询或分析
5. 不在对话中回显完整密钥，不把密钥写入 `SKILL.md`、测试文件或仓库
6. 如果认证失败或凭证过期，提示用户重新提供或更新后再继续

缓存原则：

- 优先按“服务”而不是按“skill 名”缓存凭证
- 本地缓存仅保存当前用户可用的认证信息
- 仅在同一服务可复用时才复用，不跨服务混用

### 失败重试

| 失败场景 | 处理策略 |
|---------|---------|
| curl 超时（exit code 28） | kill 旧进程，立即重试 1 次 |
| curl 连接拒绝（exit code 7） | 提示用户检查网络/VPN |
| 返回空内容 | 等待 2s 后重试 1 次 |
| 重试仍失败 | 停止并向用户报告，不要静默跳过 |

## 注意事项

1. **优先读取 `manifest.json`**：每次使用目标 skill 时，先获取该 skill 的 `manifest.json`，再与本地 `manifest.json` 比较本次需要文件的 hash 是否变化
2. **SKILL.md 默认实时读取**：每次使用时从云端获取最新内容，确保版本一致
3. **文件按需读取**：如果 SKILL.md 中引用了其他文件，只读取本次任务真正需要的文件
4. **脚本文件可缓存**：含 `scripts/` 的 Skill，脚本文件缓存到 `/tmp/` 下复用，但是否复用需以“云端 `manifest.json` / 本地 `manifest.json` 的 hash 对比”为准
5. **网络依赖**：此功能需要网络连接，如果无法访问云端服务器，应提示用户检查网络
6. **本地 `manifest.json` 的语义**：记录的是“本地已成功同步到的文件版本”，不是远端 `manifest.json` 的简单镜像

## 错误处理

- 如果 curl 返回空内容或超时，按"失败重试"策略处理
- 如果请求的 skill 不存在，提示用户使用 `list` 命令查看可用的 skills
- 如果 skill 内容格式异常，尝试直接展示原始内容让用户判断

---

## ⚠️ 网关自更新【强制，不得遗漏】

> 本网关（`zhenai-biz-skills`）自身也托管在云端。**每次成功执行 apply（Step 3）并向用户回复后，必须立即执行本节的自更新命令。这是保证本地网关与云端同步的唯一机制，遗漏即意味着本地规则落后于云端版本。**
>
> **核心原则：用户数据查询优先，自更新紧随其后，二者缺一不可。**

### 触发时机

**仅在以下条件全部满足时触发**：

1. 当前会话成功调用了云端 Skill（即 Step 3 apply 流程正常完成）
2. 用户的主要任务已完成并已回复
3. 网络可用

**不触发的情况**：纯 `list` / `show` 查看操作、任务执行失败、网络不可用。

### 执行命令（必须执行）

先从远端 `manifest.json` 动态获取完整文件列表，再同步所有文件。`SKILL.md` 和 `manifest.json` 始终存在于根目录，其余文件以实际 manifest 为准，不硬编码。

```bash
python3 - <<'PY'
import json, subprocess, sys, urllib.request
from pathlib import Path

BASE = 'http://42.193.182.174:8090/skills'
SKILL = 'zhenai-biz-skills'
LOCAL_DIR = str(Path.home() / '.cursor/skills')
SYNC = str(Path.home() / '.cursor/skills/zhenai-biz-skills/scripts/sync_required_files.py')

try:
    manifest = json.loads(urllib.request.urlopen(f'{BASE}/{SKILL}/manifest.json', timeout=15).read())
    files = list(manifest['files'].keys())
except Exception:
    files = ['SKILL.md']  # 网络异常保底：至少同步 SKILL.md

r = subprocess.run(
    [sys.executable, SYNC, '--skill-name', SKILL,
     '--base-url', BASE, '--local-dir', LOCAL_DIR, '--files', *files],
    capture_output=True, text=True
)
print(r.stdout or r.stderr)
PY
```

### 结果处理

| sync 结果 | Agent 行为 |
|-----------|-----------|
| `downloaded` 为空 | 静默，不向用户提及 |
| `downloaded` 非空 | 一句话提示：「网关已更新，下次对话生效。」 |
| 网络失败 / 云端无此 skill | 静默跳过，不报错不提示 |

### 设计要点

- **安装目标路径**：`~/.cursor/skills/zhenai-biz-skills/`（Cursor 实际加载位置）
- **当前会话不受影响**：Cursor 在会话开始时已将 SKILL.md 读入上下文，磁盘文件更新后当前对话仍使用旧版本，下次新对话自动加载新版本
- **脚本自更新安全性**：Python 进程启动时已将 `sync_required_files.py` 加载到内存，运行期间原子替换磁盘文件不影响当前执行
- **manifest.json 复用**：使用同一套 manifest hash 比对机制，hash 一致则跳过下载
