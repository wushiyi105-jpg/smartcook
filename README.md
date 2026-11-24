# 食光 ShiGuang · 智能菜谱 Agent

[![test](https://github.com/wushiyi105-jpg/smartcook/actions/workflows/test.yml/badge.svg)](https://github.com/wushiyi105-jpg/smartcook/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

![demo](assets/demo.gif)

> 不知道吃什么的时候,告诉它你手边有什么,大模型帮你决定「做什么、怎么做、缺什么能换、能不能吃」。

一个输入食材清单、由大模型完成「理解 → 识别 → 匹配 → 生成 → 判断」的智能菜谱应用。
**CLI + Web 双入口,零第三方依赖,开箱即用。**

## ✨ 特性

- 🥘 **说人话点菜** —— 「家里有半颗白菜、两个番茄、一点肉末」也能听懂,自动整理成规范食材
- 🍳 **智能推荐** —— 对照内置菜谱库,告诉你哪道能做、还缺什么主料
- 📝 **做法生成** —— 任意一道菜都能给出用料、步骤、火候、贴士,还能结合忌口个性化调整
- 🔄 **食材替代** —— 缺某样调料/食材?给出可行的替代方案和影响
- 🥗 **忌口判断** —— 花生过敏、不吃辣、减脂……提前判断这道菜能不能吃、怎么改
- 🧊 **库存管理** —— 记录家中食材,随时推荐可做的菜
- 🖥 **双入口** —— 命令行 + 网页界面(网页里每一步都可视化)
- ⚡ **零依赖** —— 纯 Python 标准库,Python 3.10+ 即可运行,无需 pip install

## 🚀 快速开始

```bash
git clone https://github.com/wushiyi105-jpg/smartcook.git
cd smartcook

# 配置模型 key(二选一)
cp .env.example .env       # 编辑 .env 填入 LLM_API_KEY
#   或 export LLM_API_KEY=你的key

# 直接开用
python -m smartcook suggest 家里有番茄 鸡蛋 青椒 和一点肉末
```

默认对接 DeepSeek(最便宜的 `deepseek-flash`),首次运行自动建库并内置 20 道家常菜。
未配置 key 时自动进入离线演示模式(内置规则引擎兜底),也能跑通全流程。

## 📖 命令参考

```bash
# 🍳 推荐:根据手边食材推荐能做的菜
python -m smartcook suggest 番茄 鸡蛋 青椒 肉末

# 🍽 做法:生成某道菜的完整做法(可结合忌口)
python -m smartcook cook 麻婆豆腐 --diet 不吃辣

# 🔄 替代:缺某食材,找可行替代品
python -m smartcook swap 郫县豆瓣酱

# 🥗 忌口:判断某道菜是否适合某忌口/过敏
python -m smartcook diet 宫保鸡丁 --restrictions 花生过敏

# 🧊 库存:管理家中食材
python -m smartcook inventory add 番茄 --qty 2个
python -m smartcook inventory list

# 📖 菜谱库
python -m smartcook recipes            # 列出全部
python -m smartcook recipes 番茄炒蛋   # 查看单道

# 🌐 Web 界面(浏览器打开 http://127.0.0.1:8000)
python -m smartcook web --port 8000

# 全局选项
python -m smartcook --json swap 香醋        # 输出原始 JSON
python -m smartcook --mock suggest ...      # 强制离线演示(不调用模型)
```

## 🔌 模型接入

兼容任意 **OpenAI 风格 `/chat/completions`** 接口,改三个环境变量即可:

| 平台 | `LLM_BASE_URL` | `LLM_MODEL` |
|---|---|---|
| DeepSeek(默认) | `https://api.deepseek.com` | `deepseek-flash` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5` |
| 其他兼容网关 | 网关地址 | 网关模型名 |

## 🧠 工作原理

一次 `suggest` 的完整链路(全部由模型完成):

```
输入:「家里有半颗白菜、两个番茄、一点肉末」
   │
   ├─ ① 理解/识别 ── 把口语食材归一化为规范清单
   │     ["番茄", "猪肉末", "白菜", ...]
   │
   ├─ ② 匹配/判断 ── 对照菜谱库,选出最合适的菜,标出缺什么
   │
   └─ ③ 生成 ── 输出推荐理由与缺失清单(联动 cook 生成完整做法)
```

其余能力:`cook`(生成做法)、`swap`(判断替代)、`diet`(判断忌口)。

## 🗂 目录结构

```
smartcook/
├── smartcook/
│   ├── agent.py      # 核心编排:模型主路径 + 离线回退
│   ├── llm.py        # LLM 客户端(OpenAI 风格接口 + .env 加载 + 空响应重试)
│   ├── mock.py       # 离线规则引擎(仅演示/测试)
│   ├── db.py         # SQLite 持久层(线程安全)
│   ├── recipes.py    # 内置菜谱加载
│   ├── cli.py        # 命令行入口
│   ├── web.py        # Web 界面(零依赖 http.server + JSON API)
│   └── __main__.py   # python -m smartcook
├── data/seed_recipes.json      # 20 道内置家常菜
├── assets/demo.gif             # 演示动图
├── tests/test_smartcook.py     # 离线路径单元测试
├── .github/workflows/test.yml  # CI
├── .env.example
└── README.md
```

## ✅ 测试

本地:

```bash
python -m unittest discover tests -v
```

每次 push / PR 由 GitHub Actions 在 Python 3.10 / 3.11 / 3.12 上自动跑同一组测试,结果见顶部 `test` 徽章。

## 👤 作者

- 邮箱:[wushiyi105@gmail.com](mailto:wushiyi105@gmail.com)
- 电话:18384198104
- GitHub:[@wushiyi105-jpg](https://github.com/wushiyi105-jpg)

## 📄 License

[MIT](./LICENSE)
