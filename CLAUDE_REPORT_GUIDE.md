# 珍爱网智慧助理 — 日报生成完整指南

> 本文档包含生成全部业务线日报所需的全部规则、方法、知识和代码架构。
> 目标：任何AI助手读完本文档后，能生成与现有系统同等质量的日报。
> 最后更新：2026-03-02

---

## 一、系统架构总览

### 1.1 项目路径
```
/Users/yanchen/智慧助理/
```

### 1.2 5条业务线 × 5个独立报告

| 业务线 | 脚本 | API team | 数据表 |
|--------|------|----------|--------|
| 建信 | `generate_jianxin_full_report.py` | `jianxin` | daily |
| 电销 | `generate_telesale_full_report.py` | `telesale` | daily |
| 红娘 | `generate_hongniang_full_report.py` | `hongniang` | daily + hourly |
| 门店 | `generate_shop_full_report.py` | `shop` | daily |
| APP | `generate_app_full_report.py` + `app_report_data.py` + `app_report_html.py` | `app` | daily + orders + traffic |

### 1.3 运行方式
```bash
cd /Users/yanchen/智慧助理
python3 generate_jianxin_full_report.py --date 2026-02-27 --no-email
```
- `--date YYYY-MM-DD`：指定报告日期
- `--no-email`：不发送邮件，仅导出HTML并在浏览器打开
- 不加 `--no-email` 则自动发送邮件

---

## 二、数据API接口

### 2.1 基础配置
- **Base URL**: `http://43.138.47.115:8600`
- **认证**: `X-API-Key` header（从 `agent_system/config/__init__.py` 的 `api_config()` 获取）
- **代码文件**: `agent_system/actions/api_client.py`

### 2.2 核心函数

```python
# 获取团队日报数据
daily(team, date=None, page=1, size=500)
# GET /api/v1/team/{team}/daily?date={date}&page={page}&page_size={size}

# 按表查询（红娘的hourly、APP的orders/traffic等）
query(team, table_role, date=None, page=1, size=500)
# GET /api/v1/team/{team}/query?table_role={table_role}&date={date}

# 获取趋势数据
trend(team, days=14)
# GET /api/v1/team/{team}/trend?days={days}

# 并行拉取多个API（用ThreadPoolExecutor，最多8线程）
parallel_fetch(calls)  # calls = [lambda: daily(...), lambda: query(...), ...]
```

### 2.3 API返回格式
```json
{
  "rows": [{"field1": "value1", "field2": "value2", ...}, ...],
  "row_count": 10,
  "columns": ["field1", "field2", ...]
}
```

### 2.4 日期格式
- API接收：`YYYYMMDD`（如 `20260227`）
- 报告显示：`YYYY-MM-DD`（如 `2026-02-27`）

### 2.5 数据解析通用函数
```python
def parse_rows(resp):
    if not resp or "error" in resp:
        return []
    return resp.get("rows", [])

def safe_float(v, d=0.0):  # 安全转浮点
def safe_int(v, d=0):      # 安全转整数
```

---

## 三、报告生成完整流程（以建信为例）

### 3.1 数据拉取（并行10天趋势）
```python
base_dt = datetime.datetime.strptime(DATE, "%Y%m%d")
calls = [
    lambda: daily("jianxin", DATE),              # 今日
    lambda: daily("jianxin", prev_date(DATE)),    # 昨日
]
for delta in range(9, -1, -1):                    # 10天趋势（报告日期前10天）
    d = (base_dt - datetime.timedelta(days=delta)).strftime("%Y%m%d")
    calls.append(lambda d=d: daily("jianxin", d))
results = parallel_fetch(calls)
```

### 3.2 数据聚合（agg_xxx函数）
每个业务线都有自己的聚合函数（如 `agg_jianxin`、`agg_telesale`），将API返回的多行原始数据汇总为一个字典 `t`，包含所有计算后的指标。

### 3.3 环比计算（dod函数）
```python
def dod(key, up_good=True):
    """计算今日vs昨日的环比变化，返回带颜色的HTML字符串"""
    tv = t.get(key, 0)
    pv = p.get(key, 0)
    if pv == 0: return ""
    chg = (tv - pv) / abs(pv) * 100
    # 绿色=好，红色=差（退费率反转）
```

### 3.4 Sparkline趋势线
```python
from agent_system.actions.report_sparkline import sparkline_svg

# 从10天API数据构建趋势值
trend_days = []
for i in range(10):
    day_rows = parse_rows(results[2 + i])
    trend_days.append(agg_jianxin(day_rows) if day_rows else {})

# 生成SVG
spk = {}
for key, color in [("pay_amt","#16a34a"), ("reply_rate","#6366f1"), ...]:
    vals = [float(d.get(key, 0) or 0) for d in trend_days]
    spk[key] = sparkline_svg(vals, color=color)
```

