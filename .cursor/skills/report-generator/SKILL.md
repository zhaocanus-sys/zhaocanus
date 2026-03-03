---
name: report-generator
description: 珍爱网5大业务线（建信/电销/红娘/门店/APP）日报自动生成。当用户说"生成日报"、"跑报表"、"建信报告"、"电销报告"、"红娘报告"、"门店报告"、"APP报告"、"日报"时使用此技能。
compatibility: Python 3.9+, requests库
metadata:
  author: zhaocanus-sys
  version: "2.0"
---

# 珍爱网日报生成系统

## 快速执行

当用户要求生成日报时，按以下步骤执行：

### Step 1: 确定参数

从用户指令中提取：
- **业务线**：建信/电销/红娘/门店/APP（必选）
- **日期**：YYYY-MM-DD格式（必选，用户未指定则询问）
- **是否发送邮件**：默认不发送（加 `--no-email`）

### Step 2: 执行脚本

```bash
cd /path/to/智慧助理
python3 {脚本名} --date {日期} --no-email
```

### Step 3: 质量自检

生成后对照14项清单（见下方）确认质量达标。

---

## 5大业务线速查表

| 业务线 | 脚本 | API team | 负责人 | 核心转化链 |
|--------|------|----------|--------|------------|
| 建信 | `generate_jianxin_full_report.py` | `jianxin` | 程朴娟 | 分配→发信→回复→企微→调配→切面 |
| 电销 | `generate_telesale_full_report.py` | `telesale` | 罗阳等8部门 | 外呼→接通→深沟→签单→营收 |
| 红娘 | `generate_hongniang_full_report.py` | `hongniang` | — | VIP→通话→深沟→见面→营收 |
| 门店 | `generate_shop_full_report.py` | `shop` | 门店运营 | 线索→接通→到店→签单→营收 |
| APP | `generate_app_full_report.py` | `app` | — | DAU→留存→付费→下单→支付→营收 |

---

## 报告核心架构

每份报告都是独立的Python脚本，生成完整HTML。架构统一：

```
1. 并行拉取API数据（今日+昨日+10天趋势）
2. 数据聚合（agg_xxx函数 → 指标字典t/p）
3. 环比计算（今日t vs 昨日p）
4. Sparkline趋势线构建（10天数据 → SVG）
5. HTML渲染（f-string模板 → 完整HTML）
6. 情景记忆存储（SQLite → 历史趋势对比）
7. 导出HTML + 可选邮件发送
```

---

## 14项必含模块（质量红线，缺一不可）

1. **头部**：业务名称、日期、负责人姓名、团队规模
2. **KPI卡片**：按转化流转顺序，红/黄/绿标色，附人均业绩，含10天Sparkline
3. **业务定位**：「{业务名}团队高业绩必须关注的重点」
4. **全局诊断**：含环比分析、捞取资源专项
5. **知识图谱诊断模式匹配**：E01-E06/J01等精确匹配
6. **因果链**：标红最大瓶颈+漏斗佐证+杠杆预估
7. **跨领域对撞**：至少2组，📚书籍来源+具体动作+业绩预估
8. **改善建议**：按预估增幅排序，每条含负责人+动作+天数+预估+来源
9. **渠道/明细表**：含捞取资源行，含人均业绩列
10. **部门明细**：含自主触达+人均捞取+人均切面
11. **TOP5深度分析**：全过程字段+综合评分+为什么好+可复制性
12. **TOP5 vs BOTTOM5对比**：13+维度+差异倍数+解读
13. **BOTTOM5诊断**：问题分析+改善建议
14. **数据→人的转向**：四维分析（技能/心态/存量管理/执行力）

---

## 赵总管理哲学（最高优先级）

**核心：数据是手段，人是核心。**

### 四维人员分析框架（每份报表必做）

