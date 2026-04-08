# AGENTS.md

## Cursor Cloud specific instructions

### 项目概述

珍爱网智慧助理（Linh）— 纯 Python CLI 项目，无 web 服务器、无 Docker 依赖。核心功能是通过 5 个报告生成脚本从远程数据平台 API 拉取数据并生成 HTML 业务日报。

### 运行环境

- **Python 3.12+** + `requests`（唯一依赖，见 `requirements.txt`）
- **无本地服务需要启动** — 无数据库、无 web server、无 Docker compose
- 数据来源为远程 API（`http://43.138.47.115:8600`），凭据已配置在 `agent_system/config/facts.json`

### 报告生成命令

参考 `SETUP.md` 中「手动运行」一节。所有报告脚本支持 `--date YYYY-MM-DD` 和 `--no-email` 参数。示例：

```bash
python3 generate_jianxin_full_report.py --date 2026-04-07 --no-email
```

5 条业务线：`generate_jianxin_full_report.py`（建信）、`generate_telesale_full_report.py`（电销）、`generate_hongniang_full_report.py`（红娘）、`generate_shop_full_report.py`（门店）、`generate_app_full_report.py`（APP）。

### 已知问题

- `generate_telesale_full_report.py` 第 409 行有 f-string 语法错误（`SyntaxError: single '}' is not allowed`），属仓库既有 bug，其余 4 个报告脚本均可正常运行。

### 注意事项

- `facts.json` 包含真实 API Key 和 SMTP 凭据，已被 `.gitignore` 排除。如果该文件缺失，需从 `facts.json.template` 复制并填入真实凭据。
- 报告脚本默认会发送邮件，测试时务必加 `--no-email` 参数。
- 无 lint/test 框架配置（无 pytest、无 flake8/ruff 配置文件）。代码验证主要通过运行报告脚本确认。
