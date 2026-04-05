# Analysis Data Service Skill

珍爱网数据分析服务技能 — 直连 CynosDB Libra 分析引擎，查询 15 个业务域、120+ 张业务表。

## 安装

```bash
bash install.sh
```

## 验证

```bash
python3 scripts/handler.py doctor
python3 scripts/handler.py data health
```

## 快速开始

```bash
# 列出所有业务域
python3 scripts/handler.py data sources

# 查看电销相关表
python3 scripts/handler.py data tables --source telesale

# 按关键词搜索表
python3 scripts/handler.py data search --keyword 投放ROI

# 查询数据
python3 scripts/handler.py data query --table Dept --limit 10

# 自由 SQL
python3 scripts/handler.py data sql --sql "SELECT * FROM compass_data.Dept LIMIT 5"

# 搜索员工
python3 scripts/handler.py org search 刘源

# 浏览部门树
python3 scripts/handler.py org dept
```

## 增量文件同步

项目内置了基于 `manifest.json` 的增量同步机制，客户端只需下载变更文件。

### 生成 manifest

```bash
python3 scripts/generate_manifest.py --root .
```

执行后在项目根目录生成 `manifest.json`，包含每个文件的 MD5 哈希和大小。

### 客户端增量拉取

```bash
# 预览差异（不实际下载）
python3 scripts/sync_client.py --server-url https://your-server.com/skill/ --local-dir ./local --dry-run

# 执行同步
python3 scripts/sync_client.py --server-url https://your-server.com/skill/ --local-dir ./local
```

### Git Hook 自动生成

启用 pre-commit hook 后，每次 commit 会自动更新 `manifest.json`：

```bash
git config core.hooksPath .githooks
```

## 给 AI Agent

如果你是 Cursor / Codex / Claude 之类的代理，标准流程：

```bash
bash install.sh
python3 scripts/handler.py doctor
```

### 结果分类

- `doctor` 退出码 `0`: 可用
- `doctor` 退出码 `1`: 不可用（依赖缺失或数据库不可达）
- `doctor` 退出码 `2`: 可用但有限制（部分数据库不可达）
