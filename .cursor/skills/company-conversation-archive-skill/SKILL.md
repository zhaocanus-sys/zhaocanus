---
name: company-conversation-archive-skill
description: |
  企微会话存档统计分析工具。当用户需要"会话存档统计"、"企微消息统计"、
  "聊天数量统计"、"会话存档"时触发。
  从 MySQL 数据库读取会话存档的聚合统计数据（消息数量、类型分布、发送人排名、时段分布等），
  不展示任何聊天内容。
metadata:
  emoji: "💬"
  requires:
    bins: ["python3"]
    scripts: ["handler.py"]
---

# 企微会话存档统计技能 (company-conversation-archive-skill)

从 MySQL 数据库读取企业微信会话存档的**统计数据**。

**安全规则：本技能为纯统计模式，所有查询均为 COUNT/GROUP BY 聚合查询，不查询、不展示、不处理任何聊天内容（文本、语音、图片、文件、链接等）。**

## 功能清单

| 命令 | 说明 |
|------|------|
| `doctor` | 诊断环境依赖和数据库连接状态 |
| `list-users` | 列出有会话存档的员工 |
| `list-sessions` | 列出员工的群聊/私聊会话（仅 ID 和消息计数） |
| `stats` | 统计分析：消息数量、类型分布、发送人 TOP N、时段分布 |

## 数据源

| 数据库 | 表 | 用途 |
|--------|-----|------|
| `zhenai_externalContact` | `SessionArchiveMsgRecord_Recent` | 近三个月会话存档（默认） |
| `zhenai_externalContact` | `SessionArchiveMsgRecord` | 全量会话存档（--full 参数） |

### 数据源 SQL 查询明细

> 所有 SQL 均为聚合查询，不包含 `SELECT *` 或内容字段（msg, audioText, linkUrl 等）。

**消息类型分布 (get_message_type_stats):**

```sql
SELECT msgType, COUNT(*) AS cnt
FROM {table}
WHERE wxid = %s AND msgTimestamp >= %s AND msgTimestamp < %s
GROUP BY msgType ORDER BY cnt DESC;
```

**每日消息趋势 (get_daily_activity):**

```sql
SELECT DATE(FROM_UNIXTIME(msgTimestamp/1000)) AS msg_date, COUNT(*) AS cnt
FROM {table}
WHERE wxid = %s AND msgTimestamp >= %s AND msgTimestamp < %s
GROUP BY msg_date ORDER BY msg_date;
```

**小时分布 (get_hourly_activity):**

```sql
SELECT HOUR(FROM_UNIXTIME(msgTimestamp/1000)) AS msg_hour, COUNT(*) AS cnt
FROM {table}
WHERE wxid = %s AND msgTimestamp >= %s AND msgTimestamp < %s
GROUP BY msg_hour ORDER BY msg_hour;
```

**发送人排名 (get_sender_stats):**

```sql
SELECT COALESCE(NULLIF(roomSenderWxid,''), wxidFrom) AS sender, COUNT(*) AS cnt
FROM {table}
WHERE wxid = %s AND msgTimestamp >= %s AND msgTimestamp < %s
GROUP BY sender ORDER BY cnt DESC LIMIT 50;
```

**消息计数 (count_messages):**

```sql
SELECT COUNT(*) AS cnt FROM {table}
WHERE wxid = %s AND msgTimestamp >= %s AND msgTimestamp < %s;
```

## 依赖

- **pymysql**: MySQL 数据库驱动（必需）
- **requests**: HTTP 请求（必需）
- **ZHENAI_API_KEY**: 鉴权 API Key（必需，向管理员申请，格式 `za_xxx`；与 `scripts/auth_config.json` 做本地 API Key 校验）

## 鉴权配置（必需）

鉴权为**本地 API Key 校验**（`scripts/auth_config.json`），合法密钥对已内嵌在该文件中。

使用前需配置 API Key，二选一：

```bash
# 方式 1（推荐）：设置环境变量
export ZHENAI_API_KEY=za_xxx

# 方式 2：写入本地文件
echo "za_xxx" > ~/.zhenai-skills/api_key
```

API Key 向管理员申请，格式 `za_xxx`。鉴权配置已内嵌在 `scripts/auth_config.json`；无需为鉴权连接远程认证服务器。历史版本使用的 `~/.zhenai-skills/.auth_cache` 鉴权缓存已废弃，可忽略或删除。

## 快速开始

```bash
# 1. 安装依赖
pip install pymysql requests

# 2. 环境诊断
python scripts/handler.py doctor

# 3. 列出有存档的员工
python scripts/handler.py list-users

# 4. 搜索员工
python scripts/handler.py list-users --search 张三

# 5. 查看某员工的会话列表
python scripts/handler.py list-sessions --wxid zhangsan_zhenai.com

# 6. 统计分析（按日期）
python scripts/handler.py stats --wxid zhangsan_zhenai.com --date today

# 7. 统计分析（日期范围）
python scripts/handler.py stats --date-start 2026-03-01 --date-end 2026-03-31
```

