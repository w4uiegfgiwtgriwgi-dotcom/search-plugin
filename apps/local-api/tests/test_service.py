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
        target_project = self.service.create_project("手动选择项目")
        collected = self.service.collect_browser_page(
            "https://example.com/video",
            "浏览器页面标题",
            project_id=target_project["id"],
            project_name="扩展采集项目",
            author_name="页面作者",
            description="页面公开描述",
            cover_url="https://example.com/cover.jpg",
            published_at="2026-08-10T12:00:00+08:00",
            site_name="示例站点",
        )
        library = self.service.list_project_library(collected["project"]["id"], keyword="浏览器采集")

        self.assertEqual(collected["project"]["name"], "手动选择项目")
        self.assertEqual(collected["result"]["platform"], "browser-extension")
        self.assertEqual(collected["result"]["author_name"], "页面作者")
        self.assertEqual(collected["result"]["cover_url"], "https://example.com/cover.jpg")
        self.assertEqual(collected["result"]["published_at"], "2026-08-10T12:00:00+08:00")
        self.assertEqual(collected["result"]["raw_metadata_json"]["site_name"], "示例站点")
        self.assertEqual(collected["material"]["tags_json"], ["浏览器采集"])
        self.assertEqual(library["total_count"], 1)
        self.assertEqual(library["items"][0]["title"], "浏览器页面标题")
        self.assertEqual(library["items"][0]["collection_source_label"], "浏览器采集")
        self.assertEqual(library["items"][0]["site_name"], "示例站点")
        self.assertEqual(len(self.service.list_projects()), 1)
        with self.assertRaises(ValueError):
            self.service.collect_browser_page("chrome://settings", "设置页")
    def test_wechat_channel_search_plan_is_manual_and_safe(self):
        plan = self.service.build_wechat_channel_search_plan(
            "极端高温废墟里男人翻垃圾，最后发现旧空调",
            ["男人翻垃圾", "旧空调"],
        )

        self.assertEqual(plan["platform"], "wechat-channel")
        self.assertEqual(plan["mode"], "semi_auto")
        self.assertIn("极端高温废墟里男人翻垃圾，最后发现旧空调", plan["search_terms"])
        self.assertIn("男人翻垃圾 原视频", plan["search_terms"])
        self.assertIn("打开微信", plan["manual_steps"][0])
        self.assertTrue(any("不读取或保存微信密码" in item for item in plan["safety_boundaries"]))
        self.assertIn("微信视频号", plan["copy_blocks"]["web_assist_search"])

        with self.assertRaises(ValueError):
            self.service.build_wechat_channel_search_plan("")
    def test_query_helpers(self):
        self.assertIn("air conditioner", expand_query("旧空调"))
        self.assertEqual(normalize_url("HTTPS://Example.COM/a?utm_source=x&id=1#top"), "https://example.com/a?id=1")

if __name__ == "__main__":
    unittest.main()
