---
name: compass-skills-client
description: 从云端读取和应用 Agent Skills。支持列出云端可用的 skills、查看 skill 详情、直接应用云端 skill（不下载到本地）。当用户需要使用云端技能、查询云端有哪些技能、或者想要应用远程 skill 时使用此技能。
compatibility: 需要网络访问和 curl 命令
metadata:
  author: cloud-skills
  version: "1.0"
  cloud_base_url: "http://42.193.182.174:8090/skills/"
---

# Cloud Skills

从云端读取和应用 Agent Skills，无需下载到本地。

## 云端配置

- **云端 Skills 目录**: `http://42.193.182.174:8090/skills/`
- 每个子目录代表一个 skill，例如 `http://42.193.182.174:8090/skills/pdf` 是 PDF 处理技能

## 可用命令

### 1. help - 帮助文档

当用户询问"cloud-skills 怎么用"、"帮助"、"help"等时，展示以下命令说明：

| 命令 | 触发词 | 说明 |
|------|--------|------|
| `help` | "帮助"、"help"、"怎么用" | 显示所有可用命令及使用方法 |
| `list` | "列出"、"有哪些"、"云端技能" | 列出云端所有可用的 skills |
| `show <name>` | "查看"、"详情"、"内容" | 查看指定 skill 的详细内容 |
| `apply <name>` | "应用"、"使用"、"执行" | 应用云端 skill 执行任务 |
| `refs <name>` | "引用"、"参考文档" | 查看 skill 的引用文件 |

**使用示例**：
- `help` → 显示帮助文档
- `list` → 列出云端 skills：pdf, docx...
- `show pdf` → 查看 pdf skill 的 SKILL.md 内容
- `apply pdf` → 应用 pdf skill 处理用户的 PDF 文件
- `refs pdf` → 查看 pdf skill 的 references 目录

### 2. list - 列出云端可用的 Skills

当用户询问"云端有哪些 skill"、"列出云端技能"等时执行：

```bash
curl -s http://42.193.182.174:8090/skills/ | grep -oP 'href="\K[^"]+(?=/")' | grep -v '\.\.'
```

解析返回的 HTML，提取所有可用的 skill 名称并展示给用户。

### 3. show - 查看云端 Skill 详情

当用户想了解某个云端 skill 的具体内容时：

```bash
curl -s http://42.193.182.174:8090/skills/{skill_name}/SKILL.md
```

将 `{skill_name}` 替换为实际的 skill 名称（如 `pdf`、`docx`）。

### 4. apply - 应用云端 Skill

**重要**：云端 skill 不能下载到本地，必须直接从云端读取并应用。

应用流程：

1. 首先获取云端 skill 的 SKILL.md 内容：
   ```bash
   curl -s http://42.193.182.174:8090/skills/{skill_name}/SKILL.md
   ```

2. 如果 skill 引用了其他文件（如 `references/REFERENCE.md`、`references/FORMS.md`），也从云端读取：
   ```bash
   curl -s http://42.193.182.174:8090/skills/{skill_name}/references/REFERENCE.md
   curl -s http://42.193.182.174:8090/skills/{skill_name}/references/FORMS.md
   ```

3. 解析获取到的 SKILL.md 内容，理解其中的指令和最佳实践

4. **直接按照云端 skill 的指令执行用户的任务**，无需将 skill 保存到本地

### 5. refs - 查看云端 Skill 的引用文件

某些 skill 可能包含额外的参考文档：

```bash
# 查看 skill 目录结构
curl -s http://42.193.182.174:8090/skills/{skill_name}/

# 读取特定引用文件
curl -s http://42.193.182.174:8090/skills/{skill_name}/references/{filename}
```

## 使用示例

### 示例 1：获取帮助

用户: "cloud-skills 怎么用？" / "帮助" / "help"

响应：展示上述命令表格，说明每个命令的用途和触发词。

### 示例 2：列出所有云端 skills

用户: "云端有哪些技能？"

执行：
```bash
curl -s http://42.193.182.174:8090/skills/
```

### 示例 3：应用云端 pdf skill 处理文件

用户: "使用云端 pdf 技能处理 document.pdf"

执行流程：
1. 获取 pdf skill 内容: `curl -s http://42.193.182.174:8090/skills/pdf/SKILL.md`
2. 阅读并理解 skill 指令
3. 按照 skill 中的指导处理用户的 PDF 文件

### 示例 4：查看 skill 详情

用户: "看看云端 docx 技能的内容"

执行：
```bash
curl -s http://42.193.182.174:8090/skills/docx/SKILL.md
```

## 注意事项

1. **始终从云端实时读取**：每次使用 skill 时都从云端获取最新内容，确保使用最新版本
2. **不缓存到本地**：skill 内容不应保存到本地文件系统
3. **完整读取**：如果 SKILL.md 中引用了其他文件，也需要从云端读取这些文件
4. **网络依赖**：此功能需要网络连接，如果无法访问云端服务器，应提示用户检查网络

## 错误处理

- 如果 curl 返回空内容或错误，提示用户检查网络连接
- 如果请求的 skill 不存在，提示用户使用列表命令查看可用的 skills
- 如果 skill 内容格式异常，尝试直接展示原始内容让用户判断
