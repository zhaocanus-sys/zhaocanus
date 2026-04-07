---
name: analysis-data-service-skill
description: |
  珍爱网数据分析服务技能。当用户需要"查询业务数据"、"查看日报"、"分析投放ROI"、
  "查询电销数据"、"查看业绩团队"、"查看门店数据"、"投放分析"、"退费查询"、
  "查看组织架构"时触发。
  加载此技能后，Agent 通过 CynosDB Libra 分析引擎（天然只读）直连查询 120+ 张业务表，
  覆盖电销、建信、邀约、门店、红娘、App、趣约会、幸福汇、广告投放、
  退费、银发、业绩团队、CRM组织架构等 14 个业务域。
metadata:
  openclaw:
    emoji: "📊"
    os: ["darwin", "win32", "linux"]
    requires:
      bins: ["python3"]
      scripts: ["handler.py"]
---

# Analysis Data Service Skill (analysis-data-service-skill)

珍爱网数据分析服务技能 — 直连 CynosDB Libra 分析引擎（天然只读），查询 14 个业务域、120+ 张业务表。

## 定位

本技能是**数据直连查询工具**，通过 CynosDB 分析引擎直接查询业务数据，并支持组织架构查询。

## 数据源

| 数据源 | 用途 | 覆盖范围 |
|--------|------|----------|
| **CynosDB 分析引擎** (Libra) | 所有查询统一走此引擎，天然只读 | compass_data + zhenai_externalContact |

### 数据源 SQL 查询明细

#### 数据引擎 (data_engine.py)

**健康检查:**

```sql
SELECT VERSION() AS ver;
SELECT COUNT(*) AS cnt FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s;
```

**查看表结构:**

```sql
SHOW COLUMNS FROM `{database}`.`{table_name}`;
```

**表行数估算:**

```sql
SELECT TABLE_ROWS FROM information_schema.TABLES
WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s;
```

**表数据查询 (query_table, 动态拼接):**

```sql
SELECT {select_clause}
FROM `{database}`.`{table_name}`
WHERE `{date_col}` = %s          -- 可选: 日期过滤
  AND `{filter_col}` = %s        -- 可选: 其他过滤条件
ORDER BY `{order_by}`            -- 可选: 排序
LIMIT %s OFFSET %s;
```

**表采样数据:**

```sql
SELECT * FROM `{database}`.`{table_name}` LIMIT %s;
```

**自由 SQL (execute_sql, 用户传入):**

```sql
USE `{database}`;
{user_sql};
```

#### 组织架构 (org_resolver.py)

**加载企微部门树:**

```sql
SELECT deptId, name, parentId FROM zhenai_externalContact.WxDepartment;
```

**按 userId 查员工:**

```sql
SELECT u.userId AS userid, u.name, u.department AS departments,
       u.position, u.workStatus AS state,
       u.workerId AS crm_worker_id, u.mobile, u.email
FROM zhenai_externalContact.WxWorkerInfo u
WHERE u.userId = %s;
```

**按姓名搜索员工:**

```sql
SELECT u.userId AS userid, u.name, u.department AS departments,
       u.position, u.workStatus AS state,
       u.workerId AS crm_worker_id, d.deptName AS crm_dept
FROM zhenai_externalContact.WxWorkerInfo u
LEFT JOIN compass_data.Worker w ON u.workerId = w.workerId
LEFT JOIN compass_data.Dept d ON w.deptId = d.deptId
WHERE u.name LIKE %s              -- %keyword%
  AND u.workStatus = 1            -- 可选: 仅在职
ORDER BY u.name LIMIT 100;
```

**解析 CRM 部门:**

```sql
SELECT d.deptName
FROM compass_data.Worker w
JOIN compass_data.Dept d ON w.deptId = d.deptId
WHERE w.workerId = %s;
```

**列出 CRM 部门:**

```sql
SELECT deptId, deptName, disabled FROM compass_data.Dept
WHERE disabled = 0                -- 可选: 仅启用
ORDER BY deptName;
```

**列出部门成员 (企微部门):**

```sql
SELECT u.userId AS userid, u.name, u.department AS departments,
       u.position, u.workStatus AS state,
       u.workerId AS crm_worker_id, d.deptName AS crm_dept
FROM zhenai_externalContact.WxWorkerInfo u
LEFT JOIN compass_data.Worker w ON u.workerId = w.workerId
LEFT JOIN compass_data.Dept d ON w.deptId = d.deptId
WHERE (FIND_IN_SET(%s, u.department) OR FIND_IN_SET(%s, u.department) ...)
  AND u.workStatus = 1
ORDER BY u.name;
```

**列出 CRM 部门成员:**

```sql
SELECT u.userId AS userid, u.name, u.position,
       u.workStatus AS state, d.deptName AS crm_dept
FROM zhenai_externalContact.WxWorkerInfo u
JOIN compass_data.Worker w ON u.workerId = w.workerId
JOIN compass_data.Dept d ON w.deptId = d.deptId
WHERE w.deptId = %s AND u.workStatus = 1
ORDER BY u.name;
```

## 功能清单

