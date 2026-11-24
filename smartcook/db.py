"""SQLite 持久层:菜谱库 + 家庭食材库存。纯标准库 sqlite3。

线程安全:Web 服务用 ThreadingHTTPServer,每请求一个线程,
故用 check_same_thread=False + 一把锁串行化对同一连接的访问。
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "smartcook.db")


class Database:
    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("SMARTCOOK_DB") or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    ingredients TEXT NOT NULL,   -- JSON list
                    steps TEXT NOT NULL,          -- JSON list
                    tips TEXT NOT NULL,           -- JSON list
                    tags TEXT NOT NULL,           -- JSON list
                    allergens TEXT NOT NULL,      -- JSON list
                    time_minutes INTEGER,
                    difficulty TEXT,
                    servings TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    qty TEXT,
                    added_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            self.conn.commit()

    # ---------- 菜谱 ----------
    def seed_recipes(self, recipes: list[dict]) -> int:
        """批量写入内置菜谱(幂等,按 name 去重)。"""
        n = 0
        with self._lock:
            for r in recipes:
                try:
                    self.conn.execute(
                        "INSERT INTO recipes (name, ingredients, steps, tips, tags, allergens, time_minutes, difficulty, servings) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (
                            r["name"],
                            json.dumps(r.get("ingredients", []), ensure_ascii=False),
                            json.dumps(r.get("steps", []), ensure_ascii=False),
                            json.dumps(r.get("tips", []), ensure_ascii=False),
                            json.dumps(r.get("tags", []), ensure_ascii=False),
                            json.dumps(r.get("allergens", []), ensure_ascii=False),
                            r.get("time_minutes"),
                            r.get("difficulty"),
                            r.get("servings"),
                        ),
                    )
                    n += 1
                except sqlite3.IntegrityError:
                    pass
            self.conn.commit()
        return n

    def all_recipes(self) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM recipes ORDER BY id").fetchall()
        return [self._row_to_recipe(r) for r in rows]

    def get_recipe(self, name: str) -> dict | None:
        with self._lock:
            row = self.conn.execute("SELECT * FROM recipes WHERE name = ?", (name,)).fetchone()
        return self._row_to_recipe(row) if row else None

    def search_recipes(self, keyword: str) -> list[dict]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM recipes WHERE name LIKE ? OR ingredients LIKE ? ORDER BY id",
                (f"%{keyword}%", f"%{keyword}%"),
            ).fetchall()
        return [self._row_to_recipe(r) for r in rows]

    @staticmethod
    def _row_to_recipe(row) -> dict:
        return {
            "name": row["name"],
            "ingredients": json.loads(row["ingredients"]),
            "steps": json.loads(row["steps"]),
            "tips": json.loads(row["tips"]),
            "tags": json.loads(row["tags"]),
            "allergens": json.loads(row["allergens"]),
            "time_minutes": row["time_minutes"],
            "difficulty": row["difficulty"],
            "servings": row["servings"],
        }

    def recipe_catalog(self) -> str:
        """把菜谱库压成一段给模型的紧凑目录(name + 食材)。"""
        lines = []
        for r in self.all_recipes():
            lines.append(f"{r['name']}:{'、'.join(r['ingredients'])}")
        return "\n".join(lines)

    # ---------- 库存 ----------
    def add_item(self, name: str, qty: str | None):
        with self._lock:
            self.conn.execute(
                "INSERT INTO inventory (name, qty) VALUES (?,?) "
                "ON CONFLICT(name) DO UPDATE SET qty=excluded.qty",
                (name, qty or ""),
            )
            self.conn.commit()

    def remove_item(self, name: str) -> bool:
        with self._lock:
            cur = self.conn.execute("DELETE FROM inventory WHERE name = ?", (name,))
            self.conn.commit()
            return cur.rowcount > 0

    def list_items(self) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM inventory ORDER BY added_at").fetchall()
        return [dict(r) for r in rows]

    def clear_items(self):
        with self._lock:
            self.conn.execute("DELETE FROM inventory")
            self.conn.commit()

    def close(self):
        self.conn.close()
