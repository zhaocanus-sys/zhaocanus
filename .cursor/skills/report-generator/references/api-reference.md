# API接口与数据字段速查

> 最后更新：2026-03-02

---

## 一、基础配置

- **Base URL**: `http://43.138.47.115:8600`（配置于 `agent_system/config/facts.json` → `api.base_url`）
- **认证方式**: HTTP Header `X-API-Key`
- **代码文件**: `agent_system/actions/api_client.py`
- **配置加载**: `agent_system/config/__init__.py` → `api_config()`

---

## 二、核心API函数

### 2.1 daily — 团队日报数据

```python
daily(team, date=None, page=1, size=500)
# GET /api/v1/team/{team}/daily?date={date}&page={page}&page_size={size}
```

- `team`: `jianxin` | `telesale` | `hongniang` | `shop` | `app`
- `date`: `YYYYMMDD` 格式（如 `20260227`），不传则返回最新

### 2.2 query — 按表角色查询

```python
query(team, table_role, date=None, page=1, size=500)
# GET /api/v1/team/{team}/query?table_role={table_role}&date={date}
```

- `table_role`: `daily` | `hourly` | `orders` | `traffic`
- 用途：红娘的 `hourly`（员工明细）、APP的 `orders`/`traffic`

### 2.3 trend — 趋势数据

```python
trend(team, days=14)
# GET /api/v1/team/{team}/trend?days={days}
```

### 2.4 tables — 可用表列表

```python
tables(team)
# GET /api/v1/team/{team}/tables
```

### 2.5 parallel_fetch — 并行拉取

```python
parallel_fetch(calls)
# calls = [lambda: daily(...), lambda: query(...), ...]
# 最多8线程并发，返回有序结果列表
```

### 2.6 辅助函数

```python
safe_float(v, d=0.0)  # 安全转浮点，处理None/逗号/百分号
safe_int(v, d=0)       # 安全转整数
```

---

## 三、API返回格式

```json
{
  "rows": [{"field1": "value1", "field2": "value2"}, ...],
  "row_count": 10,
  "columns": ["field1", "field2", ...]
}
```

错误时返回：
```json
{"error": "错误信息", "rows": [], "row_count": 0, "columns": []}
```

---

## 四、日期格式约定

| 场景 | 格式 | 示例 |
|------|------|------|
| API参数 | `YYYYMMDD` | `20260227` |
| 报告显示 | `YYYY-MM-DD` | `2026-02-27` |
| 命令行参数 | `YYYY-MM-DD` | `--date 2026-02-27` |

---

## 五、各业务线数据字段

### 5.1 建信（jianxin）— daily表

| 字段 | 含义 | 聚合方式 | KPI用途 |
|------|------|----------|---------|
| `pay_amt` | 切面业绩（元） | SUM | 北极星指标 |
| `pay_amt_m` | 月累计业绩 | MAX | 月进度 |
| `reply_rate` | 回复率(%) | AVG | 转化效率 |
| `wechat` | 企微添加数 | SUM | 渠道沉淀 |
| `transfer` | 调配人数 | SUM | 输送电销 |
| `proactive` | 自主触达数 | SUM | 主动性 |
| `transfer_rate` | 调配转化率(%) | 计算 | 质量 |
| `staff_count` | 在岗人数 | COUNT | 规模 |
| `laoqu` | 捞取数 | SUM | 存量管理 |
| `channel` | 渠道来源 | GROUP BY | 渠道分析 |
| `dept` | 部门 | GROUP BY | 部门分析 |

### 5.2 电销（telesale）— daily表

| 字段 | 含义 | 聚合方式 | KPI用途 |
|------|------|----------|---------|
| `total_rev` | 总营收（元） | SUM | 北极星指标 |
| `total_rev_m` | 月累计营收 | MAX | 月进度 |
| `connect_rate` | 接通率(%) | AVG/计算 | 基准18% |
| `deep_rate` | 深沟率(%) | AVG/计算 | 基准35% |
| `signed` | 签单数 | SUM | 成交 |
| `avg_ai` | AI评分均值 | AVG | 话术质量 |
| `per_capita` | 人均产值 | 计算 | 单兵能力 |
| `callout` | 外呼量 | SUM | 工作量 |
| `connected` | 接通量 | SUM | 有效触达 |
| `deep_talk` | 深沟量 | SUM | 深度转化 |
| `staff_count` | 在岗人数 | COUNT | 规模 |
| `dept` | 部门 | GROUP BY | 部门分析 |
| `laoqu` | 捞取数 | SUM | 存量管理 |

### 5.3 红娘（hongniang）— daily + hourly表

**daily表（团队汇总）：**

| 字段 | 含义 | 聚合方式 |
|------|------|----------|
| `on_vip` | 在线VIP数 | SUM |
| `link_time_count` | 通话次数 | SUM |
| `jm_n` | 见面安排数 | SUM |
| `jm_rate` | 见面安排率(%) | 计算 |
| `total_rev` | 今日营收 | SUM |
| `per_rev` | 人均产值 | 计算 |
| `refund_amt` | 退费金额 | SUM |
| `refund_rate` | 退费率(%) | refund_amt/pay_m |
| `pay_1d_num` | 新签数 | SUM |
| `love_match` | 恋爱达成 | SUM |
| `pay_m` | 月累计营收 | MAX |

**hourly表（员工明细）：** 用于TOP/BOTTOM分析

### 5.4 门店（shop）— daily表