### 3.5 HTML生成（f-string模板）
每个报告用 `generate_html()` 函数，内部是一个大的f-string（`f'''...'''`），直接嵌入计算后的变量。

### 3.6 情景记忆存储
```python
from agent_system.actions.memory_manager import ReportMemory
mem = ReportMemory()
mem.save("jianxin", DATE, today_metrics)
trend_html = mem.trend_comparison_html("jianxin", DATE, today_metrics, metric_labels)
```

### 3.7 导出和发送
```python
from agent_system.actions.report_exporter import export_html
from agent_system.actions.email_sender import send_report_email

path = export_html(html, filename, open_browser=True)
send_report_email(subject, html)  # 发给赵总
```

---

## 四、报表14项必含模块（缺一不可）

> 来源：赵总确认的质量基准线，只进不退

1. **头部**：业务名称、日期、负责人姓名、团队规模
2. **KPI卡片**：按转化流转顺序排列，红/黄/绿标色，凡有团队业绩必须附人均业绩，**每个卡片含10天Sparkline趋势线**
3. **业务定位**：「{业务名}团队高业绩必须关注的重点」，含员工能力差异和捞取资源
4. **全局诊断**：含环比分析、捞取资源专项、渠道/部门效率差异
5. **知识图谱诊断模式匹配**：E01-E06/J01等精确匹配，不泛泛而谈
6. **因果链**：逐级损耗+标红最大瓶颈+漏斗佐证+杠杆预估
7. **跨领域对撞**：至少2组，用框架解释现象+具体动作+📚来源
8. **改善建议**：不限条数，按预估增幅排序，每条含负责人+动作+天数+预估+来源
9. **渠道/明细表**：按关键指标降序，含捞取资源行，含人均业绩列
10. **部门明细**：含自主触达+人均捞取+人均切面列
11. **TOP5深度分析**：全过程字段+综合评分+为什么好+可复制性
12. **TOP5 vs BOTTOM5能力差异对比**：13+维度+差异倍数+解读+复制要点
13. **BOTTOM5诊断**：全过程字段+问题分析+改善建议
14. **数据→人的转向**：四维分析（技能/心态/存量管理/执行力）

---

## 五、赵总管理智慧（最高优先级规则）

### 5.1 核心哲学
**数据是手段，人是核心。** 报表不是展示数据的工具，而是通过数据发现「人」的问题和机会。

### 5.2 四维人员分析框架（每份报表必做）

| 维度 | 核心问题 | 数据信号 | 管理动作 |
|------|----------|----------|----------|
| 技能 | 会不会做？ | AI分、深沟率、TOP vs BOTTOM差异 | 标杆录音→话术通关→师徒带教 |
| 心态 | 愿不愿做？ | 外呼趋势、捞取主动性、连续低产天数 | 新人激励/老人轮岗+荣誉 |
| 存量管理 | 资源用好了吗？ | 人均存量、捞取数、回访频次 | 存量盘活+公海回流+捞取激励 |
| 执行力 | 动作落地了吗？ | 布置后数据改善幅度 | 3天无改善→绩效挂钩 |

### 5.3 管理规则10条

1. 全局 vs 部门诊断必须分栏
2. 管理者姓名必须体现 + 管理视角缺失推断
3. 建议含时间维度（今日部署/坚持天数/预估提升）
4. 10天趋势 + 持续不改善升级处罚（连续7天→P0，3天无动作→绩效扣分）
5. 反鞭打快牛（优先中腰部提升，不压榨头部）
6. 弱依赖强闭环（业务团队可自行落地的方案优先）
7. 改善建议按预估增幅排序
8. 报告按转化流转顺序展示核心数据
9. 第一原则：助手全部搞定
10. 数据→人的分析必做（四维框架）

### 5.4 评分铁律（过程30分+结果70分）

- **建信/电销/红娘/邀约**：过程数据再好，没有成交/营业额，最多得30分。切记：过程最多30分，结果占70分。
- **门店**：100%关联业绩。30%=签单率（≥30%合格/≥35%优秀），70%=到店产出（¥3000标准/¥4000良好/¥5000优秀）。无成交率和业绩=0分。

### 5.5 公司背景（必须理解）

