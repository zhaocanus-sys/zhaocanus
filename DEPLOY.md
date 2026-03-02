# 智慧助理（Linh）系统 · 全量无损迁移指南

> 本文件是系统重装后的唯一入口。按顺序执行即可 100% 恢复全部功能。
> 打包日期：2026-03-02 | 系统版本：v2（含红娘/APP/门店全量报告）

---

## 一、准备条件（重装后先做）

| 必装软件 | 来源 |
|---------|------|
| Cursor IDE | https://cursor.com |
| Python 3.11+ | https://python.org 或 `brew install python` |
| Docker Desktop（可选，用于小红书MCP） | https://docker.com |
| Node.js 18+（可选，用于xreach） | https://nodejs.org |

---

## 二、一键部署（三步完成）

### 第一步：解压备份包

```bash
# 将 linh-system-backup-YYYYMMDD.tar.gz 放到任意目录后：
cd ~/Desktop  # 或你放备份包的目录
tar -xzf linh-system-backup-*.tar.gz
cd linh-system-backup-*/
```

### 第二步：执行自动部署脚本

```bash
chmod +x restore.sh
./restore.sh
```

脚本会自动完成：
- ✅ 恢复工作区到 `/Users/yanchen/智慧助理/`
- ✅ 恢复全局 Cursor Skills（~/.cursor/skills/ 和 ~/.agents/skills/）
- ✅ 恢复 Cursor 编辑器设置
- ✅ 恢复 MCP 配置（mcporter）
- ✅ 安装 Python 依赖
- ✅ 验证 API 连通性
- ✅ 验证邮件配置
- ✅ 打印最终状态报告

### 第三步：打开 Cursor

```
Cursor → File → Open Folder → /Users/yanchen/智慧助理/
```

Linh 会自动读取规则，系统立即可用。

---

## 三、系统架构说明

```
linh-system-backup/
├── DEPLOY.md                    ← 本文件（看这里）
├── restore.sh                   ← 自动部署脚本
├── workspace/                   ← 完整工作区（所有核心代码）
│   ├── .cursor/rules/           ← Linh 人设 + 管理规则（6个）
│   ├── .cursor/memories/        ← 情景记忆（自动恢复）
│   ├── agent_system/            ← 核心引擎
│   │   ├── config/              ← facts.json（邮箱/API/人员/部门配置）
│   │   ├── knowledge_base/      ← 知识库（14个文件 + 规则框架）
│   │   ├── engines/             ← 对撞引擎 + 分析管道
│   │   ├── actions/             ← 邮件/API/报告导出
│   │   └── agents/              ← DataExpert 智能体
│   ├── generate_telesale_full_report.py    ← 电销全量报告生成器
│   ├── generate_jianxin_full_report.py     ← 建信全量报告生成器（48KB，774行，14模块全覆盖）
│   ├── generate_hongniang_full_report.py   ← 红娘全量报告生成器（v2）
│   ├── generate_app_full_report.py         ← APP全量报告生成器（新）
│   ├── generate_shop_full_report.py        ← 门店全量报告生成器（新）
│   ├── quality_supervision/     ← 质检模块
│   └── reports/                 ← 历史报告样本（建信基准59.1KB）
├── cursor-skills/                ← ~/.cursor/skills/（知识记录/链接学习）
├── cursor-skills-cursor/         ← ~/.cursor/skills-cursor/（规则/技能创建工具）
├── agents-skills/                ← ~/.agents/skills/（小红书/微信/web-fetch等）
└── cursor-settings/
    ├── settings.json             ← Cursor 编辑器偏好设置
    └── mcporter.json             ← MCP 服务器配置
```

---

## 四、核心功能清单

### 报告生成（4条业务线全量覆盖）

```bash
# 电销全量报告
python3 generate_telesale_full_report.py --date 2026-03-02

# 建信全量报告（基准线59.1KB）
python3 generate_jianxin_full_report.py --date 2026-03-02

# 红娘全量报告（v2含员工TOP5/BOTTOM5）
python3 generate_hongniang_full_report.py --date 2026-03-02

# APP全量报告
python3 generate_app_full_report.py --date 2026-03-02

# 门店全量报告
python3 generate_shop_full_report.py --date 2026-03-02
```

每个脚本均：拉取 API 数据 → 生成 HTML → 导出到 reports/ → 自动发送邮件

### 报告质量基准

所有报告满足 14 项模块自检清单（见 `agent_system/knowledge_base/report_template_benchmark.md`），不低于建信基准线（59.1KB，2026-02-27）。

### Linh 对话功能

- 数据分析与诊断
- 邮件起草与发送
- 情景记忆自动写入
- 跨领域知识对撞
- 虚拟赵总质疑环节

---

## 五、常见问题

### API 不通？

```bash
python3 -c "from agent_system.actions.api_client import me; print(me())"
# 预期输出：{"username": "zhao_boss", ...}
```

检查 `agent_system/config/facts.json` 中的 `api.api_key`。

### 邮件发送失败？

```bash
python3 -c "
from agent_system.actions.email_sender import send_report_email
ok = send_report_email('测试', '<p>测试邮件</p>')
print('成功' if ok else '失败')
"
```

检查 `facts.json` 中的 `smtp.auth_code`（腾讯企业邮箱授权码）。

### 小红书 MCP 不工作？

```bash
docker start xiaohongshu-mcp
# 或重新部署：
docker run -d --name xiaohongshu-mcp -p 18060:18060 --platform linux/amd64 xpzouying/xiaohongshu-mcp
```

---

## 六、重装后第一句话

打开 Cursor、打开工作区后，直接对 Linh 说：

> **「开始工作」**

Linh 会自动读取 facts.json、preferences.json，加载记忆，系统立即就绪。

---

*打包人：Linh Nguyen（智慧助理）| 2026-03-02*
