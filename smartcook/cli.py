"""命令行入口:python -m smartcook <命令> [选项]。"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, agent, db as dbmod, llm, recipes
from .llm import LLMError

MOCK_BANNER = (
    "⚠️  当前为离线演示模式(未配置 LLM_API_KEY),结果由内置规则生成。\n"
    "   在 .env 填入 LLM_API_KEY 后,理解/识别/生成/判断将由大模型完成。\n"
)


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------
def _ing(i) -> str:
    if isinstance(i, dict):
        name, amt = i.get("name", ""), i.get("amount", "")
        return f"{name} {amt}".strip() if amt else str(name)
    return str(i)


def render_suggest(r: dict) -> str:
    lines = ["🧺 识别到的食材:" + ("、".join(r.get("ingredients", [])) or "—"), ""]
    dishes = r.get("dishes", [])
    if not dishes:
        lines.append("没有匹配到合适的菜,试试换些食材。")
        return "\n".join(lines)
    lines.append(f"🍳 推荐菜谱 ({len(dishes)}):")
    for idx, d in enumerate(dishes, 1):
        missing = "、".join(d.get("missing", [])) or "—"
        lines.append(f"  {idx}. {d.get('name','')}   [已有:{d.get('match','?')}] 缺:{missing}")
        if d.get("reason"):
            lines.append(f"     {d['reason']}")
    return "\n".join(lines)


def render_cook(r: dict) -> str:
    meta = []
    if r.get("time_minutes"):
        meta.append(f"⏱ {r['time_minutes']} 分钟")
    if r.get("difficulty"):
        meta.append(f"难度:{r['difficulty']}")
    if r.get("servings"):
        meta.append(f"份量:{r['servings']}")
    lines = [f"🍽  {r.get('name','')}" + ("  " + " · ".join(meta) if meta else ""), ""]
    if r.get("ingredients"):
        lines.append("【食材】")
        lines += [f"  · {_ing(i)}" for i in r["ingredients"]]
        lines.append("")
    if r.get("steps"):
        lines.append("【做法】")
        for idx, s in enumerate(r["steps"], 1):
            lines.append(f"  {idx}. {s}")
        lines.append("")
    if r.get("tips"):
        lines.append("【贴士】")
        lines += [f"  · {t}" for t in r["tips"]]
    return "\n".join(lines)


def render_swap(r: dict) -> str:
    lines = [f"🔄 「{r.get('original','')}」的替代方案:"]
    for idx, s in enumerate(r.get("substitutes", []), 1):
        note = f" —— {s['note']}" if s.get("note") else ""
        lines.append(f"  {idx}. {s['name']}{note}")
    return "\n".join(lines)


def render_diet(r: dict) -> str:
    lines = [f"🥗 {r.get('dish','')}  ·  忌口:{r.get('restrictions','')}"]
    lines.append(f"结论:{r.get('verdict','需注意')}")
    if r.get("reasons"):
        lines.append("原因:")
        lines += [f"  · {x}" for x in r["reasons"]]
    if r.get("adjustments"):
        lines.append("建议:")
        lines += [f"  · {x}" for x in r["adjustments"]]
    return "\n".join(lines)


def render_inventory(items: list[dict]) -> str:
    if not items:
        return "冰箱空空的,用 `smartcook inventory add <食材> [--qty 数量]` 添加吧。"
    lines = ["🧊 家中食材:"]
    for it in items:
        qty = f"  x{it['qty']}" if it.get("qty") else ""
        lines.append(f"  · {it['name']}{qty}")
    return "\n".join(lines)


def render_recipes(rs: list[dict]) -> str:
    lines = [f"📖 菜谱库共 {len(rs)} 道:"]
    for r in rs:
        tags = " ".join("#" + t for t in r.get("tags", []))
        lines.append(f"  · {r['name']}  ({r.get('time_minutes','?')}分钟 / {r.get('difficulty','?')})  {tags}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------
def _get_db(args) -> dbmod.Database:
    d = dbmod.Database(args.db if getattr(args, "db", None) else None)
    recipes.ensure_seeded(d)
    return d


def cmd_suggest(args):
    db = _get_db(args)
    cfg = llm.config_from_args(args)
    text = " ".join(args.ingredients)
    r = agent.suggest(text, config=cfg, db=db, force_mock=args.mock)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render_suggest(r))


def cmd_cook(args):
    db = _get_db(args)
    cfg = llm.config_from_args(args)
    r = agent.cook(args.name, config=cfg, db=db, diet=args.diet, on_hand=args.on_hand, force_mock=args.mock)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render_cook(r))


def cmd_swap(args):
    cfg = llm.config_from_args(args)
    r = agent.swap(args.ingredient, config=cfg, force_mock=args.mock)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render_swap(r))


def cmd_diet(args):
    db = _get_db(args)
    cfg = llm.config_from_args(args)
    r = agent.diet(args.dish, args.restrictions, config=cfg, db=db, force_mock=args.mock)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render_diet(r))


def cmd_inventory(args):
    db = _get_db(args)
    if args.action == "add":
        db.add_item(args.name, args.qty)
        print(f"✅ 已加入: {args.name}" + (f" x{args.qty}" if args.qty else ""))
    elif args.action == "remove":
        ok = db.remove_item(args.name)
        print(f"✅ 已移除: {args.name}" if ok else f"❌ 未找到: {args.name}")
    elif args.action == "clear":
        db.clear_items()
        print("✅ 库存已清空")
    else:  # list
        print(render_inventory(db.list_items()))


def cmd_recipes(args):
    db = _get_db(args)
    if args.show:
        r = db.get_recipe(args.show)
        if not r:
            print(f"❌ 未找到菜谱: {args.show}")
            return
        print(render_cook(r))
    else:
        print(render_recipes(db.all_recipes()))


def cmd_web(args):
    from . import web
    web.serve(host=args.host, port=args.port, db_path=args.db if getattr(args, "db", None) else None,
              force_mock=args.mock)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="smartcook",
        description="食光 · 智能菜谱 Agent:输入食材,让大模型帮你决定做什么、怎么做。",
    )
    p.add_argument("--version", action="version", version=f"smartcook {__version__}")
    p.add_argument("--mock", action="store_true", help="强制离线演示模式(不调用模型)")
    p.add_argument("--json", action="store_true", help="以 JSON 输出原始结果")
    p.add_argument("--model", help="覆盖 LLM_MODEL")
    p.add_argument("--base-url", help="覆盖 LLM_BASE_URL")
    p.add_argument("--api-key", help="覆盖 LLM_API_KEY")
    p.add_argument("--db", help="SQLite 数据库路径")

    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("suggest", help="根据手边食材推荐能做的菜")
    sp.add_argument("ingredients", nargs="+", help="食材描述,如:番茄 鸡蛋 青椒")
    sp.set_defaults(func=cmd_suggest)

    cp = sub.add_parser("cook", help="生成某道菜的完整做法")
    cp.add_argument("name", help="菜名")
    cp.add_argument("--diet", help="忌口/要求,如:不吃辣")
    cp.add_argument("--on-hand", help="手边已有食材,用于个性化")
    cp.set_defaults(func=cmd_cook)

    wp = sub.add_parser("swap", help="查询缺失食材的替代品")
    wp.add_argument("ingredient", help="缺失的食材")
    wp.set_defaults(func=cmd_swap)

    dp = sub.add_parser("diet", help="判断某道菜是否适合某忌口")
    dp.add_argument("dish", help="菜名")
    dp.add_argument("--restrictions", required=True, help="忌口/要求,如:花生过敏、不吃辣")
    dp.set_defaults(func=cmd_diet)

    ip = sub.add_parser("inventory", help="管理家中食材库存")
    ip.add_argument("action", choices=["add", "remove", "list", "clear"])
    ip.add_argument("name", nargs="?", help="食材名(add/remove 用)")
    ip.add_argument("--qty", help="数量(add 用)")
    ip.set_defaults(func=cmd_inventory)

    rp = sub.add_parser("recipes", help="查看内置菜谱库")
    rp.add_argument("show", nargs="?", help="菜名(查看单道做法)")
    rp.set_defaults(func=cmd_recipes)

    webp = sub.add_parser("web", help="启动 Web 界面")
    webp.add_argument("--host", default="127.0.0.1")
    webp.add_argument("--port", type=int, default=8000)
    webp.set_defaults(func=cmd_web)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    # 未配置 key 且未显式 --mock 时,提示进入离线演示模式
    if not args.mock and args.command not in ("inventory", "recipes"):
        if not llm.config_from_args(args).get("api_key"):
            print(MOCK_BANNER, file=sys.stderr)

    try:
        args.func(args)
    except LLMError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
