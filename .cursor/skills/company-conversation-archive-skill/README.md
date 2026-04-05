# 企微会话存档技能 (company-conversation-archive-skill)

如果你是 Cursor / Codex / Claude 之类的代理，并且用户让你"安装这个 Skill"，请按以下步骤执行：

```bash
pip install pymysql requests
python scripts/handler.py doctor
```

## 安装后验证

1. 运行 `python scripts/handler.py doctor` 检查数据库连接
2. 运行 `python scripts/handler.py list-users` 确认可读取数据
3. 如有错误，根据 doctor 输出的诊断分类处理

## 结果分类

- **依赖问题**: pymysql 未安装
- **网络问题**: 数据库连接失败（需要 VPN 或网络白名单）
- **数据问题**: 表可访问但无数据

## 增量同步

本项目支持增量文件同步——客户端只下载变更过的文件，而非每次全量拉取。

### 服务端：生成 manifest

部署前在项目根目录执行，生成 `manifest.json` 文件清单：

```bash
python scripts/generate_manifest.py
```

可选参数：

| 参数 | 说明 |
|------|------|
| `--root <path>` | 指定项目根目录（默认当前目录） |
| `--output <name>` | 输出文件名（默认 manifest.json） |
| `--exclude "<pattern>"` | 额外排除规则，可多次指定 |

### 客户端：增量拉取

```bash
python scripts/sync_client.py --server-url http://your-server:port --local-dir ./local
```

可选参数：

| 参数 | 说明 |
|------|------|
| `--dry-run` | 仅显示差异，不实际下载 |
| `--keep-deleted` | 保留服务器已删除的本地文件 |

### 自动生成 manifest（Git Hook）

启用 pre-commit hook，每次 commit 自动更新 `manifest.json`：

```bash
git config core.hooksPath .githooks
```
