---
name: telephone-record-skill
description: |
  电话录音查询工具。当用户需要"查询电话录音"、"查看录音转写"、"电销录音"、
  "电红录音"、"400录音"、"AI客服录音"、"外呼录音"、"退费语音"、
  "呼出明细"、"通话录音"、"录音转写"、"callin"、"通话记录"时触发。
  加载此技能后，Agent 通过 MySQL 查询 7 类电话录音数据，展示通话元数据（通话人、
  时间、时长、状态等），录音文本和录音文件地址不可暴露，仅可用于统计计数。
metadata:
  openclaw:
    emoji: "📞"
    os: ["darwin", "win32", "linux"]
    requires:
      bins: ["python3"]
      scripts: ["handler.py"]
---

# 电话录音技能 (telephone-record-skill)

通过 MySQL 查询 7 类电话录音数据。**可展示通话元数据，录音文本和录音地址不可暴露。**

## 定位

本技能是**录音数据查询工具**，直接从数据库读取通话元数据（通话人、时间、时长、状态等），并给出环境和数据库的诊断提示。

**安全规则：录音文本（transcription）、录音文件地址（record_url）等敏感字段在查询和详情中已自动屏蔽，仅可通过 `count` 命令做统计计数。**

## 支持的录音类型

| 类型 key | 中文名 | 别名 | 数据库.表 |
|----------|--------|------|-----------|
| `telsales` | 电销录音 | 电话销售录音, 电销 | compass_data.telSales_call_transcription |
| `matchmaker` | 电红录音 | 电话红娘录音, 电红 | compass_data.matchmaker_call_transcription |
| `callin` | 400客服录音 | 客服录音, 400录音, callin | compass_data.callin_call_transcription |
| `voicefox` | AI客服录音 | AI客服, voicefox | zhenai_externalContact.voicefox_call_records |
| `callout` | 外呼录音转写 | 外呼录音, 外呼转写 | compass_data.CallOutRecordTextResult |
| `refund` | 珍爱通退费语音 | 退费语音, 珍爱通退费 | compass_data.refund_approval_zhenaitong_ai |
| `callout_detail` | 呼出明细 | 呼出详情, 外呼明细 | compass_data.CalloutDetail |

### 数据源 SQL 查询明细

> 以下 `{database}`.`{table}` 根据录音类型不同而变化，详见上方"支持的录音类型"表。

**表可达性探测 (probe_table):**

```sql
SELECT COUNT(*) AS cnt FROM `{database}`.`{table}` LIMIT 1;
```

**表结构查看 (get_schema):**

```sql
DESCRIBE `{database}`.`{table}`;
```

**录音列表查询 (query, 动态拼接):**

```sql
SELECT `{id_col}` AS id,
       `{worker_name_col}` AS worker_name,
       `{worker_id_col}` AS worker_id,
       `{member_id_col}` AS member_id,
       `{time_col}` AS call_time,
       `{duration_col}` AS duration
FROM `{database}`.`{table}`
WHERE `{time_col}` >= %s AND `{time_col}` < %s     -- 可选: 单日/日期范围
  AND `{worker_name_col}` LIKE %s                   -- 可选: 坐席姓名模糊匹配
  AND `{worker_id_col}` = %s                        -- 可选: 坐席ID
  AND `{member_id_col}` = %s                        -- 可选: 会员ID
  AND `{transcription_col}` LIKE %s                 -- 可选: 关键词搜索
ORDER BY `{order_col}` DESC
LIMIT %s OFFSET %s;
```

**录音计数 (count):**

```sql
SELECT COUNT(*) AS cnt FROM `{database}`.`{table}`
WHERE `{time_col}` >= %s AND `{time_col}` < %s     -- 可选: 同 query
  AND `{worker_name_col}` LIKE %s                   -- 可选
  AND `{worker_id_col}` = %s                        -- 可选
  AND `{member_id_col}` = %s                        -- 可选
  AND `{transcription_col}` LIKE %s;                -- 可选
```

**录音详情 (get_detail, 排除敏感字段):**

```sql
SELECT `{non_sensitive_cols}` FROM `{database}`.`{table}` WHERE `{id_col}` = %s;
```

## 功能清单

| 命令 | 说明 |
|------|------|
| `types` | 列出 7 种录音类型及别名 |
| `query <type>` | 按条件查询录音列表（不含录音文本/地址） |
| `detail <type> <id>` | 查看单条录音详情（不含录音文本/地址） |
| `count <type>` | 按条件统计录音数量 |
| `schema <type>` | 查看指定录音表的字段结构 |
| `doctor` | 诊断依赖安装和数据库连通性 |

## 快速开始

```bash
# 1. 安装依赖
python -m pip install pymysql

# 2. 诊断环境和数据库
python scripts/handler.py doctor

# 3. 列出录音类型
python scripts/handler.py types

# 4. 查询电销录音（按日期）
python scripts/handler.py query telsales --date 2026-03-19

# 5. 查询 400 客服录音（按坐席）
python scripts/handler.py query callin --worker 张三

# 6. 按日期范围查询
python scripts/handler.py query matchmaker --date-start 2026-03-01 --date-end 2026-03-15

# 7. 按关键词搜索转写内容
python scripts/handler.py query telsales --keyword 退款

# 8. 查看完整录音详情
python scripts/handler.py detail telsales 43082

# 9. 查看表结构
python scripts/handler.py schema voicefox
```