- 赵总2014年创立门店业务使公司扭亏为盈，2019年出国，2023年回归断臂求生
- 旧门店涉黑涉诈涉骗涉黄，必须关闭旧模式
- 当前是「大病初愈、带伤冲刺」阶段，10亿现金是生命线
- 所有建议必须弱依赖强闭环
- 严禁提出高客单价快速转化逼签的方案

### 5.6 经营哲学
- **一鱼多吃**：首单(电销)→到店(门店)→红娘配对→续费/增值
- **前端建信+后端营销**：建信做信任传递(养鱼)，电销做收割
- **风险隔离优先**：门店加盟SaaS模式，合规风险不回流总部

---

## 六、各业务线独立规则

### 6.1 建信团队（jianxin）

**定位**：IM/企微深度沟通，养鱼模式，信任传递桥梁

**转化流转**：资源分配 → IM发信 → 用户回复 → 企微添加 → 深度跟进 → 调配给电销 → 切面成交

**核心KPI**：切面业绩、月累计、人均切面、在岗人数、回复率、企微添加、调配人数、自主触达、调配转化率

**Sparkline覆盖**：pay_amt, per_capita, reply_rate, wechat, transfer, proactive, transfer_rate

**负责人**：程朴娟

**API调用**：`daily("jianxin", date)`

### 6.2 电销团队（telesale）

**定位**：线上获客后电话转化，公司核心利润中心，快周转

**转化流转**：外呼 → 接通 → 深沟 → 签单 → 营收

**核心KPI**：总营收、在岗人数、人均产值、接通率（基准18%）、深沟率（基准35%）、签单数、AI评分均值、月累计

**Sparkline覆盖**：total_rev, per_capita, connect_rate, deep_rate, signed, avg_ai

**8个部门负责人**：罗阳等（在 DEPT_MANAGERS 字典中定义）

**API调用**：`daily("telesale", date)`

**特殊注意**：电销KPI卡片是暗色背景，Sparkline颜色用 `rgba(255,255,255,.7)` 保证可见

### 6.3 红娘团队（hongniang）

**定位**：VIP用户一对一服务，公司品牌生命线，长尾价值挖掘

**转化流转**：VIP资源 → 通话 → 深沟 → 安排见面 → 营收

**核心KPI**：在线VIP、通话次数、见面安排(率)、今日营收、人均产值、退费率、恋爱达成、新签

**Sparkline覆盖**：on_vip, link_time_count, jm_n, total_rev, per_rev, refund_rate, pay_1d_num

**退费率计算修正**：退费率用 `pay_m`（月累计营收）做分母，不能用日营收（否则会出现>1000%的荒谬数字）

**API调用**：`query("hongniang", "daily", date)` + `query("hongniang", "hourly", date)`（员工明细）

### 6.4 门店团队（shop）

**定位**：线下面对面签单，高客单价，外包邀约+加盟SaaS隔离风险

**转化流转**：线索 → 邀约接通 → 到店 → 签单 → 营收

**核心KPI**：当日线索、邀约接通、到店人数、签单数(率)、日营收、人均产值、退费率、线索即日分配(红线≥80%)

**Sparkline覆盖**：leads_1d, link_num, sg_num, shop_sign, total_rev, per_rev, refund_rate, lead_speed_1d

**门店评分特殊规则**：30%签单率 + 70%到店产出（¥3000标准/¥4000良好/¥5000优秀）

**风险预警**：高到店+无成交=偷盗嫌疑（签单率<5%时高风险预警）

**API调用**：`daily("shop", date)`

### 6.5 APP业务（app）

**定位**：在线付费产品核心现金牛，DAU驱动的流量转化，公司现金流压舱石

**三张数据表**：
- `daily`（51字段）：营收/用户/留存/直播/订单/产品/跨业务/月累计
- `orders`（20字段）：三级入口/渠道/平台/产品/用户类型/试用/版本
- `traffic`（16字段）：渠道/注册/付费/成本/ROI

**核心KPI**（10张卡片）：DAU、次日留存、付费率、ARPU(基准¥30)、日营收、复购金额、退款率(红线<2%)、订单成功率、珍心占比(红线<80%)、月累营收

**关键红线**：珍心>80%=结构风险、退款>2%=治理、支付失败>40%=P0、次日留存<35%=根本问题、付费率<3%=转化障碍

**20+分析模块**：直播运营深度/支付漏斗/入口场景/多平台对比/留存矩阵/渠道ROI/产品品类/用户结构/跨业务协同/因果链/知识对撞/AARRR全链路等

**书籍映射**：《Hooked》《增长黑客》《订阅经济》《平台革命》《怪诞行为学》《用户增长方法论》《精益创业》《精益数据分析》

