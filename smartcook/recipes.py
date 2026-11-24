"""内置菜谱数据加载与初始化。"""

from __future__ import annotations

import json
import os

SEED_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "seed_recipes.json")


def load_seed_recipes() -> list[dict]:
    with open(SEED_PATH, encoding="utf-8") as f:
        return json.load(f)


def ensure_seeded(db) -> int:
    """首次运行时把内置菜谱写入数据库,返回写入条数。"""
    return db.seed_recipes(load_seed_recipes())