## 查询参数

| 参数 | 说明 |
|------|------|
| `--date` | 精确日期 (YYYY-MM-DD)，支持 today / yesterday |
| `--date-start` | 起始日期 |
| `--date-end` | 结束日期 |
| `--worker` | 坐席姓名（模糊匹配） |
| `--worker-id` | 坐席 ID |
| `--member-id` | 会员 ID |
| `--keyword` | 转写文本关键词搜索 |
| `--limit` | 返回条数上限（默认 50） |
| `--offset` | 分页偏移 |

## 配置要求

- **pymysql**: MySQL 数据库查询
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

## 数据源标识

所有查询命令的输出**第一行**均包含 `[数据源]` 标识，格式为：

```
[数据源] 技能: telephone-record-skill | 引擎: CynosDB | 库: compass_data | 表: telSales_call_transcription
```

Agent 在向用户返回查询结果时，**必须**将此行信息转述给用户，告知数据来自哪个技能、哪个引擎、哪个库表，避免用户对数据来源产生疑惑。

### 查询 SQL 展示（强制）

除 `[数据源]` 外，命令输出中还包含 `[查询SQL]` 和 `[查询参数]` 行，记录了每条实际执行的 SQL 语句。Agent **必须**将这些信息一并展示给用户。

**展示规则：**

1. 将所有 `[查询SQL]` 按执行顺序收集，**去重后**以 SQL 代码块形式展示
2. 对应的 `[查询参数]` 跟在 SQL 后面，用行内代码标注
3. 如果同一条 SQL 被多次执行（仅参数不同），只展示一次 SQL 模板 + 说明执行了 N 次
4. 放在数据结果之前，使用「查询逻辑」作为小标题

**展示格式示例：**

```
### 查询逻辑

**Step 1: 统计录音总数**

​```sql
SELECT COUNT(*) AS cnt FROM compass_data.telSales_call_transcription
WHERE created_at >= %s AND created_at < %s AND worker_name LIKE %s
​```

参数: `['2026-03-20', '2026-03-21', '%张三%']`

**Step 2: 查询录音列表**

​```sql
SELECT id, worker_name, worker_id, member_id, created_at, LEFT(transcription, 100) AS transcription_preview
FROM compass_data.telSales_call_transcription
WHERE created_at >= %s AND created_at < %s AND worker_name LIKE %s
ORDER BY created_at DESC LIMIT %s OFFSET %s
​```

参数: `['2026-03-20', '2026-03-21', '%张三%', 50, 0]`
```

**Agent 自行编写脚本时的规则：**

如果 Agent 绕过 handler.py 直接编写 Python 脚本查询数据库，**也必须**遵循以上展示规范：
- 在结果中补充查询逻辑摘要，列出执行的 SQL 和参数
- 禁止只展示数据结果而不展示查询过程

### 数据反馈提醒（强制）

Agent 在**每次**向用户返回查询结果时，**必须**在回复末尾附带以下反馈提醒区块：

```
> 📝 如数据与实际不符，可告知我"反馈数据问题"，我将协助你提交核实请求。
```

**规则：**

1. 无论使用 handler.py 命令还是 Agent 自行编写脚本查询，都必须在结果末尾展示此提醒
2. 此提醒使用 blockquote（`>`）格式，与正文内容视觉区分
3. 禁止省略此提醒，即使用户未提出数据疑问

## 常见失败与处理

| 现象 | 含义 | 建议动作 |
|------|------|----------|
| `doctor` 报 pymysql 未安装 | 依赖缺失 | `python -m pip install pymysql` |
| `doctor` 报数据库连接失败 | 网络不通或凭证问题 | 确认 VPN/内网连接和数据库白名单 |
| `doctor` 报某张表不可访问 | 数据库用户权限不足 | 联系 DBA 确认读权限 |
| `query` 返回空 | 查询条件无匹配 | 调整日期范围或去掉过滤条件 |

## 数据反馈

当用户对查询结果有疑问（如"数据不对"、"和实际不一致"、"数据缺失"、"反馈数据问题"），
Agent 应按以下流程处理，**不要直接提交反馈**。

### 反馈前置过滤（必须按顺序执行）

**Step 1 — 自诊断**：先检查本次查询是否正常：
- 查询过程是否有报错/超时？→ 有则建议重试，不进入反馈
- 录音类型是否选对了？→ 不匹配则修正重查
- 查询日期和过滤条件是否正确？→ 错误则修正

**Step 2 — 追问确认**：向用户确认：
- "具体是哪条录音/哪个字段不对？"
- "你是从哪里对比发现的？（如 CRM 系统、其他报表）"
- 如果用户说不清具体差异 → 引导用户精确描述后重新查询，不提交反馈

**Step 3 — 结构化提交**：用户能说清楚后，调用反馈命令。
Agent 需自动从最近查询中提取 table、sql、database 填充参数。

### 命令示例

```bash
# 提交反馈
python3 scripts/handler.py feedback submit \
  --table telSales_call_transcription \
  --type data_inaccuracy \
  --description "ID=43082的电销录音转写内容不完整，只有前半段" \
  --expected "完整通话约15分钟" \
  --actual "转写文本只有前3分钟" \
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
