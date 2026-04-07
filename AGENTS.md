# AGENTS.md

## Cursor Cloud specific instructions

### 项目概述
本项目是"智慧助理（Linh）"——珍爱网（Zhenai.com）的 AI 运营报告自动生成系统。纯 Python CLI 项目，无 web 服务、无容器。

### 依赖
唯一的 Python 第三方依赖是 `requests`（见 `requirements.txt`）。其余均为标准库（`sqlite3`、`smtplib`、`json` 等）。

### 核心入口
5 个报告生成器脚本位于项目根目录：
- `generate_telesale_full_report.py`（电销）— **注意：该文件第 409 行有 f-string 语法错误，Python 3.12 下无法运行**
- `generate_jianxin_full_report.py`（建信）
- `generate_hongniang_full_report.py`（红娘）
- `generate_shop_full_report.py`（门店）
- `generate_app_full_report.py`（APP）

运行方式：`python3 generate_<业务线>_full_report.py --date YYYYMMDD`

### 配置
- `agent_system/config/facts.json` 包含 API 密钥、SMTP 凭据、联系人映射等。模板见 `facts.json.template`。
- `agent_system/config/__init__.py` 提供 `facts()`、`smtp_config()`、`api_config()` 等配置读取函数。

### 外部依赖
- **数据 API**：`http://43.138.47.115:8600`，通过 `X-API-Key` 头认证。网络可达即可使用。
- **SMTP**：`smtp.exmail.qq.com:465`（腾讯企业邮箱），用于邮件发送。报告生成不依赖 SMTP，邮件发送失败不影响 HTML 输出。

### 报告输出
生成的 HTML 报告保存在 `/workspace/reports/` 目录下，文件名格式如 `Telesale_Full_2026-04-06.html`。

### lint / 测试
项目无自动化测试框架和 linter 配置。可使用 `python3 -m py_compile <file>` 做语法检查。验证方式为运行报告生成脚本并检查输出 HTML。
