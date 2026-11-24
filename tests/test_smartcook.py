"""离线路径的单元测试(不依赖网络 / API key)。运行:python -m unittest discover tests"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartcook import agent, db as dbmod, llm, mock, recipes  # noqa: E402


class TestLLM(unittest.TestCase):
    def test_extract_json_fenced(self):
        self.assertEqual(llm.extract_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_extract_json_with_prefix(self):
        self.assertEqual(llm.extract_json('好的,结果如下:{"a": 1}'), {"a": 1})

    def test_extract_json_list(self):
        self.assertEqual(llm.extract_json('[1, 2, 3]'), [1, 2, 3])

    def test_extract_json_empty_raises(self):
        with self.assertRaises(llm.LLMError):
            llm.extract_json("")


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = dbmod.Database(os.path.join(self.tmp, "t.db"))
        recipes.ensure_seeded(self.db)

    def tearDown(self):
        self.db.close()

    def test_seed_and_fetch(self):
        allr = self.db.all_recipes()
        self.assertGreaterEqual(len(allr), 20)
        r = self.db.get_recipe("番茄炒蛋")
        self.assertIsNotNone(r)
        self.assertIn("番茄", r["ingredients"])
        self.assertTrue(r["steps"])

    def test_inventory(self):
        self.db.add_item("番茄", "2个")
        self.db.add_item("番茄", "3个")  # upsert
        items = self.db.list_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["qty"], "3个")
        self.assertTrue(self.db.remove_item("番茄"))
        self.assertEqual(len(self.db.list_items()), 0)

    def test_search(self):
        self.assertTrue(any(r["name"] == "番茄炒蛋" for r in self.db.search_recipes("番茄")))


class TestMockAgent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = dbmod.Database(os.path.join(self.tmp, "t.db"))
        recipes.ensure_seeded(self.db)

    def tearDown(self):
        self.db.close()

    def test_suggest_offline(self):
        r = mock.suggest("家里有番茄、鸡蛋、青椒", self.db)
        self.assertIn("番茄", r["ingredients"])
        self.assertIn("鸡蛋", r["ingredients"])
        self.assertTrue(r["dishes"])
        names = [d["name"] for d in r["dishes"]]
        self.assertIn("番茄炒蛋", names)

    def test_cook_offline(self):
        r = mock.cook("番茄炒蛋", self.db)
        self.assertIsNotNone(r)
        self.assertTrue(r["steps"])

    def test_swap_offline(self):
        r = mock.swap("香醋")
        self.assertEqual(r["original"], "香醋")
        self.assertTrue(r["substitutes"])

    def test_diet_offline(self):
        r = mock.diet("宫保鸡丁", "花生过敏", self.db)
        self.assertEqual(r["verdict"], "不适合")

    def test_agent_falls_back_to_mock_without_key(self):
        r = agent.suggest("番茄 鸡蛋", config={"api_key": ""}, db=self.db)
        self.assertTrue(r["dishes"])


if __name__ == "__main__":
    unittest.main()