**API调用（14次并行）**：
```python
calls = [
    lambda: daily("app", DATE),                    # 今日
    lambda: daily("app", prev_date(DATE)),           # 昨日
    lambda: query("app", "orders", DATE, size=2000), # 订单表
    lambda: query("app", "traffic", DATE, size=500), # 流量表
]
for delta in range(9, -1, -1):  # 10天趋势
    d = (base_dt - datetime.timedelta(days=delta)).strftime("%Y%m%d")
    calls.append(lambda d=d: daily("app", d))
```

**APP模块化架构**：
- `app_report_data.py`：常量(PRODUCTS, BOOK_REFS, APP_METRIC_LABELS) + 聚合函数(agg_app, agg_orders, agg_traffic, build_trend_data)
- `app_report_html.py`：CSS + 20+个HTML生成函数 + assemble_full_html()
- `generate_app_full_report.py`：主控（数据拉取→聚合→渲染→记忆→导出）

---

## 七、跨领域知识对撞规则

### 7.1 必须引用的书籍知识库

报告中的诊断和建议必须结合以下书籍框架，格式为 `📚《书名》`：

| 标签 | 书名 | 用途 |
|------|------|------|
| SPIN | 《SPIN销售巨人》 | 深沟话术结构化 |
| LOSS | 《思考快与慢》 | 损失厌恶心理 |
| SOCIAL | 《影响力》 | 社会认同/从众心理 |
| ATOMIC | 《原子习惯》 | 系统化SOP复制 |
| FIRST90 | 《前90天》 | 新人关键窗口 |
| NPS | 《终极问题》 | 客户留存/NPS |
| CLOSER | 《挑战式销售》 | 高效成交 |
| INFLUENCE | 《影响力》 | 说服心理 |
| HOOKED | 《上瘾》 | 留存/习惯循环 |
| LEAN | 《精益创业》 | 快速验证 |
| PLATSCALE | 《平台革命》 | 平台运营 |

### 7.2 对撞格式
```
<div style="background:#f8f4ff;border-radius:10px;padding:16px;border-left:4px solid #8e44ad">
  <div style="font-weight:700;color:#8e44ad;margin-bottom:8px">
    框架A × 框架B 📚《书名A》 × 📚《书名B》
  </div>
  <div style="font-size:12px;color:#555;line-height:1.7">
    <strong>现象：</strong>数据现象描述<br>
    <strong>对撞：</strong>两个框架如何碰撞解释<br>
    <strong>动作：</strong>具体可执行动作<br>
    <strong>预估：</strong>具体业绩预估（日增¥X→月增¥Y）
  </div>
</div>
```

---

## 八、改善建议输出规范

### 8.1 每条建议必含6要素
```
| P0/P1/P2 | 问题/机会点 | 负责人（指名到人）| 今日可执行的具体动作 | 坚持天数 | 预估提升金额 | 📚知识来源 |
```

### 8.2 排序规则
按「预估增幅」从高到低排序，不限条数。

### 8.3 颗粒度示例
> 「朴娟：今日安排各部组长提交3种首发信话术，必须包含①社交验证②匹配悬念③行动号召。明日A/B测试。坚持7天。预估月增切面¥5-10万。📚《影响力》」

---

## 九、Sparkline迷你趋势线规范

### 9.1 技术实现
```python
# agent_system/actions/report_sparkline.py

def sparkline_svg(values, width=60, height=22, color="#3b82f6", fill=True):
    """纯内联SVG，零依赖"""
    # 至少需要2个数据点
    # 生成polyline + 半透明填充 + 末端圆点（绿=上升/红=下降）

def extract_trend_values(history_episodes, key, today_val=None, prev_val=None):
    """从情景记忆提取趋势值，prev_val作为保底基线"""
```

### 9.2 数据来源
- **所有业务线**：通过 `parallel_fetch` 并行拉取报告日期前10天的API数据
- 示例：报告日期2月27日 → 拉取2月18日~2月27日共10天数据

### 9.3 各业务线覆盖指标

| 业务线 | Sparkline覆盖的KPI指标 |
|--------|------------------------|
| APP | DAU, 次日留存, 付费率, ARPU, 日营收, 复购金额, 退款率, 订单成功率 |
| 建信 | 切面业绩, 人均切面, 回复率, 企微添加, 调配人数, 自主触达, 调配转化率 |
| 电销 | 总营收, 人均产值, 接通率, 深沟率, 签单数, AI评分均值 |
| 红娘 | 在线VIP, 通话次数, 见面安排, 日营收, 人均产值, 退费率, 新签 |
| 门店 | 当日线索, 邀约接通, 到店人数, 签单数, 日营收, 人均产值, 退费率, 线索即日分配 |

