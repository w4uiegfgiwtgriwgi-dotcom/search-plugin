import json
import os
import tempfile
import unittest
from pathlib import Path

from vmf_api.adapters import DouyinCliAdapter, XiaohongshuCliAdapter
from vmf_api.query import expand_query, normalize_url
from vmf_api.service import LocalApiService

class LocalApiServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = LocalApiService(":memory:")
    def tearDown(self):
        self.service.close()
    def test_search_task_collects_two_platforms(self):
        task = self.service.create_search_task("极端高温废墟旧空调", ["web-search", "bilibili"])
        self.assertEqual(task["status"], "completed")
        results = self.service.list_results(task["id"])
        self.assertEqual(len(results), 3)
        self.assertEqual({item["platform"] for item in results}, {"web-search", "bilibili"})
    def test_project_material_and_exports(self):
        task = self.service.create_search_task("旧空调", ["web-search", "bilibili"])
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
    def test_stage6_external_cli_adapters_parse_json_and_score(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            xhs_script = temp_path / "fake_xhs.py"
            dy_script = temp_path / "fake_dy.py"
            xhs_script.write_text(
                "import json\n"
                "print(json.dumps({'items':[{'title':'电动车轮胎被钉子扎孔现场补胎','url':'https://www.xiaohongshu.com/explore/abc','nickname':'修车师傅','desc':'电动车扎胎后发现钉子孔，现场补胎','tags':['电动车','扎胎','补胎']} ]}, ensure_ascii=False))\n",
                encoding="utf-8",
            )
            dy_script.write_text(
                "import json\n"
                "print(json.dumps({'data':[{'desc':'电动车被钉子扎了一个孔','aweme_id':'123456','author':{'nickname':'路边维修'}}]}, ensure_ascii=False))\n",
                encoding="utf-8",
            )
            old_xhs = os.environ.get("VMF_XHS_SEARCH_COMMAND")
            old_douyin = os.environ.get("VMF_DOUYIN_SEARCH_COMMAND")
            os.environ["VMF_XHS_SEARCH_COMMAND"] = f'"{os.sys.executable}" "{xhs_script}"'
            os.environ["VMF_DOUYIN_SEARCH_COMMAND"] = f'"{os.sys.executable}" "{dy_script}"'
            try:
                service = LocalApiService(":memory:", {
                    "xiaohongshu": XiaohongshuCliAdapter(),
                    "douyin": DouyinCliAdapter(),
                })
                task = service.create_search_task("电动车被钉子扎孔", ["xiaohongshu", "douyin"], 3)
                results = service.list_results(task["id"])
                service.close()
            finally:
                if old_xhs is None:
                    os.environ.pop("VMF_XHS_SEARCH_COMMAND", None)
                else:
                    os.environ["VMF_XHS_SEARCH_COMMAND"] = old_xhs
                if old_douyin is None:
                    os.environ.pop("VMF_DOUYIN_SEARCH_COMMAND", None)
                else:
                    os.environ["VMF_DOUYIN_SEARCH_COMMAND"] = old_douyin

        self.assertEqual(task["status"], "completed")
        self.assertEqual({item["platform"] for item in results}, {"xiaohongshu", "douyin"})
        self.assertTrue(all(item["raw_metadata_json"]["semantic_match_percent"] >= 0 for item in results))
        self.assertTrue(all(item["raw_metadata_json"]["semantic_match_reasons"] for item in results))
        self.assertTrue(any(item["raw_metadata_json"]["semantic_match_basis"] == "title+description+tags+public_metadata" for item in results))
        self.assertIn("https://www.douyin.com/video/123456", {item["source_url"] for item in results})
    def test_stage6_external_cli_errors_are_readable(self):
        xhs_error = XiaohongshuCliAdapter()._friendly_cli_error("not_authenticated: No 'a1' cookie found")
        douyin_error = DouyinCliAdapter()._friendly_cli_error("Network error: [WinError 10013] socket blocked")

        self.assertIn("需要先完成登录授权", xhs_error)
        self.assertIn("网络访问被系统或当前运行环境拦截", douyin_error)
    def test_stage6_session_status_checks_login_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            old_home = os.environ.get("VMF_SEARCH_CLI_HOME")
            os.environ["VMF_SEARCH_CLI_HOME"] = temp_dir
            try:
                xhs = XiaohongshuCliAdapter()
                douyin = DouyinCliAdapter()
                self.assertEqual(xhs.check_session()["status"], "needs_login")
                self.assertEqual(douyin.check_session()["status"], "needs_login")

                xhs_cookie = Path(temp_dir) / ".xiaohongshu-cli" / "cookies.json"
                dy_cookie = Path(temp_dir) / ".dy" / "cookies" / "default.json"
                xhs_cookie.parent.mkdir(parents=True)
                dy_cookie.parent.mkdir(parents=True)
                xhs_cookie.write_text('{"a1":"test"}', encoding="utf-8")
                dy_cookie.write_text('{"sessionid":"test"}', encoding="utf-8")

                self.assertEqual(xhs.check_session()["status"], "available")
                self.assertEqual(douyin.check_session()["status"], "available")
            finally:
                if old_home is None:
                    os.environ.pop("VMF_SEARCH_CLI_HOME", None)
                else:
                    os.environ["VMF_SEARCH_CLI_HOME"] = old_home
    def test_query_helpers(self):
        self.assertIn("air conditioner", expand_query("旧空调"))
        self.assertEqual(normalize_url("HTTPS://Example.COM/a?utm_source=x&id=1#top"), "https://example.com/a?id=1")

if __name__ == "__main__":
    unittest.main()
