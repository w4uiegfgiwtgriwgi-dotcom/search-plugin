import json
import unittest
from vmf_api.query import expand_query, normalize_url
from vmf_api.service import LocalApiService

class LocalApiServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = LocalApiService(":memory:")
    def tearDown(self):
        self.service.close()
    def test_search_task_collects_two_platforms(self):
        task = self.service.create_search_task("极端高温废墟旧空调")
        self.assertEqual(task["status"], "completed")
        results = self.service.list_results(task["id"])
        self.assertEqual(len(results), 3)
        self.assertEqual({item["platform"] for item in results}, {"web-search", "bilibili"})
    def test_project_material_and_exports(self):
        task = self.service.create_search_task("旧空调")
        result = self.service.list_results(task["id"])[0]
        project = self.service.create_project("测试项目")
        material = self.service.add_material(project["id"], result["id"], ["空调"], "可复查")
        self.assertEqual(material["tags_json"], ["空调"])
        self.assertIn("搜索结果导出", self.service.export_results(task["id"], "md"))
        self.assertIn("source_url", self.service.export_results(task["id"], "csv"))
        self.assertGreater(len(json.loads(self.service.export_results(task["id"], "json"))), 0)
    def test_browser_page_collects_into_project_library(self):
        collected = self.service.collect_browser_page(
            "https://example.com/video",
            "浏览器页面标题",
            project_name="扩展采集项目",
            author_name="页面作者",
            description="页面公开描述",
        )
        library = self.service.list_project_library(collected["project"]["id"], keyword="浏览器采集")

        self.assertEqual(collected["project"]["name"], "扩展采集项目")
        self.assertEqual(collected["result"]["platform"], "browser-extension")
        self.assertEqual(collected["result"]["author_name"], "页面作者")
        self.assertEqual(collected["material"]["tags_json"], ["浏览器采集"])
        self.assertEqual(library["total_count"], 1)
        self.assertEqual(library["items"][0]["title"], "浏览器页面标题")
        with self.assertRaises(ValueError):
            self.service.collect_browser_page("chrome://settings", "设置页")
    def test_query_helpers(self):
        self.assertIn("air conditioner", expand_query("旧空调"))
        self.assertEqual(normalize_url("HTTPS://Example.COM/a?utm_source=x&id=1#top"), "https://example.com/a?id=1")

if __name__ == "__main__":
    unittest.main()
