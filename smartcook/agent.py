"""核心 Agent 编排:模型主路径 + 离线回退。

四个能力:
  suggest —— 输入手边食材,理解/识别食材 → 匹配菜谱库 → 推荐可做的菜
  cook    —— 指定菜名,生成完整做法(结合手边食材与忌口个性化)
  swap    —— 缺某食材时,判断可行的替代品
  diet    —— 结合忌口/过敏,判断某道菜是否适合并给出调整

每条路径优先调用大模型;未配置 key 或显式 --mock 时回退到离线规则引擎。
"""

from __future__ import annotations

from . import llm, mock
from .llm import LLMError

JSON_ONLY = "只输出 JSON,不要输出任何解释或多余文字。"


def _use_model(config: dict | None, force_mock: bool) -> bool:
    if force_mock:
        return False
    cfg = {**llm.default_config(), **(config or {})}
    return bool(cfg.get("api_key"))


def _cfg(config: dict | None) -> dict:
    return {**llm.default_config(), **(config or {})}


def _chat(messages, config, temperature=0.2, max_tokens=2048) -> str:
    return llm.chat(messages, config=_cfg(config), temperature=temperature, max_tokens=max_tokens)


def _match_recipe_name(name: str, db) -> str | None:
    """把模型返回的菜名归一到菜谱库(用于后续 cook 联动)。"""
    if db.get_recipe(name):
        return name
    for cand in db.all_recipes():
        if name in cand["name"] or cand["name"] in name:
            return cand["name"]
    return None


# ---------------------------------------------------------------------------
# suggest
# ---------------------------------------------------------------------------
def suggest(ingredients_text: str, config: dict | None = None, db=None, force_mock: bool = False) -> dict:
    if not _use_model(config, force_mock):
        return mock.suggest(ingredients_text, db)

    cfg = _cfg(config)

    # 第一步:理解 + 识别 —— 把自然语言整理成规范食材清单
    raw = _chat([{
        "role": "system",
        "content": "你是家常菜助手。把用户描述的可用食材整理成规范食材名列表,合并同义说法。",
    }, {
        "role": "user",
        "content": f"用户手边食材:{ingredients_text}\n{JSON_ONLY}\n输出格式:{{\"ingredients\":[\"食材1\",\"食材2\"]}}",
    }], cfg)
    ingredients = llm.extract_json(raw).get("ingredients", [])

    # 第二步:判断 + 生成 —— 对照菜谱库选出最合适的菜
    catalog = db.recipe_catalog()
    raw2 = _chat([{
        "role": "system",
        "content": "你是家常菜推荐助手。根据可用食材,从菜谱库中选出最合适的 2~5 道菜。菜名必须与菜谱库完全一致。基础调味料(油、盐、糖、生抽、老抽、料酒、淀粉、醋、香油、花椒等)视为常备,不计入缺失。",
    }, {
        "role": "user",
        "content": (
            f"菜谱库(每行:菜名:食材):\n{catalog}\n\n"
            f"可用食材:{ingredients}\n{JSON_ONLY}\n"
            f"输出格式:{{\"dishes\":[{{\"name\":\"菜名\",\"match\":\"已匹配食材(逗号分隔,如:番茄、鸡蛋)\","
            f"\"missing\":[\"缺失食材\"],\"reason\":\"一句话理由\"}}]}}"
        ),
    }], cfg, max_tokens=2048)
    dishes = llm.extract_json(raw2).get("dishes", [])

    # 归一化菜名,保证与菜谱库联动
    for d in dishes:
        canonical = _match_recipe_name(d.get("name", ""), db)
        if canonical:
            d["name"] = canonical
    return {"ingredients": ingredients, "dishes": dishes}


# ---------------------------------------------------------------------------
# cook
# ---------------------------------------------------------------------------
def cook(name: str, config: dict | None = None, db=None, diet: str | None = None,
         on_hand: str | None = None, force_mock: bool = False) -> dict:
    if not _use_model(config, force_mock):
        result = mock.cook(name, db)
        if not result:
            raise LLMError(f"离线库未收录「{name}」,请配置 LLM_API_KEY 后由模型生成做法")
        return result

    cfg = _cfg(config)
    extra = []
    if on_hand:
        extra.append(f"食客手边还有这些食材:{on_hand},可尽量利用。")
    if diet:
        extra.append(f"食客忌口/要求:{diet},请在做法与提示中体现并给出替代方案。")
    suffix = "\n".join(extra)

    raw = _chat([{
        "role": "system",
        "content": "你是专业家常菜厨师,给出清晰、可执行的完整做法,用量尽量具体。",
    }, {
        "role": "user",
        "content": (
            f"请给出「{name}」的完整做法。{suffix}\n{JSON_ONLY}\n输出格式:\n"
            '{"name":"菜名","ingredients":[{"name":"食材","amount":"用量"}],'
            '"steps":["步骤1","步骤2"],"tips":["贴士1"],'
            '"time_minutes":数字,"difficulty":"简单/中等/较难","servings":"份量"}'
        ),
    }], cfg, max_tokens=3000)

    data = llm.extract_json(raw)
    return {
        "name": data.get("name", name),
        "ingredients": data.get("ingredients", []),
        "steps": data.get("steps", []),
        "tips": data.get("tips", []),
        "time_minutes": data.get("time_minutes"),
        "difficulty": data.get("difficulty"),
        "servings": data.get("servings"),
    }


# ---------------------------------------------------------------------------
# swap
# ---------------------------------------------------------------------------
def swap(ingredient: str, config: dict | None = None, force_mock: bool = False) -> dict:
    if not _use_model(config, force_mock):
        return mock.swap(ingredient)

    cfg = _cfg(config)
    raw = _chat([{
        "role": "system",
        "content": "你是厨房食材替代专家,判断缺失食材的可行替代品及影响。",
    }, {
        "role": "user",
        "content": (
            f"我做饭缺「{ingredient}」,请给出 2~3 个可行替代品及一句说明。{JSON_ONLY}\n"
            '输出格式:{"original":"缺失食材","substitutes":[{"name":"替代品","note":"说明"}]}'
        ),
    }], cfg)
    data = llm.extract_json(raw)
    return {"original": data.get("original", ingredient), "substitutes": data.get("substitutes", [])}


# ---------------------------------------------------------------------------
# diet
# ---------------------------------------------------------------------------
def diet(dish: str, restrictions: str, config: dict | None = None, db=None,
         force_mock: bool = False) -> dict:
    if not _use_model(config, force_mock):
        return mock.diet(dish, restrictions, db)

    cfg = _cfg(config)
    raw = _chat([{
        "role": "system",
        "content": "你是营养与忌口判断助手,判断某道菜是否适合食客,并给出调整建议。",
    }, {
        "role": "user",
        "content": (
            f"菜品:{dish};食客忌口/要求:{restrictions}。{JSON_ONLY}\n"
            '输出格式:{"dish":"菜名","restrictions":"忌口","verdict":"适合/需注意/不适合",'
            '"reasons":["原因"],"adjustments":["调整建议"]}'
        ),
    }], cfg)
    data = llm.extract_json(raw)
    return {
        "dish": data.get("dish", dish),
        "restrictions": data.get("restrictions", restrictions),
        "verdict": data.get("verdict", "需注意"),
        "reasons": data.get("reasons", []),
        "adjustments": data.get("adjustments", []),
    }
