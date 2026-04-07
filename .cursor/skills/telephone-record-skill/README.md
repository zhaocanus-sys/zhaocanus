# 电话录音技能 (Telephone Record Skill)

如果你是 Cursor / Codex / Claude 之类的代理，并且用户让你"安装这个 Skill"，请按以下步骤操作。

## 安装

```bash
# macOS / Linux
bash install.sh

# Windows
python -m pip install pymysql
```

## 验证

```bash
python scripts/handler.py doctor
```

## 你必须完成的事情

1. 安装 pymysql 依赖
2. 运行 `python scripts/handler.py doctor` 检查数据库连通性
3. 用中文告诉用户结果

## 结果必须明确分类

你最终给用户的结论，必须尽量落到下面几类之一：

- 依赖问题
- 网络问题（数据库不可达）
- 数据库权限问题（某些表不可访问）

## 判定标准

- `doctor` 退出码 `0`: 全部可用
- `doctor` 退出码 `1`: 有错误（依赖缺失或数据库不可达）
- `doctor` 退出码 `2`: 有警告（部分表不可访问）

## 基本用法

```bash
python scripts/handler.py types                              # 列出录音类型
python scripts/handler.py query telsales --date 2026-03-19   # 查询电销录音
python scripts/handler.py detail callin 1                    # 查看录音详情
python scripts/handler.py schema voicefox                    # 查看表结构
```

## 增量文件同步

本项目支持基于 `manifest.json` 的增量文件同步，客户端只需下载变更的文件。

### 生成 manifest

```bash
python scripts/generate_manifest.py                     # 在项目根目录生成 manifest.json
python scripts/generate_manifest.py --root /path/to/dir  # 指定项目根目录
python scripts/generate_manifest.py --exclude docs logs  # 额外排除目录
```

### 客户端增量同步

```bash
# 预览差异（不实际下载）
python scripts/sync_client.py --server-url http://example.com/project --dry-run

# 执行同步
python scripts/sync_client.py --server-url http://example.com/project --local-dir ./local-copy
```

### 启用 Git Hook 自动更新 manifest

每次 `git commit` 时自动重新生成 `manifest.json` 并加入暂存区：

```bash
git config core.hooksPath .githooks
```
