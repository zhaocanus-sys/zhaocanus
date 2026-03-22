# CLAUDE.md — 珍爱网智慧助理 开发指南

> 本文档面向AI助手（Claude、Cursor等），说明代码库结构、开发规范和关键约定。
> 最后更新：2026-03-22

---

## 一、项目概述

**项目名称**：珍爱网智慧助理（Zhenai Intelligent Assistant）
**语言**：Python 3（纯数据分析与报告生成，无Web框架）
**核心职责**：为珍爱网5条业务线每日自动生成运营日报，包含AI诊断、知识碰撞洞见，并通过邮件分发给管理层。

---

## 二、目录结构

```
/home/user/zhaocanus/
├── generate_jianxin_full_report.py    # 建信日报入口
├── generate_telesale_full_report.py   # 电销日报入口
├── generate_hongniang_full_report.py  # 红娘日报入口
├── generate_shop_full_report.py       # 门店日报入口
├── generate_app_full_report.py        # APP日报入口
├── app_report_data.py                 # APP数据聚合层
├── app_report_html.py                 # APP HTML渲染层
├── requirements.txt                   # Python依赖（requests>=2.31.0）
├── restore.sh                         # 自动化部署脚本
├── reports/                           # 生成的HTML报告输出目录
├── agent_system/                      # 核心引擎
│   ├── config/
│   │   ├── __init__.py                # fact(), preferences(), api_config()
│   │   ├── facts.json.template        # 凭证模板（提交到git）
│   │   └── facts.json                 # 实际凭证（.gitignore，不提交）
│   ├── actions/
│   │   ├── api_client.py              # HTTP API封装（14个方法，ThreadPoolExecutor）
│   │   ├── email_sender.py            # SMTP邮件发送（TLS）
│   │   ├── memory_manager.py          # ReportMemory（SQLite情景记忆）
│   │   ├── report_sparkline.py        # SVG Sparkline生成器
│   │   └── report_exporter.py         # HTML文件导出
│   ├── knowledge_base/                # 领域知识与规则
│   │   ├── report_design_principles_kb.md
│   │   ├── zhao_management_wisdom_kb.md
│   │   ├── report_template_benchmark.md
│   │   ├── report_rules_app.md
│   │   ├── book_index.json
│   │   └── frameworks/
│   │       ├── collision_matrices.json
│   │       ├── data_collision_rules.json
│   │       └── logic_collision_rules.json
│   ├── engines/
│   │   ├── collision_engine.py        # 知识碰撞框架
│   │   └── analysis_pipeline.py       # 数据分析流水线
│   └── agents/
│       └── data_expert.py             # DataExpert智能体人格
├── docs/                              # 旧版文档
├── SETUP.md                           # 3步快速开始
├── DEPLOY.md                          # 迁移/部署指南
└── CLAUDE_REPORT_GUIDE.md             # 20KB完整技术指南（核心参考文档）
```

---

## 三、运行方式

### 3.1 安装依赖

```bash
pip3 install -r requirements.txt
```

### 3.2 配置凭证

```bash
cp agent_system/config/facts.json.template agent_system/config/facts.json
# 编辑 facts.json，填入 API key、SMTP凭证、邮件收件人列表
```

### 3.3 生成日报

```bash
# 格式：python3 generate_{team}_full_report.py --date YYYY-MM-DD [--no-email]
python3 generate_jianxin_full_report.py --date 2026-03-22 --no-email
```

- `--date YYYY-MM-DD`：指定报告日期（必填）
- `--no-email`：只导出HTML并在浏览器打开，不发邮件
- 不加 `--no-email`：自动发邮件给赵总

---

## 四、5条业务线

| 业务线 | 脚本 | API team | 负责人 | 核心职能 |
|--------|------|----------|--------|----------|
| 建信 | `generate_jianxin_full_report.py` | `jianxin` | 程朴娟 | IM深度沟通，养鱼传递信任 |
| 电销 | `generate_telesale_full_report.py` | `telesale` | 多部门 | 电话转化，核心利润中心 |
| 红娘 | `generate_hongniang_full_report.py` | `hongniang` | — | VIP一对一服务，品牌生命线 |
| 门店 | `generate_shop_full_report.py` | `shop` | — | 线下签单，高客单价 |
| APP | `generate_app_full_report.py` | `app` | — | 在线付费产品，现金流压舱石 |

---

## 五、数据API