| 维度 | 核心问题 | 数据信号 | 管理动作 |
|------|----------|----------|----------|
| 技能 | 会不会做？ | AI分/深沟率/TOP差异 | 标杆录音→话术通关 |
| 心态 | 愿不愿做？ | 外呼趋势/连续低产 | 新人激励/老人轮岗 |
| 存量 | 资源用好了吗？ | 人均存量/捞取数 | 存量盘活+公海回流 |
| 执行力 | 动作落地了吗？ | 布置后改善幅度 | 3天无改善→绩效挂钩 |

### 管理铁律

- 过程最多30分，结果占70分。无成交/营收最多30分。
- 门店评分100%关联业绩：30%签单率 + 70%到店产出（¥3000标准/¥4000良好/¥5000优秀）
- 改善建议按预估增幅排序，每条指名到人
- 反鞭打快牛：优先提升中腰部，不压榨头部
- 严禁提出高客单价快速转化逼签方案
- 10天持续不改善升级P0处罚

---

## 改善建议格式（每条必含6要素）

```
| 优先级 | 问题/机会点 | 负责人 | 今日可执行动作 | 坚持天数 | 预估增幅 | 📚来源 |
```

颗粒度示例：
> 程朴娟：今日安排各部组长提交3种首发信话术，必须包含①社交验证②匹配悬念③行动号召。明日A/B测试。坚持7天。预估月增切面¥5-10万。📚《影响力》

---

## 跨领域知识对撞（书籍库）

| 标签 | 书名 | 适用场景 |
|------|------|----------|
| SPIN | 《SPIN销售巨人》 | 深沟话术结构化 |
| LOSS | 《思考快与慢》 | 损失厌恶心理 |
| SOCIAL | 《影响力》 | 社会认同/从众 |
| ATOMIC | 《原子习惯》 | SOP系统化复制 |
| FIRST90 | 《前90天》 | 新人关键窗口 |
| NPS | 《终极问题》 | 客户留存 |
| CLOSER | 《挑战式销售》 | 高效成交 |
| HOOKED | 《上瘾》 | 留存/习惯循环 |
| LEAN | 《精益创业》 | 快速验证 |
| PLATSCALE | 《平台革命》 | 平台运营 |

每组对撞必须：现象 → 框架碰撞 → 具体动作 → 业绩预估

---

## KPI Sparkline趋势线

每个KPI卡片嵌入60×22px内联SVG趋势线，展示报告日期前10天走势。

- 数据来源：并行API拉取10天daily数据
- 末端圆点：绿=上升，红=下降
- 工具：`agent_system/actions/report_sparkline.py`

---

## 技术组件

| 组件 | 文件 | 功能 |
|------|------|------|
| API客户端 | `agent_system/actions/api_client.py` | daily()/query()/parallel_fetch() |
| 邮件发送 | `agent_system/actions/email_sender.py` | send_report_email() |
| HTML导出 | `agent_system/actions/report_exporter.py` | export_html() |
| 情景记忆 | `agent_system/actions/memory_manager.py` | ReportMemory类(SQLite) |
| 趋势线 | `agent_system/actions/report_sparkline.py` | sparkline_svg() |

---

## 详细参考文档

- 全业务线规则精华：[rules-all-teams.md](references/rules-all-teams.md)
- API接口和数据字段速查：[api-reference.md](references/api-reference.md)
- 评分铁律和风险预警：[scoring-and-fraud.md](references/scoring-and-fraud.md)
- 完整操作手册：[CLAUDE_REPORT_GUIDE.md](../../../CLAUDE_REPORT_GUIDE.md)

---

## 修改或新增报告

如需修改现有报告或新增业务线报告：

1. 阅读 `references/rules-all-teams.md` 了解全部规则
2. 参考现有脚本（如 `generate_shop_full_report.py`）的代码结构
3. 确保14项必含模块全部覆盖
4. 运行测试：`python3 脚本名.py --date YYYY-MM-DD --no-email`
5. 浏览器打开HTML确认质量不低于现有水平

## 注意事项

- 首次使用需配置 `agent_system/config/facts.json`（从模板复制）
- Python依赖：`pip3 install -r requirements.txt`
- 报告输出目录：`reports/`
- 情景记忆数据库：`agent_system/memory.db`（自动创建）
