# 🤖 arXiv Daily Radar - 学术前沿雷达

> 一个专为 AI/LLM 研究人员打造的“零成本” arXiv 论文自动化追踪系统。

面对每天 arXiv 呈井喷式增长的 NLP/LLM 论文，本项目通过 Python + GitHub Actions + 飞书机器人，基于精准正则匹配，实现一个完全自动化的每日学术播报，从海量预印本中精准狙击你的专属研究领域（e.g. Agentic RL），并排版为简洁的 Markdown 卡片推送至你的个人飞书。

## ✨ 核心特性

- 🎯 **双重正则捕获**：支持为每个研究方向配置“高精度（锁定核心算法）”与“高召回（概念组合查找）”双重正则表达式
- 🌍 **原生时区免疫**：内置强制北京时间（UTC+8）对齐机制，解决 GitHub Actions 服务器 UTC 时区带来的时间切割错乱问题
- 🧩 **配置与代码解耦**：采用 YAML 独立配置文件，未来修改或扩展研究领域只需修改配置文件，无需触碰核心 Python 代码
- 🛡️ **云端安全零成本**：依托 GitHub Actions 免费定时运行，飞书 Webhook 和个人邮箱等敏感信息均通过 GitHub Secrets 注入，代码库 100% 安全开源

## 🚀 部署与使用指南

### 1. 准备工作
- 在个人飞书中创建一个群组，添加**自定义机器人**，并保存好 `Webhook URL`
- Fork 或 Clone 本仓库到你的本地或 GitHub

### 2. 配置你的专属追踪领域 (`config.yaml`)
修改项目根目录下的 `config.yaml`，按以下格式配置你所关心的研究方向：
```yaml
Agentic RL:
  categories: "(cat:cs.CL+OR+cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.MA)"
  high_precision: '(?i)\b(Agentic\s*RL|RLHF|RLAIF|GRPO|DPO|KTO|PPO|Reward\s*Model(ing)?)\b'
  high_recall: '(?i)(?=.*\b(agent(s|ic)?|llm(s)?)\b)(?=.*\b(rl|reward|policy|preference)\b).*'
  