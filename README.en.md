# ShiGuang SmartCook · Recipe Agent

[![test](https://github.com/wushiyi105-jpg/smartcook/workflows/test/badge.svg)](https://github.com/wushiyi105-jpg/smartcook/actions) [![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)]() [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE) [![codecov](https://codecov.io/gh/wushiyi105-jpg/smartcook/branch/main/graph/badge.svg)](https://codecov.io/gh/wushiyi105-jpg/smartcook)

![usage](assets/demo.gif)

> When you do not know what to eat, tell it what you have on hand, and the model decides "what to cook, how to cook it, what can be swapped for what is missing, and whether it is safe to eat".

A recipe app whose input is an ingredient list and whose reasoning — understand → identify → match → generate → judge — is done by the model.
**Dual CLI + Web entry points, zero third-party dependencies, works out of the box.**

## ✨ Features

- 🥘 **Order in plain speech** — "half a cabbage, two tomatoes, a bit of minced pork at home" is understood and tidied into canonical ingredients
- 🍳 **Smart recommendation** — checks the built-in recipe library and tells you which dishes are makeable, and what main ingredient each still lacks
- 📝 **Method generation** — any dish gets ingredients, steps, heat levels and tips, adjustable around your dietary restrictions
- 🔄 **Ingredient substitution** — missing a condiment or an ingredient? It proposes feasible swaps and what they change
- 🥗 **Dietary check** — peanut allergy, no spice, cutting fat… it judges up front whether this dish is safe and how to adapt it
- 🧊 **Pantry management** — record what is at home and get recommendations on demand
- 🖥 **Two entry points** — command line plus a Web UI where every step is visualised
- ⚡ **Zero dependencies** — pure Python standard library, Python 3.10+ is enough, no pip install needed

## 🚀 Quick start

```bash
git clone https://github.com/wushiyi105-jpg/smartcook.git
cd smartcook

# configure a model key (pick one)
cp .env.example .env       # edit .env and put in LLM_API_KEY
#   or: export LLM_API_KEY=your-key

# start using it
python -m smartcook suggest 家里有番茄 鸡蛋 青椒 和一点肉末
```

It talks to DeepSeek by default (the cheapest, `deepseek-flash`), creates the database on first run, and ships 20 home-style dishes.
> **⚠️ The project carries no API key of its own — put in your own** (`.env` is already gitignored and never committed).
With no key configured it falls into offline mode (a built-in rule engine), and the full flow still works.

Run in Docker:

```bash
docker build -t smartcook .
docker run -p 8000:8000 smartcook
```

## 🤔 Why not just ask a general LLM

A general chat model can write a plausible tomato-and-egg recipe. What SmartCook adds is the four things it cannot do:

1. **Reproducible results** — the recipe library, pantry and missing-ingredient list live locally, and the dish names a model returns are forced onto the built-in recipes ("tomato-and-egg" and "egg-and-tomato" never become two different dishes). With `--mock` the whole path is deterministic: the same ingredients asked twice give the same list, which is what makes it testable.
2. **Data stays local** — what is in your kitchen, who cannot eat peanuts, which dishes were recommended before, all sit in `data/smartcook.db`. Only the ingredient text you type is sent to the model; the pantry and restrictions are never synced anywhere.
3. **Works offline** — with no key it enters offline mode and normalises ingredients, matches recipes, proposes swaps and judges restrictions through built-in rules, with all 20 dishes intact. A general chat assistant simply stops when offline.
4. **Structured output** — every command returns fixed fields (makeable dishes, missing main ingredients, substitutes, dietary verdict), and `--json` feeds them straight into another program; CLI and Web share the same result. A chat model gives you prose you still have to parse.

## 🎯 Use cases

- **Home after work, staring at the fridge**: throw in "half a cabbage, two tomatoes, a bit of minced pork" as you would say it, and `suggest` returns two to five makeable dishes plus the one main ingredient each still lacks. If too much is missing, that is your shopping list, and you skip flipping through recipes one by one.
- **Someone at home has an allergy or restriction**: run `diet` first to see whether the dish is safe and where the risk sits, then `cook --diet no-chilli` to handle the chilli in the method, then `swap` to replace a missing condiment and see what it does to the taste.
- **Cooking for one without buying duplicates**: keep what you have in `inventory` and `suggest` prefers it. Add new purchases as you go and ask again a few days later, instead of buying the same vegetable twice and binning the first lot.

## 🗺 Roadmap

- **Pantry quantities**: have `cook` deduct amounts from `inventory` instead of only tracking "have / have not".
- **One-tap shopping list**: merge and deduplicate everything `suggest` reports as missing into a single list you can take to the shop.
- **Recipe import and export**: load your own family recipes from JSON to replace or extend the built-in 20, and export them as a backup.
- **Step timer**: a countdown in the Web UI for steps that need waiting — stewing, steaming, resting dough — instead of reaching for your phone.
- **Follow-up questions on one dish**: ask "how do I fix it if I oversalted" or "can I use an air fryer" in the same session, keeping context instead of starting over.

## ❓ FAQ

**Where do I get an API key?**
The project ships without one. It talks to DeepSeek (`https://api.deepseek.com`) by default: create a key in the DeepSeek console, then put it in `.env` as `LLM_API_KEY` or `export LLM_API_KEY=your-key`. Any OpenAI-style `/chat/completions` endpoint works, including a local Ollama — see the table above for the URL and model name.

**Where is data stored, and is it uploaded?**
By default in `data/smartcook.db`, a single SQLite file, and `SMARTCOOK_DB` changes the path. Pantry, recipes and history stay on this machine; when a model is called, only the ingredient or dish text from that one request is sent, never the whole database.

**Does it work without a key?**
Yes. It enters offline mode automatically: normalisation, matching, swaps and dietary checks come from rules and cover the built-in 20 dishes. A dish outside the library is reported as not in the library rather than invented; a model is needed only when you want the method for any dish.

**How do I switch models?**
Change three environment variables — `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` — with no code changes, or override temporarily with `--model`.

**Why do two recommendations differ slightly?**
The model step samples, so wording and ordering can change; dish names are still forced onto the local library and missing ingredients follow the library's ingredient table. For fully stable output add `--mock`, where the path is pure rules and recomputable.

## 📖 Command reference

```bash
# 🍳 suggest: recommend dishes from what is on hand
python -m smartcook suggest 番茄 鸡蛋 青椒 肉末

# 🍽 cook: full method for one dish (respects restrictions)
python -m smartcook cook 麻婆豆腐 --diet 不吃辣

# 🔄 swap: find workable substitutes for a missing ingredient
python -m smartcook swap 郫县豆瓣酱

# 🥗 diet: judge whether a dish suits a restriction or allergy
python -m smartcook diet 宫保鸡丁 --restrictions 花生过敏

# 🧊 inventory: manage pantry items
python -m smartcook inventory add 番茄 --qty 2个
python -m smartcook inventory list

# 📖 recipe library
python -m smartcook recipes            # list everything
python -m smartcook recipes 番茄炒蛋   # show one

# 🌐 Web UI (open http://127.0.0.1:8000)
python -m smartcook web --port 8000

# global options
python -m smartcook --json swap 香醋        # raw JSON output
python -m smartcook --mock suggest ...      # force offline mode (no model call)
```

## 🔌 Model backends

Works with any **OpenAI-style `/chat/completions`** endpoint, **using your own API key**; three environment variables are all it takes:

| Platform | `LLM_BASE_URL` | `LLM_MODEL` |
|---|---|---|
| DeepSeek (default) | `https://api.deepseek.com` | `deepseek-flash` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Local Ollama | `http://localhost:11434/v1` | `qwen2.5` |
| Other compatible gateway | gateway URL | gateway model name |

> `LLM_API_KEY` is required; `LLM_BASE_URL` and `LLM_MODEL` are optional.

## 🧠 How it works

The full chain behind one `suggest` call (all of it done by the model):

```
Input: "家里有半颗白菜、两个番茄、一点肉末"
   │
   ├─ ① understand / identify ── normalise colloquial ingredients into a canonical list
   │     ["番茄", "猪肉末", "白菜", ...]
   │
   ├─ ② match / judge ── check the recipe library, pick the best dishes, mark what is missing
   │
   └─ ③ generate ── output the reasoning and the missing list (feeds cook for the full method)
```

The other capabilities: `cook` (generate the method), `swap` (judge substitutions), `diet` (judge restrictions).

### Data flow

How one piece of data moves between the modules:

```mermaid
flowchart LR
    A[手边食材] --> B[db.py<br/>读家庭库存]
    B --> C[agent.py<br/>模型抽出食材清单]
    C --> D[recipes.py + db.py<br/>取菜谱库候选]
    D --> E[agent.py<br/>模型决定做什么 · 缺什么能换]
    E --> F{有没有可用的 key}
    F -->|没有| G[mock.py<br/>确定性规则回退]
    F -->|有| E
    G --> H[db.py 落库]
    E --> H
    H --> I[cli.py / web.py]
```

## 🗂 Layout

```
smartcook/
├── smartcook/
│   ├── agent.py      # core orchestration: model path + offline fallback
│   ├── llm.py        # LLM client (OpenAI-style API + .env loading + empty-response retry)
│   ├── mock.py       # offline rule engine (fallback / tests)
│   ├── db.py         # SQLite persistence layer (thread safe)
│   ├── recipes.py    # built-in recipe loading
│   ├── cli.py        # command line entry
│   ├── web.py        # Web UI (http.server + JSON API, no dependencies)
│   └── __main__.py   # python -m smartcook
├── data/seed_recipes.json      # 20 built-in home-style dishes
├── assets/demo.gif             # demo animation
├── tests/test_smartcook.py     # offline path unit tests
├── .github/workflows/test.yml  # CI
├── .env.example
└── README.md
```

## ✅ Tests

Locally:

```bash
python -m unittest discover tests -v
```

Every push / PR runs the same suite on GitHub Actions across Python 3.10 / 3.11 / 3.12; see the `test` badge at the top.

## 👤 Author

- Name: shiyi
- Email: [wushiyi105@gmail.com](mailto:wushiyi105@gmail.com)
- Phone: 18384198104
- GitHub: [@wushiyi105-jpg](https://github.com/wushiyi105-jpg)

## 📄 License

[MIT](./LICENSE)