## 近三月 vs 全量数据

默认使用 `SessionArchiveMsgRecord_Recent`（近三个月），查询更快。
加 `--full` 参数切换到 `SessionArchiveMsgRecord`（全量数据）：

```bash
python scripts/handler.py list-users --full
python scripts/handler.py stats --wxid ID --date 2025-01-01 --full
```

## 数据源标识

所有查询命令的输出**第一行**均包含 `[数据源]` 标识，格式为：

```
[数据源] 技能: company-conversation-archive-skill | 引擎: CynosDB | 库: zhenai_externalContact | 表: SessionArchiveMsgRecord_Recent
```

Agent 在向用户返回查询结果时，**必须**将此行信息转述给用户，告知数据来自哪个技能、哪个引擎、哪个库表，避免用户对数据来源产生疑惑。

### 查询 SQL 展示（强制）

除 `[数据源]` 外，命令输出中还包含 `[查询SQL]` 和 `[查询参数]` 行，记录了每条实际执行的 SQL 语句。Agent **必须**将这些信息一并展示给用户。

**展示规则：**

1. 将所有 `[查询SQL]` 按执行顺序收集，**去重后**以 SQL 代码块形式展示
2. 对应的 `[查询参数]` 跟在 SQL 后面，用行内代码标注
3. 如果同一条 SQL 被多次执行（仅参数不同），只展示一次 SQL 模板 + 说明执行了 N 次
4. 放在数据结果之前，使用「查询逻辑」作为小标题

**Agent 自行编写脚本时的规则：**

如果 Agent 绕过 handler.py 直接编写 Python 脚本查询数据库，**也必须**遵循以上展示规范：
- 在结果中补充查询逻辑摘要，列出执行的 SQL 和参数
- 禁止只展示数据结果而不展示查询过程
- **禁止使用 SELECT * 或查询任何内容字段（msg, audioText, linkUrl, fileName 等）**

### 数据反馈提醒（强制）

Agent 在**每次**向用户返回查询结果时，**必须**在回复末尾附带以下反馈提醒区块：

```
> 📝 如数据与实际不符，可告知我"反馈数据问题"，我将协助你提交核实请求。
```

**规则：**

1. 无论使用 handler.py 命令还是 Agent 自行编写脚本查询，都必须在结果末尾展示此提醒
2. 此提醒使用 blockquote（`>`）格式，与正文内容视觉区分
3. 禁止省略此提醒，即使用户未提出数据疑问

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| 数据库连接失败 | 网络不通或无 VPN | 确认可访问腾讯云数据库 |
| list-users 返回 0 人 | 存档表中无数据 | 确认数据已写入 |
| stats 返回 0 条 | wxid 不正确或该日期无数据 | 先用 list-users 确认 wxid |

## 数据反馈

当用户对查询结果有疑问（如"数据不对"、"和实际不一致"、"数据缺失"、"反馈数据问题"），
Agent 应按以下流程处理，**不要直接提交反馈**。

### 反馈前置过滤（必须按顺序执行）

**Step 1 — 自诊断**：先检查本次查询是否正常：
- 查询过程是否有报错/超时？→ 有则建议重试，不进入反馈
- 执行的 SQL 和表名是否正确匹配用户意图？→ 不匹配则修正重查
- wxid 是否正确？→ 错误则修正

**Step 2 — 追问确认**：向用户确认：
- "具体是哪个统计指标不对？"
- "你是从哪里对比发现的？（如企微客户端、其他系统）"
- 如果用户说不清具体差异 → 引导用户精确描述后重新查询，不提交反馈

**Step 3 — 结构化提交**：用户能说清楚后，调用反馈命令。
Agent 需自动从最近查询中提取 table、sql、database 填充参数。

### 命令示例

```bash
# 提交反馈
python3 scripts/handler.py feedback submit \
  --table SessionArchiveMsgRecord_Recent \
  --type missing_data \
  --description "张三的3月20日消息统计为0，但企微客户端能看到聊天" \
  --expected "应有约50条消息" \
  --actual "统计返回0条" \
  --severity medium

# 查看反馈列表
python3 scripts/handler.py feedback list

# 查询反馈状态
python3 scripts/handler.py feedback status --id FB-20260325-a1b2c3
```

### 问题类型说明

| 类型 | 说明 |
|------|------|
| `data_inaccuracy` | 数据不准确（默认） |
| `missing_data` | 数据缺失 |
| `stale_data` | 数据未更新/过时 |
| `wrong_format` | 数据格式错误 |
| `other` | 其他问题 |

## 维护者

- 管理员（如需帮助请联系管理员）