---

## 十、情景记忆系统

### 10.1 架构
- **存储**：SQLite（`agent_system/memory.db`）
- **表结构**：`report_episodes(team, date, metrics JSON)`
- **功能**：每日报告生成时自动存储关键指标，支持历史趋势对比

### 10.2 使用方式
```python
from agent_system.actions.memory_manager import ReportMemory
mem = ReportMemory()

# 存储今日指标
mem.save("jianxin", "20260227", {"pay_amt": 300000, "reply_rate": 7.5, ...})

# 召回历史（自动排除今日）
history = mem.recall("jianxin", days=7, before_date="20260227")

# 生成趋势对比HTML（自动计算环比、7日均值）
trend_html = mem.trend_comparison_html("jianxin", "20260227", today_metrics, metric_labels)
```

---

## 十一、邮件发送

```python
from agent_system.actions.email_sender import send_report_email
send_report_email(subject="🔷 建信团队业务体检报告 2026-02-27", html_content=html)
# 默认收件人：赵总  默认抄送：田小英
```

---

## 十二、HTML报告视觉规范

### 12.1 通用CSS变量
```css
body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; background: #f0f2f5; }
```

### 12.2 KPI卡片颜色逻辑
```python
def color_kpi(val, good_threshold, warn_threshold, higher_is_better=True):
    if higher_is_better:
        if val >= good_threshold: return "#16a34a"  # 绿色
        if val >= warn_threshold: return "#d97706"  # 橙色
        return "#dc2626"                             # 红色
    else:  # 退费率等，低好
        if val <= warn_threshold: return "#16a34a"
        if val <= good_threshold: return "#d97706"
        return "#dc2626"
```

### 12.3 诊断条颜色
- `critical`（红底）：严重问题
- `warning`（橙底）：警告
- `good`（绿底）：达标
- `info`（蓝底）：信息

### 12.4 改善建议优先级颜色
- P0（`#dc2626`红色）→ P1（`#d97706`橙色）→ P2（`#6366f1`紫色）

---

## 十三、防退化机制

1. **生成前自检**：读取第四节14项清单，逐项确认
2. **知识库引用**：分析时引用本文档和赵总智慧知识库
3. **基准对比**：若赵总反馈「比之前差了」，对比基准找出缺失模块
4. **只进不退**：每次赵总提出新要求，追加到规则知识库，下次必须覆盖

---

## 十四、GitHub代码仓库

- **地址**：https://github.com/zhaocanus-sys/zhaocanus
- **分支**：main
- **推送方式**：SSH（密钥已配置）
```bash
cd /Users/yanchen/智慧助理
git add -A && git commit -m "描述" && git push origin main
```

---

## 十五、关键文件清单

| 类别 | 文件路径 | 说明 |
|------|---------|------|
| **API** | `agent_system/actions/api_client.py` | 数据接口 |
| **邮件** | `agent_system/actions/email_sender.py` | 报告发送 |
| **导出** | `agent_system/actions/report_exporter.py` | HTML导出 |
| **记忆** | `agent_system/actions/memory_manager.py` | 情景记忆SQLite |
| **趋势线** | `agent_system/actions/report_sparkline.py` | Sparkline SVG |
| **建信报告** | `generate_jianxin_full_report.py` | 建信日报 |
| **电销报告** | `generate_telesale_full_report.py` | 电销日报 |
| **红娘报告** | `generate_hongniang_full_report.py` | 红娘日报 |
| **门店报告** | `generate_shop_full_report.py` | 门店日报 |
| **APP数据** | `app_report_data.py` | APP数据聚合 |
| **APP渲染** | `app_report_html.py` | APP HTML生成 |
| **APP主控** | `generate_app_full_report.py` | APP日报主入口 |
| **设计原则** | `agent_system/knowledge_base/report_design_principles_kb.md` | 报表规则 |
| **赵总智慧** | `agent_system/knowledge_base/zhao_management_wisdom_kb.md` | 管理哲学 |
| **质量基准** | `agent_system/knowledge_base/report_template_benchmark.md` | 防退化基准 |
| **APP规则** | `agent_system/knowledge_base/report_rules_app.md` | APP专属规则 |

---

> **核心提醒**：这套系统的灵魂不是代码，而是赵总的管理哲学——「数据是手段，人是核心」。所有报表的终极目的是帮助管理者发现「人」的问题，制定具体可执行的改善动作。