### 5.1 基础配置

- **Base URL**：`http://43.138.47.115:8600`
- **认证**：`X-API-Key` 请求头（从 `api_config()` 获取）
- **客户端代码**：`agent_system/actions/api_client.py`

### 5.2 核心函数

```python
from agent_system.actions.api_client import APIClient
api = APIClient()

api.daily(team, date)                  # GET /api/v1/team/{team}/daily?date=YYYYMMDD
api.query(team, table_role, date)      # GET /api/v1/team/{team}/query?table_role=...
api.trend(team, days=14)               # GET /api/v1/team/{team}/trend?days=14
api.parallel_fetch(calls)              # ThreadPoolExecutor, max_workers=min(len,8)
api.health(team)                       # GET /api/v1/health/{team}
```

### 5.3 API响应格式

```json
{
  "rows": [{"field1": "value1", ...}, ...],
  "row_count": 10,
  "columns": ["field1", "field2", ...]
}
```

### 5.4 日期格式约定

- API接收：`YYYYMMDD`（如 `20260322`）
- 报告显示：`YYYY-MM-DD`（如 `2026-03-22`）

### 5.5 数据解析通用函数

每个报告脚本都定义以下安全解析函数：

```python
def parse_rows(resp):
    if not resp or "error" in resp:
        return []
    return resp.get("rows", [])

def safe_float(v, d=0.0): ...   # 安全转浮点
def safe_int(v, d=0): ...       # 安全转整数
```

---

## 六、报告生成流程

每个业务线报告脚本遵循相同的6步流程：

```
1. parallel_fetch(calls)   → 并行拉取今日+昨日+10天趋势API数据
2. agg_{team}(rows)        → 数据聚合（原始多行→单字典 t/p）
3. dod(key, up_good=True)  → 环比计算（返回带颜色HTML片段）
4. sparkline_svg(vals)     → 生成SVG趋势线（每个KPI卡片必须有）
5. generate_html()         → f-string大模板，直接嵌入计算变量
6. export_html() / send_report_email()  → 导出文件或发送邮件
```

### 6.1 环比颜色规则

```python
def dod(key, up_good=True):
    chg = (tv - pv) / abs(pv) * 100
    color = "#16a34a" if (chg > 0) == up_good else "#dc2626"
    # 退费率：up_good=False（上升=差）
```

### 6.2 Sparkline颜色约定

| 业务线 | Sparkline颜色 |
|--------|--------------|
| 建信/红娘/门店 | 各指标用 `#16a34a`（绿）、`#6366f1`（蓝紫）等 |
| 电销 | 暗色背景卡片，用 `rgba(255,255,255,.7)` 保证可见 |

### 6.3 情景记忆

```python
from agent_system.actions.memory_manager import ReportMemory
mem = ReportMemory()
mem.save("jianxin", DATE, today_metrics)
trend_html = mem.trend_comparison_html("jianxin", DATE, today_metrics, metric_labels)
```

数据库：`agent_system/memory.db`（SQLite，`report_episodes` 表）

---

## 七、报表14项必含模块

> 缺一不可，只进不退

1. **头部**：业务名称、日期、负责人姓名、团队规模
2. **KPI卡片**：转化流转顺序、红/黄/绿标色、人均业绩、**10天Sparkline**（必须）
3. **业务定位**：员工能力差异 + 捞取资源重点
4. **全局诊断**：环比分析、捞取资源专项、渠道/部门效率差异
5. **知识图谱诊断**：精确匹配 E01-E06/J01 等模式，不泛泛而谈
6. **因果链**：逐级损耗 + 标红最大瓶颈 + 漏斗佐证 + 杠杆预估
7. **跨领域对撞**：至少2组，框架×心理学书籍，含 📚 来源
8. **改善建议**：按预估增幅排序，每条含负责人+动作+天数+预估+来源
9. **渠道/明细表**：关键指标降序、含捞取资源行、含人均列
10. **部门明细**：自主触达 + 人均捞取 + 人均切面列
11. **TOP5深度分析**：全过程字段 + 综合评分 + 可复制性
12. **TOP5 vs BOTTOM5对比**：13+维度 + 差异倍数 + 解读 + 复制要点
13. **BOTTOM5诊断**：全过程字段 + 问题分析 + 改善建议
14. **数据→人的转向**：四维框架（技能/心态/存量管理/执行力）

---

## 八、关键命名约定

