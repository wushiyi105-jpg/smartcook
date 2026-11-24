"""离线演示模式:无 API key 时的确定性规则引擎。

定位:让项目在没有 key 时也能端到端跑通、以及供单元测试使用。
配置 LLM_API_KEY 后,真正的「理解 / 识别 / 匹配 / 生成 / 判断」全部由
大模型完成,本模块不再参与。
"""

from __future__ import annotations

# 食材同义词表:把口语说法归一到规范食材名(仅离线模式使用)。
SYNONYMS: dict[str, list[str]] = {
    "番茄": ["番茄", "西红柿"],
    "土豆": ["土豆", "马铃薯", "洋芋"],
    "鸡蛋": ["鸡蛋", "鸡子", "鸭蛋", "蛋"],
    "猪里脊": ["里脊", "猪里脊", "肉丝", "瘦肉", "猪肉"],
    "鸡胸肉": ["鸡胸", "鸡脯", "鸡肉"],
    "鸡翅": ["鸡翅"],
    "鸡腿": ["鸡腿"],
    "牛肉末": ["牛肉", "肉末", "绞肉"],
    "牛腩": ["牛腩"],
    "排骨": ["排骨", "肋排"],
    "青椒": ["青椒", "尖椒", "辣椒"],
    "干辣椒": ["干辣椒"],
    "白菜": ["白菜", "大白菜"],
    "生菜": ["生菜"],
    "西兰花": ["西兰花", "西蓝花", "绿菜花"],
    "茄子": ["茄子"],
    "四季豆": ["四季豆", "豆角", "芸豆", "豇豆"],
    "冬瓜": ["冬瓜"],
    "豆腐": ["豆腐"],
    "香菇": ["香菇", "冬菇", "花菇"],
    "木耳": ["木耳", "黑木耳"],
    "胡萝卜": ["胡萝卜", "红萝卜"],
    "黄瓜": ["黄瓜"],
    "洋葱": ["洋葱"],
    "蒜": ["蒜", "大蒜"],
    "姜": ["姜", "生姜"],
    "小葱": ["葱", "小葱", "香葱"],
    "大米": ["大米", "米饭", "米"],
    "皮蛋": ["皮蛋", "松花蛋"],
    "紫菜": ["紫菜"],
    "花生米": ["花生"],
    "虾皮": ["虾皮"],
    "火腿肠": ["火腿", "火腿肠"],
    "可乐": ["可乐"],
    "时令绿叶菜": ["青菜", "绿叶菜", "时蔬", "油菜", "菠菜", "小白菜"],
}

# 视为家中常备的基础调料,离线模式下不当作「缺失食材」。
STAPLES = {
    "食用油", "盐", "白糖", "糖", "生抽", "老抽", "料酒", "淀粉",
    "白胡椒粉", "香油", "香醋", "醋", "蚝油", "花椒", "花椒粉", "面粉",
}

# 常见替代品速查(离线模式用;在线由模型生成更贴合的判断)。
SUBSTITUTES: dict[str, list[dict]] = {
    "香醋": [{"name": "陈醋", "note": "风味更醇厚,酸度接近"}, {"name": "白醋", "note": "更酸更冲,酌情减量"}, {"name": "柠檬汁", "note": "果酸清香,适合凉拌"}],
    "蚝油": [{"name": "生抽+少量糖", "note": "提鲜接近"}, {"name": "鱼露", "note": "鲜味浓,略咸,减盐"}],
    "郫县豆瓣酱": [{"name": "黄豆酱+辣椒面", "note": "接近红油香辣"}, {"name": "甜面酱+辣椒油", "note": "偏甜口替代"}],
    "淀粉": [{"name": "面粉", "note": "用量减半,易结块需搅匀"}, {"name": "藕粉/木薯粉", "note": "勾芡更透亮"}],
    "可乐": [{"name": "糖+生抽+水", "note": "近似甜咸口,缺焦糖香"}],
    "鸡蛋": [{"name": "嫩豆腐", "note": "素替,口感接近,需调味"}, {"name": "鹰嘴豆水", "note": "烘焙替代,中式炒菜不推荐"}],
    "猪里脊": [{"name": "鸡胸肉", "note": "更清淡低脂"}, {"name": "牛里脊", "note": "更香,火候要快"}],
    "牛腩": [{"name": "牛腱子", "note": "更瘦,炖煮时间相近"}, {"name": "猪五花", "note": "更肥润,适合红烧"}],
    "香油": [{"name": "熟白芝麻油", "note": "香味接近"}, {"name": "花椒油", "note": "麻香,别用多"}],
    "干辣椒": [{"name": "辣椒面", "note": "辣味更直接"}, {"name": "小米辣", "note": "鲜辣,减量"}],
}


