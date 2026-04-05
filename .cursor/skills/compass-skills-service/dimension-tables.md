# 珍爱网维度表速查（珍爱维表.xlsx）

> **数据来源**: `skills/compass-skills-service/珍爱维表.xlsx`  
> **更新日期**: 2026-03-10  
> **用途**: API 返回的 ID/编码字段（如 platform、paychanneltype、offline_city 等）需对照本维度表解读为中文含义。  
> **结构说明**: 每行包含 dict_type（维度类型）、dict_name（维度中文名）、first_id/first_name（一级 ID/名称）、second_id/second_name（二级 ID/名称）。

---

## 一、维度表索引

| dict_type | 中文名称 | 条数 | 适用场景 |
|-----------|----------|------|----------|
| offline_city | 线下城市 | 39 | 门店/电销地域分析 |
| dc_platform | dc数据上报平台类型 | 40 | 数据上报来源（android/ios/web/applet） |
| platform | 平台信息维表 | 43 | 终端平台（与 knowledge 6.5 platformname 对应） |
| pay_channel | 支付方式 | 15 | 线下门店支付方式 |
| paychanneltype | 付费方式 | 57 | 线上支付渠道（与 knowledge 6.5 channelname 对应） |
| dept_ability | 部门职能 | 15 | 电销/红娘部门分类 |
| adm_media | 投放媒体 | 33 | 广告投放渠道 |
| livetype | 直播类型 | 12 | 趣约会直播分析 |
| product_price_type | 情感咨询产品服务类型 | 13 | 红娘/情感咨询产品 |
| gender | 性别 | 2 | 用户画像 |
| agerange | 年龄段 | 5 | 用户画像 |
| education | 学历 | 8 | 用户画像 |
| marriage | 婚姻 | 6 | 用户画像 |
| salary | 收入 | 10 | 用户画像 |
| obj_salary | 择偶收入 | 9 | 用户画像 |
| occupation | 职业 | 276 | 用户画像 |
| constellation | 星座 | 13 | 用户画像 |
| house | 住房条件 | 8 | 用户画像 |
| vehicle | 车辆条件 | 4 | 用户画像 |
| chongqing_offline_refuse | 重庆郊区资源不分配线下 | 79 | 邀约/电销资源分配规则 |

---

## 二、核心维度明细（与 API 字段映射）

### 2.1 平台与终端（platform / dc_platform）

**platform**（平台信息维表）— 对应 API 字段 `platformname`、`platform`：

| first_id | first_name | 说明 |
|----------|------------|------|
| 1 | PC | 网站 |
| 2 | WAP | wap H5 |
| 4-9, 10, 17, 19, 53, 62 | Android | 安卓端 |
| 5, 8, 18, 28, 51, 54, 81-83 | iOS | 苹果端 |
| 100 | 鸿蒙 | 2019年及之前表示iOS，2024起表示鸿蒙 |
| 52, 92-98 | 小程序 | 珍爱微信小程序、优恋空间、百度/头条/QQ小程序等 |
| 201-203 | PC/小程序 | 管理后台等 |

**dc_platform**（dc数据上报平台类型）— 用于数据埋点归类：

| second_name | 含义 |
|-------------|------|
| android_za | 珍爱 Android |
| ios_za | 珍爱 iOS |
| www_za | 珍爱 Web |
| applet_za | 珍爱小程序 |
| wap_za | 珍爱 WAP |

### 2.2 支付与渠道（pay_channel / paychanneltype）

**pay_channel**（支付方式）— 线下门店用：

- 卡转账、现金转账、交现金、刷POS机、刷全功能POS机、刷实名制POS机、刷快钱POS机、支付宝、微信、网银转账等

**paychanneltype**（付费方式）— 线上支付，对应 API 字段 `channelname`：

- 微信、支付宝、Apple Pay、IPS支付、贝宝支付、银行转账等（second_name 列有「微信」「支付宝」「其他」等归类）

### 2.3 线下与地域（offline_city）

**offline_city**（线下城市）— 39 个城市：

北京、上海、广州、深圳、成都、武汉、重庆、长沙、南京、西安、合肥、福州、厦门、济南、青岛、东莞、佛山、珠海、郑州、沈阳、大连、石家庄、南昌、昆明、哈尔滨、长春、太原、泉州、太原等

### 2.4 部门与职能（dept_ability）

**dept_ability**（部门职能）：

- 精英销售、红娘、其他、线下红娘、培训、客服、客诉、财务、牵线通、约见、战略合作部、邀约、线下开拓

### 2.5 投放媒体（adm_media）

**adm_media**（投放媒体）— 广告投放渠道：

头条、广点通、百度搜索、百度信息、微信广告、网易广告、爱奇艺、微博等 33 个

### 2.6 直播相关（livetype / live_tab / view_source）

**livetype**（直播类型）：视频、语音、蜜语、频道房、牵线房、红娘牵线、红娘-专属、红娘-七人房等

**live_tab**（直播tab）：三人牵线Tab、关注Tab、推荐Tab、热门Tab、语音Tab、线下VIP约见Tab

**view_source**（直播来源）：直播列表、推荐页大直播间、推荐页插入小直播间等

### 2.7 用户画像维度

| dict_type | 中文名 | 示例值 |
|-----------|--------|--------|
| gender | 性别 | 男、女 |
| agerange | 年龄段 | 23及以下、24-27、28-35、36-45、46及以上 |
| education | 学历 | 中专、高中、大专、本科、硕士、博士 |
| marriage | 婚姻 | 未婚、离异、丧偶 |
| salary | 收入 | ~3K、3K-5K、5K-8K、8K-12K、12K-20K、20K-50K、50K~ |
| obj_salary | 择偶收入 | 不限、3000元、5000元、8000元、12000元、20000元、50000元 |
| occupation | 职业 | 276 种（金融业、计算机业、商业、服务行业等） |
| constellation | 星座 | 牡羊座、金牛座、双子座等 12 星座 |
| house | 住房条件 | 未填写、和家人同住、已购房、租房等 |
| vehicle | 车辆条件 | 未填写、已买车、未买车 |

---

## 三、使用规则

1. **API 返回 ID 时**：若字段名为 platform、paychanneltype、offline_city、dept_ability 等，到本维度表按 dict_type 查找 first_id 或 second_id 对应的 first_name/second_name 进行解读。
2. **与 knowledge.md 第六章配合**：第六章数据字典描述字段含义，本维度表提供 ID→中文的映射。例如 `platformname` 在第六章说明为「终端平台」，具体「1=PC」「8=iOS」等需查本表 platform 维度。
3. **数据源**：完整映射以 `珍爱维表.xlsx` 为准，本文档为速查摘要。新增或变更维度时需同步更新 Excel 与本文档。

---

> **维护说明**：当珍爱维表.xlsx 更新时，需同步更新本文档及上述索引表。