| 约定 | 示例 |
|------|------|
| 报告入口脚本 | `generate_{team}_full_report.py` |
| 数据聚合函数 | `agg_{team}(rows)` → 返回指标字典 `t` 或 `p` |
| 环比计算函数 | `dod(key, up_good=True)` |
| SVG趋势线函数 | `sparkline_svg(vals, color, width, height)` |
| 数据安全解析 | `parse_rows(resp)`, `safe_float(v)`, `safe_int(v)` |
| KPI颜色函数 | `color_kpi(val, good, bad)` → 绿/橙/红 |
| 颜色常量 | 好: `#16a34a`，警告: `#d97706`，差: `#dc2626` |
| HTML生成函数 | `generate_html()` → 返回HTML字符串 |

---

## 九、配置系统

### 9.1 facts.json（secrets，不提交git）

```json
{
  "api": {"base_url": "...", "api_key": "..."},
  "smtp": {"host": "...", "port": 465, "user": "...", "password": "..."},
  "email": {"to": ["..."], "from": "..."},
  "dept_managers": {"dept_name": "manager_name"}
}
```

### 9.2 preferences.json

存放用户偏好、执行原则、报告规范、邮件样式等非敏感配置。

### 9.3 配置加载

```python
from agent_system.config import fact, preferences, api_config
api_key = fact("api.api_key")
smtp_host = fact("smtp.host")
```

---

## 十、数据库

| 文件 | 用途 |
|------|------|
| `agent_system/memory.db` | 情景记忆（`report_episodes` 表） |
| `agent_system/config/memory_fts.db` | 全文搜索索引 |
| `zhenai_real.db` | 源数据缓存 |
| `zhenai_telesale.db` | 电销源数据缓存 |

> `.gitignore` 排除所有 `*.db` 文件，不提交。

**memory.db Schema：**

```sql
CREATE TABLE report_episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team TEXT NOT NULL,
    date TEXT NOT NULL,        -- "20260322"
    metrics TEXT NOT NULL,     -- JSON字符串
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team, date)
);
CREATE INDEX idx_team_date ON report_episodes(team, date DESC);
```

---

## 十一、赵总管理智慧（AI生成报告必须遵守）

### 11.1 第一原则

> **助手全部搞定，不得让用户执行本可由助手代劳之事。**

### 11.2 四维人员分析框架（每份报告必做）

| 维度 | 核心问题 | 数据信号 | 管理动作 |
|------|----------|----------|----------|
| 技能 | 会不会做？ | AI分、深沟率、TOP vs BOTTOM差异 | 标杆录音→话术通关→师徒带教 |
| 心态 | 愿不愿做？ | 外呼趋势、捞取主动性、连续低产 | 新人激励/老人轮岗+荣誉 |
| 存量管理 | 资源用好了吗？ | 人均存量、捞取数、回访频次 | 存量盘活+公海回流+捞取激励 |
| 执行力 | 动作落地了吗？ | 布置后数据改善幅度 | 3天无改善→绩效挂钩 |

### 11.3 评分铁律

- **建信/电销/红娘/邀约**：过程30分 + 结果70分。过程数据再好，没有成交/营业额最多30分。
- **门店**：签单率30%（≥30%合格/≥35%优秀）+ 到店产出70%（¥3000标准/¥4000良好/¥5000优秀）。

### 11.4 10条管理规则

1. 全局 vs 部门诊断必须分栏
2. 管理者姓名必须体现 + 管理视角缺失推断
3. 建议含时间维度（今日部署/坚持天数/预估提升）
4. 10天趋势 + 连续7天无改善升级P0，连续3天无动作→绩效扣分
5. 反鞭打快牛（优先中腰部提升，不压榨头部）
6. 弱依赖强闭环（业务团队可自行落地的方案优先）
7. 改善建议按预估增幅排序
8. 报告按转化流转顺序展示核心数据
9. 第一原则：助手全部搞定
10. 数据→人的分析必做（四维框架）

### 11.5 严禁事项

- 严禁提出高客单价快速转化逼签方案
- 严禁门店业务输出涉黑/涉诈/涉骗模式内容
- 报告建议必须弱依赖强闭环

---

## 十二、各业务线特殊规则

### 12.1 建信（jianxin）

- 转化流转：资源分配 → IM发信 → 用户回复 → 企微添加 → 深度跟进 → 调配电销 → 切面成交
- KPI Sparkline：`pay_amt`, `per_capita`, `reply_rate`, `wechat`, `transfer`, `proactive`, `transfer_rate`