| 命令 | 说明 |
|------|------|
| `data sources` | 列出所有业务域（15个） |
| `data tables --source {key}` | 列出某业务域下的所有表 |
| `data columns --table {name}` | 查看表结构（字段名、类型、行数） |
| `data query --table {name}` | 查询业务表数据（支持日期过滤、分页） |
| `data search --keyword {kw}` | 按业务关键词搜索表 |
| `data sql --sql "..."` | 执行自由 SQL 查询 |
| `data health` | 检查分析引擎连通性 |
| `org search` | 按姓名搜索员工 |
| `org dept` | 浏览/搜索部门树 |
| `org members` | 列出部门成员 |
| `org resolve` | 按 userId 查员工详情 |
| `doctor` | 环境与连通性诊断 |

## 业务域 → 表映射

| 业务域 key | 中文名 | 表数 | 典型表 |
|-----------|--------|------|--------|
| telesale | 电话销售 | 13 | ads_za_crm_telsale_day_report_group_d |
| jianxin | 建信 | 5 | ads_za_offline_tel_operation_report_d |
| invite | 邀约 | 7 | ads_za_offline_invite_data_monitoring_result_d |
| shop | 门店 | 10 | ads_za_crm_saleworker_report_1d_result |
| hongniang | 红娘 | 19 | ads_za_offline_meet_push_d |
| app | App主站 | 7 | ads_za_app_revenue_order_d_all |
| qyh | 趣约会 | 5 | r_qyh_active_m |
| xfh | 幸福汇 | 6 | ads_za_offline_data_center_allot_d |
| advertising | 广告投放 | 20 | ads_za_ad_conversion_index_daily_d_all |
| refund | 退费 | 5 | ads_offline_service_refundinfo2_d_all |
| yf | 银发 | 1 | ads_venus_act_summary_d |
| performance | 业绩团队 | 29 | DetailSaleOrder |
| crm | CRM组织架构 | 9 | Dept, Worker, CrmSendSMS |

## 配置要求

- **pymysql**: CynosDB 数据库查询
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
# 1. 安装
bash install.sh

# 2. 检查分析引擎连通性
python3 scripts/handler.py data health

# 3. 列出所有业务域
python3 scripts/handler.py data sources

# 4. 查看电销相关表
python3 scripts/handler.py data tables --source telesale

# 5. 按关键词搜索表
python3 scripts/handler.py data search --keyword 投放ROI

# 6. 查看表结构
python3 scripts/handler.py data columns --table ads_za_crm_telsale_day_report_group_d

# 7. 查询数据（支持日期过滤）
python3 scripts/handler.py data query --table ads_za_crm_telsale_day_report_group_d --date 20260322 --limit 10

# 8. 自由 SQL
python3 scripts/handler.py data sql --sql "SELECT deptId, deptName FROM compass_data.Dept WHERE disabled=0 LIMIT 10"

# 9. 浏览组织架构
python3 scripts/handler.py org dept
```

## 数据源标识

所有查询命令的输出**第一行**均包含 `[数据源]` 标识，格式为：

```
[数据源] 技能: analysis-data-service-skill | 引擎: CynosDB Libra 分析引擎 | 库: compass_data | 表: Dept
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

**Step 1: 查询部门信息**

​```sql
SELECT deptId, deptName FROM compass_data.Dept WHERE deptName LIKE %s
​```

参数: `['%网销%']`

**Step 2: 获取在职员工**

​```sql
SELECT w.workerId, w.workerName, w.email ...
FROM compass_data.Worker w JOIN compass_data.Dept d ON w.deptId = d.deptId
WHERE w.deptId = %s AND w.dimissionDate IS NULL
​```

参数: `[33548]`
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

## 运行时数据目录

```
~/.analysis-data-service/
└── cache/
    └── dept_tree.json      # 部门树快照缓存
```

## 常见失败与处理

| 现象 | 含义 | 建议动作 |
|------|------|----------|
| `data health` 失败 | CynosDB 分析引擎不可达 | 检查网络连通性、代理设置 |
| `data query` 报 Unknown table | 表名不在注册表中 | 使用 `data search` 找正确表名 |
| `org ...` 失败 | CynosDB 无法访问 | 执行 `data health` 检查，确认网络 |
| `doctor` 报依赖缺失 | pymysql 未安装 | 执行 `pip install pymysql` |

## 数据反馈

当用户对查询结果有疑问（如"数据不对"、"和实际不一致"、"数据缺失"、"反馈数据问题"），
Agent 应按以下流程处理，**不要直接提交反馈**。

### 反馈前置过滤（必须按顺序执行）

**Step 1 — 自诊断**：先检查本次查询是否正常：
- 查询过程是否有报错/超时？→ 有则建议重试，不进入反馈
- 执行的 SQL 和表名是否正确匹配用户意图？→ 不匹配则修正重查
- 查询日期是否正确？→ 错误则修正

**Step 2 — 追问确认**：向用户确认：
- "具体是哪个字段/数值不对？"
- "你是从哪个系统对比发现的？（如 CRM、OA、其他报表）"
- 如果用户说不清具体差异 → 引导用户精确描述后重新查询，不提交反馈

**Step 3 — 结构化提交**：用户能说清楚后，调用反馈命令。
Agent 需自动从最近查询中提取 table、sql、database 填充参数。

### 命令示例

```bash
# 提交反馈
python3 scripts/handler.py feedback submit \
  --table ads_za_crm_telsale_day_report_group_d \
  --type data_inaccuracy \
  --description "3月25日电销日报的拨打量数据偏低，与CRM系统不一致" \
  --expected "CRM显示拨打量约5000" \
  --actual "查询结果显示3200" \
  --severity medium \
  --sql "SELECT * FROM compass_data.ads_xxx WHERE ftime='20260325'"

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
