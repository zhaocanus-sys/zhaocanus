# App Store Connect 配置操作步骤（你跟着点就行）

## 第一步：创建 App

1. 打开 https://appstoreconnect.apple.com
2. 点击 "My Apps" → "+" → "New App"
3. 填写以下信息：

| 字段 | 填写内容 |
|------|---------|
| Platforms | iOS |
| Name | AquaMark - Watermark Photo & Video |
| Primary Language | English (U.S.) |
| Bundle ID | com.aquamark.app（需先在 Developer Portal 注册） |
| SKU | AQUAMARK2026 |
| User Access | Full Access |

## 第二步：注册 Bundle ID

1. 打开 https://developer.apple.com/account/resources/identifiers/list
2. 点击 "+" → "App IDs" → "App"
3. Description: AquaMark
4. Bundle ID: Explicit → `com.aquamark.app`
5. Capabilities 勾选：
   - ✅ In-App Purchase
   - ✅ Push Notifications（未来可用）
6. 点击 "Continue" → "Register"

## 第三步：配置内购产品

在 App Store Connect → 你的 App → "Features" → "In-App Purchases"

### 产品1：周订阅
| 字段 | 内容 |
|------|------|
| Type | Auto-Renewable Subscription |
| Reference Name | AquaMark Pro Weekly |
| Product ID | com.aquamark.pro.weekly |
| Subscription Group | AquaMark Pro |
| Price | $3.99 (Tier 4) |
| Duration | 1 Week |
| Display Name | AquaMark Pro Weekly |
| Description | Full access to all Pro features |

### 产品2：月订阅
| 字段 | 内容 |
|------|------|
| Type | Auto-Renewable Subscription |
| Reference Name | AquaMark Pro Monthly |
| Product ID | com.aquamark.pro.monthly |
| Subscription Group | AquaMark Pro |
| Price | $7.99 (Tier 8) |
| Duration | 1 Month |
| Free Trial | 3 Days |
| Display Name | AquaMark Pro Monthly |
| Description | Full access to all Pro features |

### 产品3：年订阅（主推）
| 字段 | 内容 |
|------|------|
| Type | Auto-Renewable Subscription |
| Reference Name | AquaMark Pro Annual |
| Product ID | com.aquamark.pro.yearly |
| Subscription Group | AquaMark Pro |
| Price | $29.99 (Tier 30) |
| Duration | 1 Year |
| Free Trial | 7 Days |
| Display Name | AquaMark Pro Annual |
| Description | Full access to all Pro features — Best Value |

### 产品4：终身买断
| 字段 | 内容 |
|------|------|
| Type | Non-Consumable |
| Reference Name | AquaMark Pro Lifetime |
| Product ID | com.aquamark.pro.lifetime |
| Price | $49.99 (Tier 50) |
| Display Name | AquaMark Pro Lifetime |
| Description | Unlock all Pro features forever |

## 第四步：上传截图

在 App Store Connect → App → Version → Media:

| 设备 | 尺寸 | 数量 |
|------|------|------|
| iPhone 6.7" (15 Pro Max) | 1290 × 2796 | 5张 |
| iPhone 6.1" (15 Pro) | 1179 × 2556 | 5张 |
| iPad Pro 12.9" | 2048 × 2732 | 5张 |

截图内容建议：
1. 首页工具总览（展示全部功能）
2. 图片水印编辑器（编辑中状态）
3. 视频编辑器（含时间线）
4. Pro付费页面
5. 批量处理功能

## 第五步：填写 App 信息

直接复制 `app_store_listing.md` 中的内容填入对应字段。

## 第六步：App Privacy

在 App Store Connect → App → "App Privacy":
- "Does your app collect data?" → Yes
- 只勾选 "Diagnostics" → "Crash Data" + "Performance Data"
- "Is this data linked to the user?" → No
- "Is this data used for tracking?" → No

## 第七步：提交审核

1. 确认所有字段填写完毕
2. 确认截图已上传
3. 确认 Build 已上传
4. Review Notes 填写 `review_preparation.md` 中的模板
5. 点击 "Submit for Review"

---

## ⏱ 预计审核时间
- 首次提交：24-48小时
- 被拒后重新提交：24小时内

## 💡 如果被拒
将被拒原因发给我，我立即准备修改方案和申诉文案。
