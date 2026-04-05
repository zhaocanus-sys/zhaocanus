#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 分析引擎
支持双后端: Anthropic (Claude) / 智谱 (GLM)
"""
import os
import sys

# ── Prompt 模板 ──────────────────────────────────

DAILY_PROMPT = """你是珍爱网技术团队的 AI 助理。
请根据以下企业微信群聊记录，生成结构化日报。

## 输出要求

### 今日讨论摘要
- 按议题分组，每个议题用一句话总结结论，标注参与人

### 已达成决策
- 列出今天达成的具体决定，标注决策人

### 待跟进事项 (TODO)
- [ ] 事项描述 -- 负责人: @xxx

### 风险 & 阻塞
- 识别讨论中提到的延期风险或阻塞点

### 明日关注
- 根据讨论推断明天需关注的事项

## 规则
1. 过滤闲聊和表情，聚焦技术讨论和业务进展
2. 关键数字和技术细节保留原文
3. 未明确结论的标注 [待定]
4. 语言简练，每条不超过 2 句话

---
群聊记录:
{chat_log}"""

WEEKLY_PROMPT = """你是技术团队周报助手。
请从本周群聊记录中提取周报素材：

### 本周完成
| 事项 | 详情 | 相关人员 | 完成日期 |
|------|------|---------|---------|

### 本周进行中
| 事项 | 当前进度 | 阻塞点 | 预计完成 |
|------|---------|--------|---------|

### 下周计划
- 根据讨论推断下周重点

### 关键数据
- 讨论中出现的关键指标

## 规则
1. 只提取工作进展相关内容
2. 跨天讨论的事项合并为一条

---
本周群聊记录:
{chat_log}"""

MEETING_PROMPT = """请将以下群聊讨论整理为会议纪要：

## 会议纪要
**参与人员：** 从发言中提取
**讨论主题：** 自动归纳

### 议题与结论
（按讨论顺序梳理每个议题的背景、要点和结论）

### 行动项 (Action Items)
| 序号 | 行动项 | 负责人 | 截止日期 | 优先级 |
|------|--------|--------|---------|--------|

### 遗留问题
（未解决的问题）

---
群聊记录:
{chat_log}"""

TEMPLATES = {
    "daily": DAILY_PROMPT,
    "weekly": WEEKLY_PROMPT,
    "meeting": MEETING_PROMPT,
}


# ── 后端检测 ──────────────────────────────────────

def _detect_backend() -> str:
    """检测可用 AI 后端，优先 Anthropic"""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("Z_API_KEY"):
        return "zai"
    print("❌ 未设置 AI API Key，请配置以下任意一项:")
    print("   export ANTHROPIC_API_KEY=<your-key>")
    print("   export Z_API_KEY=<your-key>")
    sys.exit(1)


def _analyze_anthropic(prompt: str) -> str:
    """Anthropic Claude 后端"""
    try:
        import anthropic
    except ImportError:
        print("❌ anthropic 未安装: pip3 install anthropic")
        sys.exit(1)

    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    print(f"   后端: Anthropic / {model}")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def _analyze_zai(prompt: str) -> str:
    """智谱 GLM 后端"""
    try:
        from zhipuai import ZhipuAI
    except ImportError:
        print("❌ zhipuai 未安装: pip3 install zhipuai")
        sys.exit(1)

    api_key = os.environ["Z_API_KEY"]
    model = os.environ.get("Z_MODEL", "glm-4-flash")
    print(f"   后端: 智谱 / {model}")
    client = ZhipuAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


# ── 公开接口 ──────────────────────────────────────

def analyze_chat(chat_log: str, template: str = "daily") -> str:
    """
    主入口：分析聊天记录

    Args:
        chat_log: 格式化后的聊天记录文本
        template: 模板名 (daily / weekly / meeting)

    Returns:
        AI 生成的结构化分析结果
    """
    prompt_tpl = TEMPLATES.get(template, TEMPLATES["daily"])
    prompt = prompt_tpl.format(chat_log=chat_log)

    backend = _detect_backend()
    if backend == "anthropic":
        return _analyze_anthropic(prompt)
    else:
        return _analyze_zai(prompt)