### 12.2 电销（telesale）

- 转化流转：外呼 → 接通 → 深沟 → 签单 → 营收
- 接通率基准：18%；深沟率基准：35%
- **KPI卡片暗色背景**，Sparkline 用 `rgba(255,255,255,.7)`
- 8个部门负责人存于 `DEPT_MANAGERS` 字典

### 12.3 红娘（hongniang）

- 转化流转：VIP资源 → 通话 → 深沟 → 安排见面 → 营收
- 退费率分母：用 `pay_m`（月累计营收），**不能用日营收**（否则数字荒谬）
- API调用：`query("hongniang", "daily", date)` + `query("hongniang", "hourly", date)`

### 12.4 门店（shop）

- 转化流转：线索 → 邀约接通 → 到店 → 签单 → 营收
- 线索即日分配红线：≥80%
- 风险预警：签单率<5% + 高到店 = 高风险（偷盗嫌疑）

### 12.5 APP

- 三张数据表：`daily`（51字段）、`orders`（20字段）、`traffic`（16字段）
- 关键红线：珍心占比>80%=结构风险、退款>2%=P0治理、支付失败>40%=P0紧急、次日留存<35%=根本问题
- APP模块分为两个文件：`app_report_data.py`（数据层）+ `app_report_html.py`（渲染层）

---

## 十三、知识库与碰撞框架

```
agent_system/knowledge_base/
├── report_design_principles_kb.md    # 报告设计6大规则
├── zhao_management_wisdom_kb.md      # 赵总管理哲学
├── report_template_benchmark.md      # 14项质量检查清单
├── report_rules_app.md               # APP专项规则（8.6KB）
├── book_index.json                   # 书籍引用索引
└── frameworks/
    ├── collision_matrices.json        # 碰撞矩阵
    ├── data_collision_rules.json      # 数据碰撞规则
    └── logic_collision_rules.json     # 逻辑碰撞规则
```

报告中的跨领域对撞（第7模块）必须：
- 至少2组框架碰撞
- 每组含：框架名称 + 解释现象 + 具体动作 + 📚 书籍来源

---

## 十四、Git 工作流

### 14.1 分支规范

- 开发分支：`claude/add-claude-documentation-735NC`（当前）
- 主分支：`master`
- 远程：`http://local_proxy@127.0.0.1:41501/git/zhaocanus-sys/zhaocanus`

### 14.2 常用命令

```bash
git add <file>
git commit -m "feat: 描述改动"
git push -u origin claude/add-claude-documentation-735NC
```

### 14.3 .gitignore 排除项

```
__pycache__/
*.pyc
*.db
agent_system/config/facts.json    # 敏感凭证
agent_system/cache/               # 外部数据缓存
```

---

## 十五、关键参考文档

| 文档 | 用途 |
|------|------|
| `CLAUDE_REPORT_GUIDE.md` | **最重要**：20KB完整技术指南，含所有规则、API、HTML结构 |
| `SETUP.md` | 3步快速开始 |
| `DEPLOY.md` | 系统迁移与部署 |
| `agent_system/knowledge_base/report_template_benchmark.md` | 14项质量检查清单 |
| `agent_system/knowledge_base/zhao_management_wisdom_kb.md` | 赵总管理哲学 |
| `.cursor/skills/report-generator/SKILL.md` | Cursor IDE技能定义 |

---

## 十六、FAQ

**Q：如何添加新业务线？**
A：参考 `generate_jianxin_full_report.py`，创建 `generate_{team}_full_report.py`，实现 `agg_{team}()`、`dod()`、`generate_html()`、`main()` 四个核心函数。

**Q：Sparkline不显示或颜色看不清？**
A：电销暗色背景需用 `rgba(255,255,255,.7)` 而非纯色。检查 `report_sparkline.py` 的 `sparkline_svg()` 调用参数。

**Q：退费率数字异常（>100%）？**
A：退费率分母必须用月累计营收（`pay_m`），不能用日营收。红娘报告有此特殊处理。

**Q：facts.json 在哪里？**
A：`agent_system/config/facts.json`，不在git中。首次部署从 `facts.json.template` 复制并填入凭证。

**Q：如何验证API连通性？**
A：`api.health()` 或直接运行报告脚本加 `--no-email`，观察控制台输出。