def _canonical_ingredients(text: str) -> list[str]:
    """从自然语言里识别出规范食材名(离线规则版)。"""
    found: list[str] = []
    for canon, syns in SYNONYMS.items():
        if any(s in text for s in syns):
            found.append(canon)
    return found


def suggest(ingredients_text: str, db) -> dict:
    """按食材重叠度给菜谱打分,返回推荐(离线规则版)。"""
    found = _canonical_ingredients(ingredients_text)
    have = set(found)

    scored = []
    for r in db.all_recipes():
        ings = [i for i in r["ingredients"] if i not in STAPLES]
        if not ings:
            continue
        present = [i for i in ings if i in have or any(s in ingredients_text for s in SYNONYMS.get(i, [i]))]
        missing = [i for i in ings if i not in present]
        ratio = len(present) / len(ings)
        scored.append({"recipe": r, "present": present, "missing": missing, "ratio": ratio})

    scored.sort(key=lambda x: (-x["ratio"], -len(x["present"])))
    top = [s for s in scored if s["ratio"] > 0][:5]

    dishes = []
    for s in top:
        if s["ratio"] >= 1.0:
            reason = f"食材齐全,可直接开做"
        else:
            reason = f"已有 {len(s['present'])}/{len(s['present'])+len(s['missing'])} 样主料,缺 {('、'.join(s['missing']) or '—')}"
        dishes.append({
            "name": s["recipe"]["name"],
            "match": "、".join(s["present"]) or "—",
            "missing": s["missing"],
            "reason": reason,
        })
    return {"ingredients": found, "dishes": dishes}


def cook(name: str, db) -> dict | None:
    """按菜名返回内置菜谱(离线规则版)。"""
    r = db.get_recipe(name)
    if r:
        return r
    for cand in db.all_recipes():
        if name in cand["name"] or cand["name"] in name:
            return cand
    return None


def swap(ingredient: str) -> dict:
    """返回替代品(离线规则版)。"""
    subs = SUBSTITUTES.get(ingredient)
    if not subs:
        # 尝试部分匹配
        for key, v in SUBSTITUTES.items():
            if ingredient in key or key in ingredient:
                subs = v
                break
    if not subs:
        subs = [{"name": "请在线询问模型", "note": "离线库未收录该食材的替代方案"}]
    return {"original": ingredient, "substitutes": subs}


def diet(dish: str, restrictions: str, db) -> dict:
    """基于菜谱标签/过敏原做忌口判断(离线规则版)。"""
    r = db.get_recipe(dish) or (cook(dish, db))
    reasons: list[str] = []
    adjustments: list[str] = []
    verdict = "适合"

    if not r:
        return {
            "dish": dish, "restrictions": restrictions,
            "verdict": "需注意", "reasons": ["离线库未收录该菜,建议在线询问模型"],
            "adjustments": [],
        }

    text = restrictions or ""
    allergens = r.get("allergens") or []
    allergen_map = {"鸡蛋": ["蛋"], "花生": ["花生", "坚果"], "虾皮": ["虾", "海鲜"]}
    for a in allergens:
        keys = allergen_map.get(a, [a])
        if any(k in text for k in keys):
            verdict = "不适合"
            reasons.append(f"含过敏原「{a}」")

    tags = r.get("tags") or []
    if any("辣" in t for t in tags) and ("辣" in text):
        verdict = max_verdict(verdict, "需注意")
        reasons.append("菜品偏辣")
        adjustments.append("去干辣椒/花椒,或改用甜椒增色")

    if "低脂" in text or "减脂" in text:
        verdict = max_verdict(verdict, "需注意")
        reasons.append("需控制油脂")
        adjustments.append("减少用油,改用蒸/焯/快炒")

    if not reasons:
        reasons.append("未检出明显冲突,可正常食用")
    return {"dish": dish, "restrictions": restrictions, "verdict": verdict, "reasons": reasons, "adjustments": adjustments}


_ORDER = {"适合": 0, "需注意": 1, "不适合": 2}


def max_verdict(a: str, b: str) -> str:
    return b if _ORDER[b] > _ORDER[a] else a
