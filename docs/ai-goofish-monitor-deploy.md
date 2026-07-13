# ai-goofish-monitor 部署说明

闲鱼智能监控（[Usagi-org/ai-goofish-monitor](https://github.com/Usagi-org/ai-goofish-monitor)）本地部署记录。

## 当前状态

| 项 | 值 |
|---|---|
| 部署路径 | `/workspace/ai-goofish-monitor` |
| 访问地址 | `http://127.0.0.1:8000` |
| 健康检查 | `GET /health` |
| Web 账号 | `admin` / `Goofish@2026`（见 `.env`，请尽快修改） |
| 启动方式 | 本地 venv + Playwright(系统 Chrome) + tmux |
| 管理脚本 | `scripts/deploy_ai_goofish_monitor.sh` |

> 本环境 Docker 镜像解压 overlayfs whiteout 失败，故采用 pip/本地方式；官方仍推荐 Docker。

## 快速操作

```bash
# 首次安装
./scripts/deploy_ai_goofish_monitor.sh install

# 启动 / 停止 / 状态
./scripts/deploy_ai_goofish_monitor.sh start
./scripts/deploy_ai_goofish_monitor.sh status
./scripts/deploy_ai_goofish_monitor.sh stop
./scripts/deploy_ai_goofish_monitor.sh restart
```

## 必填配置（`.env`）

编辑 `ai-goofish-monitor/.env`：

```bash
OPENAI_API_KEY=你的Key
OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1/   # 或其他 OpenAI 兼容地址
OPENAI_MODEL_NAME=支持视觉的模型名                         # 例: XiaomiMiMo/MiMo-V2-Flash / gpt-4o
```

可选推送：`NTFY_TOPIC_URL` / `BARK_URL` / `WX_BOT_URL` / Telegram 等。

## 闲鱼登录态

1. 安装项目自带 Chrome 扩展（`chrome-extension/`）
2. 登录闲鱼网页，用扩展导出登录状态
3. 在 Web UI「账号管理」粘贴登录态

无登录态时爬虫无法稳定抓取。

## 环境限制（Cloud Agent）

当前 Cursor Cloud 出口域名白名单**不包含**：

- `goofish.com` / `taobao.com`（闲鱼抓取）
- `api.openai.com` / `modelscope.cn`（AI 分析）
- 企微 / Bark 等推送域名

因此：本机 Web 控制台可正常打开，但**真实监控/AI 筛选/推送需在网络放行后**，或把同一套目录迁到本机/有完整出口的服务器再跑。

## 合规提醒

仅供个人闲置信息监控；勿用于黄牛倒卖。交易走平台担保，AI 结果仅供参考。
