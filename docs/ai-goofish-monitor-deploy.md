# 闲鱼智能监控（ai-goofish-monitor）部署说明

> 项目：https://github.com/Usagi-org/ai-goofish-monitor  
> 本仓库提供一键部署脚本与本机/云端部署记录。

## 当前环境状态（Cursor Cloud）

| 项 | 状态 |
|----|------|
| Web 服务 | ✅ 已启动，`http://127.0.0.1:8000` |
| 登录账号 | `admin` / 见 `ai-goofish-monitor/.web_password` |
| SQLite | ✅ `ai-goofish-monitor/data/app.sqlite3` |
| 前端构建 | ✅ `ai-goofish-monitor/dist/` |
| 系统 Chrome | ✅ 已安装（Playwright channel=chrome） |
| Docker 镜像 | ⚠️ 本环境 overlayfs 白名单解压失败，已改本地 pip 部署 |
| 闲鱼抓取 | ❌ 云环境出网策略拦截 `goofish.com` |
| AI 分析 | ❌ 云环境拦截 `openai.com` / `modelscope.cn` |
| 推送 | ❌ 云环境拦截 `ntfy.sh` 等 |

**结论**：本云端 Agent 环境可完成安装与 Web UI 验证，但**实际 24h 监控请在本机或 VPS 部署**（需可访问闲鱼 + AI API）。

## 本机 / VPS 一键部署（推荐）

```bash
# 在可访问外网的机器上执行
bash scripts/deploy_ai_goofish_monitor.sh
```

脚本会：

1. 克隆/更新 `Usagi-org/ai-goofish-monitor`
2. 安装 Python 依赖、Playwright、系统 Chromium/Chrome
3. 构建 Web 前端
4. 生成 `.env`（若无）并启动服务（默认端口 8000）

### 最少必填配置（编辑 `ai-goofish-monitor/.env`）

```bash
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.openai.com/v1/   # 或兼容接口，如 ModelScope
OPENAI_MODEL_NAME=gpt-4o                     # 必须支持图片（Vision）

# 可选：推送
NTFY_TOPIC_URL=
WX_BOT_URL=
BARK_URL=
```

### 首次使用步骤

1. 打开 `http://127.0.0.1:8000`，用 `WEB_USERNAME` / `WEB_PASSWORD` 登录
2. 安装 Chrome 扩展：[闲鱼登录态提取](https://chromewebstore.google.com/detail/xianyu-login-state-extrac/eidlpfjiodpigmfcahkmlenhppfklcoa)
3. 登录闲鱼网页 → 扩展导出 JSON → 粘贴到「闲鱼账号管理」
4. 「任务管理」创建监控任务并绑定账号

### 常用命令

```bash
# 启动（已部署过）
bash scripts/start_ai_goofish_monitor.sh

# 查看日志
tail -f ai-goofish-monitor/logs/server.log

# 停止
bash scripts/stop_ai_goofish_monitor.sh
```

### Docker 方式（本机推荐，需 Docker 可用）

```bash
cd ai-goofish-monitor
cp .env.example .env   # 填入 API Key
docker compose up -d
docker compose logs -f app
```

默认 Web UI：`http://127.0.0.1:8000`

## 合规提醒

- 仅供个人闲置信息监控，勿用于黄牛倒卖
- 控制刷新频率，避免触发平台风控
- AI 筛选仅供参考，交易务必走平台担保
