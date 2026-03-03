# 珍爱网智慧助理 — 快速开始

3步完成安装，即可用AI生成日报。

---

## 第1步：克隆仓库 + 安装依赖

```bash
git clone git@github.com:zhaocanus-sys/zhaocanus.git 智慧助理
cd 智慧助理
pip3 install -r requirements.txt
```

## 第2步：配置凭据

```bash
cp agent_system/config/facts.json.template agent_system/config/facts.json
```

编辑 `agent_system/config/facts.json`，填入以下3项：

| 配置项 | 位置 | 说明 |
|--------|------|------|
| API密钥 | `api.api_key` | 数据平台API Key，找张苗获取 |
| SMTP授权码 | `smtp.auth_code` | 腾讯企业邮箱授权码 |
| 发送邮箱 | `smtp.from_email` | 你的 @zhenai.com 邮箱 |

## 第3步：在Cursor中使用

1. 用 Cursor 打开 `智慧助理` 文件夹
2. Cursor 会自动发现 `.cursor/skills/report-generator/` 中的 Skill
3. 直接对AI说：

```
生成建信团队2月27日日报
```

AI会自动读取知识库、调用API、生成HTML报告并在浏览器中打开。

---

## 支持的指令示例

| 指令 | 效果 |
|------|------|
| `生成建信团队2月27日日报` | 建信日报 |
| `跑一下电销2月27号的报表` | 电销日报 |
| `红娘报告 2026-02-27` | 红娘日报 |
| `门店报告 2026-02-27` | 门店日报 |
| `APP报告 2026-02-27` | APP日报 |

---

## 手动运行（不用AI）

```bash
cd 智慧助理

# 生成建信日报（不发邮件）
python3 generate_jianxin_full_report.py --date 2026-02-27 --no-email

# 生成电销日报（自动发邮件）
python3 generate_telesale_full_report.py --date 2026-02-27

# 生成红娘日报
python3 generate_hongniang_full_report.py --date 2026-02-27 --no-email

# 生成门店日报
python3 generate_shop_full_report.py --date 2026-02-27 --no-email

# 生成APP日报
python3 generate_app_full_report.py --date 2026-02-27 --no-email
```

报告输出到 `reports/` 目录，浏览器自动打开。

---

## 项目结构

```
智慧助理/
├── generate_jianxin_full_report.py    # 建信日报
├── generate_telesale_full_report.py   # 电销日报
├── generate_hongniang_full_report.py  # 红娘日报
├── generate_shop_full_report.py       # 门店日报
├── generate_app_full_report.py        # APP日报主控
├── app_report_data.py                 # APP数据聚合
├── app_report_html.py                 # APP HTML渲染
├── CLAUDE_REPORT_GUIDE.md             # 完整技术文档
├── SETUP.md                           # 本文件
├── requirements.txt                   # Python依赖
├── reports/                           # 报告输出目录
├── agent_system/
│   ├── config/
│   │   ├── facts.json                 # 凭据配置（不提交Git）
│   │   └── facts.json.template        # 凭据模板
│   ├── actions/
│   │   ├── api_client.py              # API客户端
│   │   ├── email_sender.py            # 邮件发送
│   │   ├── report_exporter.py         # HTML导出
│   │   ├── memory_manager.py          # 情景记忆(SQLite)
│   │   └── report_sparkline.py        # Sparkline趋势线
│   └── knowledge_base/
│       ├── report_design_principles_kb.md
│       ├── zhao_management_wisdom_kb.md
│       ├── report_template_benchmark.md
│       └── report_rules_app.md
└── .cursor/skills/report-generator/   # Cursor Skill
    ├── SKILL.md                       # 主引导文件
    └── references/
        ├── rules-all-teams.md         # 全业务线规则
        ├── api-reference.md           # API速查
        └── scoring-and-fraud.md       # 评分+风险
```

---

## 常见问题

**Q: API连不上？**
A: 检查 `facts.json` 中的 `api.api_key` 是否正确，联系张苗(miao.zhang6@zhenai.com)。

**Q: 邮件发不出？**
A: 检查 `smtp.auth_code` 是否为腾讯企业邮箱的授权码（非登录密码）。

**Q: 报告中数据为0？**
A: 确认 `--date` 参数的日期有数据（周末/节假日可能无数据）。

**Q: Cursor没有自动识别Skill？**
A: 确保 `.cursor/skills/report-generator/SKILL.md` 文件存在，重启Cursor。