| 字段 | 含义 | 聚合方式 | KPI用途 |
|------|------|----------|---------|
| `leads_1d` | 当日线索 | SUM | 资源量 |
| `link_num` | 邀约接通数 | SUM | 有效触达 |
| `sg_num` | 到店人数 | SUM | 转化中间 |
| `shop_sign` | 签单数 | SUM | 成交 |
| `sign_rate` | 签单率(%) | 计算 | ≥30%合格/≥35%优秀 |
| `total_rev` | 日营收 | SUM | 北极星 |
| `per_rev` | 人均产值 | 计算 | 单兵能力 |
| `refund_amt` | 退费金额 | SUM | 风险 |
| `refund_rate` | 退费率(%) | 计算 | 风险 |
| `lead_speed_1d` | 线索即日分配(%) | 计算 | 红线≥80% |
| `staff_count` | 在岗人数 | COUNT | 规模 |
| `city` | 城市 | GROUP BY | 区域分析 |

### 5.5 APP — daily表（51字段）

**营收核心：**
| 字段 | 含义 |
|------|------|
| `amt` | 日营收（北极星指标） |
| `pay_num` / `pay_num_new` | 付费人数 / 新增付费 |
| `fugou_amt` | 复购金额（占比>50%为健康） |
| `pay_amt` | 支付金额 |
| `refund_money` | 退款金额（退款率红线<2%） |

**用户规模：**
| 字段 | 含义 |
|------|------|
| `active_members` | DAU |
| `mems` | 新注册人数 |
| `reg_num_m` | 月累注册 |

**留存矩阵（9个节点）：**
`retain_1d` / `retain_2d` / `retain_3d` / `retain_4d` / `retain_5d` / `retain_6d` / `retain_7d` / `retain_15d` / `retain_30d`

**直播板块：**
| 字段 | 含义 |
|------|------|
| `anchmems` | 开播主播数 |
| `anchtime` | 总直播时长（秒） |
| `giftmems` | 送礼人数 |
| `costmoney` | 直播消费金额 |
| `live_guard` | 直播守护收入 |

**订单漏斗：**
| 字段 | 含义 |
|------|------|
| `order_cnt` | 订单创建数 |
| `order_pay` | 支付成功数 |
| `order_num` | 订单人数 |

**产品品类（9个）：**
`zhenxin_member`（珍心，红线<80%）/ `super_member_full` / `super_member_plus` / `live_guard` / `zhenai_coin` / `super_remind` / `star_privilege` / `super_recommend` / `other`

**跨业务协同：**
| 字段 | 含义 |
|------|------|
| `leads_offline` / `leads_online` | 线下/线上leads |
| `allot` / `laoqu` | 分配/捞取 |
| `link_1d_num` / `callout_1d_num` | 链接数/外呼数 |

**月累计：**
`pay_num_m` / `pay_amt_m` / `pay_num_m_cut` / `pay_amt_m_cut` / `amt_pay_m_online1` / `last_consumeonday_d` / `last_consumeonday_m`

### 5.6 APP — orders表（20字段）

| 字段 | 含义 |
|------|------|
| `entrance1` / `entrance2` / `entrance3` | 三级入口 |
| `channelname` / `channelname2` | 支付渠道 |
| `platformname` | 平台（iOS/Android/小程序/鸿蒙/WAP/PC） |
| `producttype` / `productfullname` | 产品类型/产品全名（含价格档位） |
| `user_type` | 用户类型（普通/风险） |
| `is_trial` | 是否试用 |
| `iscallback` | 支付回调状态 |
| `app_version` | APP版本 |

### 5.7 APP — traffic表（16字段）

| 字段 | 含义 |
|------|------|
| `parent_name` / `parents` | 渠道大类/子渠道 |
| `regnum` / `regnew_mems` | 注册数/新注册会员 |
| `num_pay_online_d` | 日付费人数 |
| `amt_pay_d_online` / `amt_pay_m_online1` | 日/月在线营收 |
| `real_cost` | 投放成本 |
| `validnum` | 有效用户数 |
| `pay_online_rate` | 付费率 |

---

## 六、数据聚合模式

每个业务线都有 `agg_xxx(rows)` 函数，将API返回的多行数据聚合为单一指标字典：

```python
def agg_jianxin(rows):
    t = {}
    t["pay_amt"] = sum(safe_float(r.get("pay_amt")) for r in rows)
    t["staff_count"] = len(rows)
    t["per_capita"] = t["pay_amt"] / t["staff_count"] if t["staff_count"] else 0
    # ... 更多字段
    return t
```

通用模式：
- SUM：营收、签单等总量指标
- AVG：比率类指标
- COUNT：人数（rows行数）
- MAX：月累计（取最大值即为最新）
- 计算字段：人均 = 总量 / 人数

---

## 七、10天趋势数据拉取模式

所有业务线统一采用 `parallel_fetch` 拉取10天趋势：

```python
import datetime
from agent_system.actions.api_client import daily, query, parallel_fetch

base_dt = datetime.datetime.strptime(DATE, "%Y%m%d")  # DATE = "20260227"

calls = [
    lambda: daily(team, DATE),               # [0] 今日
    lambda: daily(team, prev_date(DATE)),     # [1] 昨日
]
for delta in range(9, -1, -1):               # [2]~[11] 10天趋势
    d = (base_dt - datetime.timedelta(days=delta)).strftime("%Y%m%d")
    calls.append(lambda d=d: daily(team, d))

results = parallel_fetch(calls)

# results[0] = 今日, results[1] = 昨日
# results[2]~results[11] = 报告日期前10天（从远到近）
```

红娘额外需要 `hourly` 表：
```python
calls.append(lambda: query("hongniang", "hourly", DATE))
```

APP额外需要 `orders` 和 `traffic` 表：
```python
calls.insert(2, lambda: query("app", "orders", DATE, size=2000))
calls.insert(3, lambda: query("app", "traffic", DATE, size=500))
```
