# 食光 ShiGuang · 智能菜谱 Agent

[![test](https://github.com/wushiyi105-jpg/smartcook/actions/workflows/test.yml/badge.svg)](https://github.com/wushiyi105-jpg/smartcook/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![零第三方依赖](https://img.shields.io/badge/dependencies-零-2ea44f)]()

> 告诉它你手边有什么食材,大模型帮你决定「做什么、怎么做、缺什么能换、能不能吃」。

一个**生活方向**的智能体项目:输入自然语言食材清单,运行时由大模型完成
**理解 → 识别 → 匹配 → 生成 → 判断**的完整链路,给出可做的菜、完整做法、
缺失食材的替代方案、以及忌口/过敏判断。

- 🐍 零第三方依赖,Python 3.10+ 标准库即可运行
- 🖥 双入口:**CLI**(命令行)+ **Web**(自带网页界面)
- 🧠 模型优先,离线演示模式兜底(无 key 也能跑通全流程)
- 🔌 兼容任意 OpenAI 风格接口:DeepSeek / OpenAI / 本地 Ollama / 通义 / 月之暗面…

---

## 判定标准对照(是否算 Agent)

| 判定标准 | 满足? | 依据 |
|---|---|---|
| **模型参与** | ✅ | 运行时确实调用大模型:理解口语食材并归一化、识别、匹配菜谱、**生成**做法、**判断**替代品与忌口。非「纯规则脚本」——内置规则引擎仅用于无 key 时的离线演示与单元测试。 |
| **独立运行** | ✅ | 对象本身是可运行的完整软件,有 CLI 与 Web 两个入口,能接收任务、执行、返回结果;不寄生在别的 Agent 里。 |
| **结论** | **是 Agent** | 两条均满足 |

关键边界对照:它不是「裸 prompt」、不是「仅 MCP 文件 I/O」、不是「AI 写代码」、
也不是「只提 AI 字眼的爬虫」——它每次运行都有模型在做真实的理解/判断/生成任务。

---

## 快速开始

```bash
# 1. 克隆(或本地进入项目目录)
cd smartcook

# 2. 配置模型 key(二选一)
cp .env.example .env      # 然后编辑 .env 填入你的 key
#   或直接 export LLM_API_KEY=你的key

# 3. 运行(无需 pip install)
python -m smartcook suggest 家里有番茄 鸡蛋 青椒 和一点肉末
```

默认对接 DeepSeek(最便宜的 `deepseek-flash`)。首次运行自动建库并写入 20 道内置家常菜。

---

## 命令参考

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
python -m smartcook --mock suggest ...      # 强制离线演示(不调用模型)
python -m smartcook --json swap 香醋        # 输出原始 JSON
python -m smartcook --model xxx --base-url xxx --api-key xxx ...
```

---

## 模型接入

通过环境变量(或 `.env`)配置,兼容任意 **OpenAI 风格 `/chat/completions`** 接口:

| 平台 | `LLM_BASE_URL` | `LLM_MODEL` |
|---|---|---|
| DeepSeek(默认) | `https://api.deepseek.com` | `deepseek-flash` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5` |
| 其他兼容网关 | 网关地址 | 网关模型名 |

三个变量:`LLM_API_KEY`(必填)、`LLM_BASE_URL`、`LLM_MODEL`。

---

## 离线演示模式(重要说明)

**未配置 `LLM_API_KEY` 时**,项目自动进入「离线演示模式」:由一个内置的
确定性规则引擎(关键词匹配 + 菜谱打分 + 替代速查表)跑通全流程,保证项目
开箱即用、也能做单元测试。

⚠️ 该模式**仅用于演示与测试**。项目的主路径、也是它之所以是 Agent 的路径,
**始终是模型路径**——配置 key 后,理解/识别/生成/判断全部由大模型完成,
规则引擎不再参与。

---

## 工作原理

一次 `suggest` 的完整链路(全部由模型完成):

```
输入:「家里有半颗白菜、两个番茄、一点肉末」
   │
   ├─ ① 理解/识别 ── 模型把口语食材归一化为规范清单
   │     ["番茄", "猪肉末", "白菜", ...]
   │
   ├─ ② 匹配/判断 ── 对照菜谱库,选出最合适的菜,标出缺什么
   │
   └─ ③ 生成 ── 输出推荐理由与缺失清单(联动 cook 生成完整做法)
```

其余能力:`cook`(生成做法)、`swap`(判断替代)、`diet`(判断忌口)。

## 目录结构

```
smartcook/
├── smartcook/
│   ├── agent.py      # 核心编排:模型主路径 + 离线回退
│   ├── llm.py        # LLM 客户端(urllib,兼容 OpenAI 风格接口 + .env 加载 + 空响应重试)
│   ├── mock.py       # 离线规则引擎(仅演示/测试)
│   ├── db.py         # SQLite 持久层(线程安全)
│   ├── recipes.py    # 内置菜谱加载
│   ├── cli.py        # 命令行入口
│   ├── web.py        # Web 界面(零依赖 http.server + JSON API)
│   └── __main__.py   # python -m smartcook
├── .github/workflows/test.yml   # CI:每次 push/PR 自动跑单元测试
├── data/seed_recipes.json       # 20 道内置家常菜
├── tests/test_smartcook.py      # 离线路径单元测试
├── .env.example             # 配置模板
└── README.md
```

## 测试

本地:

```bash
python -m unittest discover tests -v
```

CI:每次 push / PR,由 GitHub Actions 在 Python 3.10 / 3.11 / 3.12 上自动跑同一组测试,
结果见仓库顶部的 `test` 徽章。

## License

[MIT](./LICENSE)
