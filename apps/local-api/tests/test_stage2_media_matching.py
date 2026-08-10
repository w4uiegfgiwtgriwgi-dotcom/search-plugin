import subprocess
import unittest
from pathlib import Path

from vmf_api.service import LocalApiService


FIXTURE_DIR = Path("tests/fixtures/stage2")
ROBUSTNESS_THRESHOLD = 0.45


def run_ffmpeg(args):
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def run_ffmpeg_optional(args):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=False, capture_output=True, text=True)


class Stage2MediaMatchingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        cls.video_path = FIXTURE_DIR / "stage2-self-made-testsrc.mp4"
        cls.decoy_video_path = FIXTURE_DIR / "stage2-decoy-solid.mp4"
        cls.query_frame_path = FIXTURE_DIR / "stage2-air-query.png"
        run_ffmpeg([
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=4:duration=3",
            str(cls.video_path),
        ])
        run_ffmpeg([
            "-f",
            "lavfi",
            "-i",
            "color=c=black:size=160x90:rate=4:duration=3",
            str(cls.decoy_video_path),
        ])
        run_ffmpeg([
            "-ss",
            "1.25",
            "-i",
            str(cls.video_path),
            "-frames:v",
            "1",
            str(cls.query_frame_path),
        ])
        cls.variant_paths = cls._build_variant_images(cls.query_frame_path)

    @classmethod
    def _build_variant_images(cls, source_path):
        variants = {
            "compressed": FIXTURE_DIR / "stage2-air-query-compressed.jpg",
            "scaled": FIXTURE_DIR / "stage2-air-query-scaled.png",
            "tone": FIXTURE_DIR / "stage2-air-query-tone.png",
            "text": FIXTURE_DIR / "stage2-air-query-text.png",
            "occlusion": FIXTURE_DIR / "stage2-air-query-occlusion.png",
        }
        run_ffmpeg(["-i", str(source_path), "-q:v", "8", str(variants["compressed"])])
        run_ffmpeg(["-i", str(source_path), "-vf", "scale=96:54", str(variants["scaled"])])
        run_ffmpeg(["-i", str(source_path), "-vf", "eq=brightness=0.08:saturation=0.8", str(variants["tone"])])
        text_result = run_ffmpeg_optional([
            "-i",
            str(source_path),
            "-vf",
            "drawtext=text='MOCK':x=8:y=h-24:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.55",
            str(variants["text"]),
        ])
        if text_result.returncode != 0:
            run_ffmpeg(["-i", str(source_path), "-vf", "drawbox=x=6:y=h-24:w=70:h=18:color=black@0.85:t=fill", str(variants["text"])])
        run_ffmpeg(["-i", str(source_path), "-vf", "drawbox=x=18:y=18:w=48:h=28:color=black@0.9:t=fill", str(variants["occlusion"])])
        return variants

    def setUp(self):
        self.service = LocalApiService(":memory:")

    def tearDown(self):
        self.service.close()

    def test_analyze_image_and_find_frame_match(self):
        asset = self.service.analyze_image(FIXTURE_DIR / "stage2-air-query.png")
        self.assertEqual(asset["kind"], "query_image")
        self.assertTrue(asset["perceptual_hash"])
        self.assertEqual(len(asset["embedding_json"]), 16)
        self.assertTrue(Path(asset["thumbnail_path"]).exists())

        match = self.service.find_frame_match(asset["id"], FIXTURE_DIR / "stage2-self-made-testsrc.mp4", fps=1.0, threshold=0.75)
        self.assertIn(match["match_type"], {"same_frame", "visually_similar"})
        self.assertGreaterEqual(match["combined_score"], 0.75)
        self.assertLessEqual(abs(match["timestamp_ms"] - 1250), 250)
        self.assertTrue(Path(match["local_frame_path"]).exists())
        self.assertEqual(match["evidence_json"]["frame_count"], 3)
        self.assertGreater(match["evidence_json"]["refined_frame_count"], 0)

    def test_uploaded_image_is_saved_and_analyzed(self):
        payload = self.query_frame_path.read_bytes()
        asset = self.service.analyze_uploaded_image("../../unsafe-name.png", payload)

        saved_path = Path(asset["source_path"])
        self.assertTrue(saved_path.exists())
        self.assertIn(".local-data", saved_path.parts)
        self.assertTrue(saved_path.name.startswith("unsafe-name-"))
        self.assertEqual(asset["kind"], "query_image")
        self.assertEqual(asset["size_bytes"], len(payload))

    def test_batch_uploaded_images_keep_successes_and_errors(self):
        payload = self.query_frame_path.read_bytes()
        batch = self.service.analyze_uploaded_images([
            ("first.png", payload),
            ("second.png", payload),
            ("bad.png", b"not a real image"),
        ])

        self.assertEqual(batch["upload_count"], 3)
        self.assertEqual(batch["asset_count"], 2)
        self.assertEqual(batch["error_count"], 1)
        self.assertEqual(len(batch["assets"]), 2)
        self.assertIn("bad.png", batch["errors"][0]["filename"])

    def test_uploaded_image_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            self.service.analyze_uploaded_image("empty.png", b"")
        with self.assertRaises(ValueError):
            self.service.analyze_uploaded_image("not-image.txt", b"hello")
        with self.assertRaises(ValueError):
            self.service.analyze_uploaded_image("fake.png", b"not a real image")

    def test_mock_matching_survives_common_image_variants(self):
        for name, variant_path in self.variant_paths.items():
            with self.subTest(variant=name):
                asset = self.service.analyze_image(variant_path)
                match = self.service.find_frame_match(asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)

                self.assertIn(match["match_type"], {"same_frame", "visually_similar"})
                self.assertGreaterEqual(match["combined_score"], ROBUSTNESS_THRESHOLD)
                self.assertTrue(Path(match["local_frame_path"]).exists())

    def test_batch_matching_sorts_matches_and_keeps_errors(self):
        asset = self.service.analyze_image(self.query_frame_path)
        batch = self.service.find_batch_frame_matches(
            asset["id"],
            [str(self.decoy_video_path), str(self.video_path), str(FIXTURE_DIR / "missing.mp4")],
            fps=1.0,
            threshold=ROBUSTNESS_THRESHOLD,
            refine_fps=4.0,
            top_k=5,
        )

        self.assertEqual(batch["candidate_count"], 3)
        self.assertEqual(batch["match_count"], 2)
        self.assertEqual(batch["error_count"], 1)
        self.assertEqual(Path(batch["matches"][0]["candidate_video_path"]), self.video_path.resolve())
        self.assertGreaterEqual(batch["matches"][0]["combined_score"], batch["matches"][1]["combined_score"])
        self.assertIn("missing.mp4", batch["errors"][0]["candidate_video_path"])

    def test_multi_asset_matching_runs_each_query_against_candidates(self):
        first = self.service.analyze_image(self.query_frame_path)
        second = self.service.analyze_image(self.variant_paths["tone"])
        result = self.service.find_multi_asset_frame_matches(
            [first["id"], second["id"]],
            [str(self.video_path), str(self.decoy_video_path)],
            fps=1.0,
            threshold=ROBUSTNESS_THRESHOLD,
            refine_fps=4.0,
            top_k=5,
        )

        self.assertEqual(result["asset_count"], 2)
        self.assertEqual(result["batch_count"], 2)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(len(result["batches"]), 2)
        self.assertEqual({batch["query_asset_id"] for batch in result["batches"]}, {first["id"], second["id"]})
        self.assertGreaterEqual(len(result["best_matches"]), 2)

    def test_save_high_score_matches_to_project_without_duplicates(self):
        project = self.service.create_project("批量收藏项目")
        first = self.service.analyze_image(self.query_frame_path)
        second = self.service.analyze_image(self.variant_paths["tone"])
        result = self.service.find_multi_asset_frame_matches(
            [first["id"], second["id"]],
            [str(self.video_path), str(self.decoy_video_path)],
            fps=1.0,
            threshold=ROBUSTNESS_THRESHOLD,
            refine_fps=4.0,
            top_k=5,
        )
        match_ids = [match["id"] for match in result["best_matches"]]

        saved = self.service.add_frame_match_materials(
            project["id"],
            match_ids,
            min_score=ROBUSTNESS_THRESHOLD,
            tags=["批量收藏"],
            note="高分匹配",
        )
        duplicate = self.service.add_frame_match_materials(project["id"], match_ids, min_score=ROBUSTNESS_THRESHOLD)
        too_high = self.service.add_frame_match_materials(project["id"], match_ids, min_score=1.1)

        self.assertGreaterEqual(saved["saved_count"], 2)
        self.assertEqual(duplicate["saved_count"], 0)
        self.assertEqual(duplicate["skipped_count"], len(match_ids))
        self.assertEqual(too_high["saved_count"], 0)
        self.assertEqual(len(self.service.list_frame_match_materials(project["id"])), saved["saved_count"])

    def test_save_frame_match_material_to_project(self):
        project = self.service.create_project("截图反查项目")
        asset = self.service.analyze_image(self.query_frame_path)
        match = self.service.find_frame_match(asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)

        material = self.service.add_frame_match_material(
            project["id"],
            match["id"],
            tags=["阶段2", "截图反查"],
            note="人工确认可用",
            review_status="confirmed",
        )
        saved = self.service.list_frame_match_materials(project["id"])

        self.assertEqual(material["project_id"], project["id"])
        self.assertEqual(material["match_id"], match["id"])
        self.assertEqual(material["selected_timestamp_ms"], match["timestamp_ms"])
        self.assertEqual(material["review_status"], "confirmed")
        self.assertEqual(material["tags_json"], ["阶段2", "截图反查"])
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["candidate_video_path"], str(self.video_path.resolve()))

        with self.assertRaises(ValueError):
            self.service.add_frame_match_material(project["id"], match["id"], review_status="maybe")

    def test_project_library_combines_search_and_frame_materials(self):
        project = self.service.create_project("统一素材项目")
        task = self.service.create_search_task("旧空调")
        result = self.service.list_results(task["id"])[0]
        search_material = self.service.add_material(project["id"], result["id"], tags=["文字搜索"], note="阶段1素材")
        self.service.update_material_rights_status(project["id"], "search_result", search_material["id"], "needs_permission")

        asset = self.service.analyze_image(self.query_frame_path)
        match = self.service.find_frame_match(asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)
        self.service.add_frame_match_material(project["id"], match["id"], tags=["截图反查"], note="阶段2素材")

        library = self.service.list_project_library(project["id"])
        source_types = {item["source_type"] for item in library["items"]}

        self.assertEqual(library["total_count"], 2)
        self.assertEqual(library["search_result_count"], 1)
        self.assertEqual(library["frame_match_count"], 1)
        self.assertEqual(source_types, {"search_result", "frame_match"})
        self.assertEqual(library["summary"]["all_count"], 2)
        self.assertEqual(library["summary"]["filtered_count"], 2)
        self.assertEqual(library["summary"]["by_source_type"]["search_result"], 1)
        self.assertEqual(library["summary"]["by_source_type"]["frame_match"], 1)
        self.assertEqual(sum(library["summary"]["by_match_confidence"].values()), 1)
        self.assertEqual(library["summary"]["by_usage_status"]["needs_permission"], 1)
        self.assertEqual(library["summary"]["by_usage_status"]["rights_unknown"], 1)
        self.assertEqual(library["filters"]["source_type"], "all")
        self.assertIn("来源=全部", library["filter_summary"])
        self.assertEqual(len(library["timeline"]), 1)
        self.assertEqual(library["timeline"][0]["title"], Path(self.video_path).name)
        self.assertEqual(library["action_items"]["counts"]["pending_review"], 1)
        self.assertEqual(library["action_items"]["counts"]["rights_attention"], 1)
        self.assertEqual(library["action_items"]["filters"]["pending_review"]["action_filter"], "pending_review")
        self.assertEqual(library["action_items"]["pending_review"][0]["source_type"], "search_result")
        self.assertEqual(library["action_items"]["pending_review"][0]["action_label"], "待复核")
        self.assertIn("打开来源", library["action_items"]["pending_review"][0]["suggested_next_step"])
        self.assertEqual(library["action_items"]["rights_attention"][0]["priority"], "high")

        frame_only = self.service.list_project_library(project["id"], source_type="frame_match")
        pending_only = self.service.list_project_library(project["id"], action_filter="pending_review")
        rights_attention = self.service.list_project_library(project["id"], action_filter="rights_attention")
        score_sorted = self.service.list_project_library(project["id"], sort_by="score_desc")
        csv_export = self.service.export_project_library(project["id"], "csv")
        md_export = self.service.export_project_library(project["id"], "md", source_type="frame_match")
        json_export = self.service.export_project_library(project["id"], "json")
        action_json_export = self.service.export_project_library(project["id"], "json", action_filter="rights_attention")

        self.assertEqual(frame_only["total_count"], 1)
        self.assertEqual(pending_only["total_count"], 1)
        self.assertEqual(pending_only["filters"]["action_filter"], "pending_review")
        self.assertIn("待处理=待复核", pending_only["filter_summary"])
        self.assertEqual(rights_attention["total_count"], 1)
        self.assertEqual(rights_attention["items"][0]["rights_status"], "needs_permission")
        self.assertEqual(frame_only["items"][0]["source_type"], "frame_match")
        self.assertEqual(frame_only["items"][0]["source_type_label"], "截图反查")
        self.assertEqual(frame_only["items"][0]["review_status_label"], "已确认")
        self.assertEqual(frame_only["items"][0]["rights_status_label"], "未知")
        self.assertEqual(frame_only["items"][0]["usage_status"], "rights_unknown")
        self.assertEqual(frame_only["items"][0]["usage_status_label"], "版权待确认")
        self.assertRegex(frame_only["items"][0]["timecode"], r"^\d{2}:\d{2}:\d{2}\.\d{3}$")
        self.assertRegex(frame_only["items"][0]["selected_timecode"], r"^\d{2}:\d{2}:\d{2}\.\d{3}$")
        self.assertGreater(frame_only["items"][0]["duration_ms"], 0)
        self.assertRegex(frame_only["items"][0]["duration_timecode"], r"^\d{2}:\d{2}:\d{2}\.\d{3}$")
        self.assertGreaterEqual(frame_only["items"][0]["phash_score"], 0)
        self.assertGreaterEqual(frame_only["items"][0]["visual_score"], 0)
        self.assertIn(frame_only["items"][0]["match_confidence"], {"high", "medium", "low"})
        self.assertIn(frame_only["items"][0]["match_confidence_label"], {"高可信", "中可信", "低可信"})
        self.assertIn("粗扫", frame_only["items"][0]["evidence_summary"])
        self.assertIn("frame_count", frame_only["items"][0]["evidence"])
        self.assertEqual(frame_only["summary"]["all_count"], 2)
        self.assertEqual(frame_only["summary"]["filtered_count"], 1)
        self.assertEqual(score_sorted["items"][0]["source_type"], "frame_match")
        self.assertIn("source_type", csv_export)
        self.assertIn("source_type_label", csv_export)
        self.assertIn("review_status_label", csv_export)
        self.assertIn("rights_status_label", csv_export)
        self.assertIn("usage_status_label", csv_export)
        self.assertIn("duration_timecode", csv_export)
        self.assertIn("phash_score", csv_export)
        self.assertIn("match_confidence", csv_export)
        self.assertIn("截图反查", md_export)
        self.assertIn("导出概览", md_export)
        self.assertIn("导出条件", md_export)
        self.assertIn("当前导出：1 条", md_export)
        self.assertIn("截图反查时间线", md_export)
        self.assertLess(md_export.index("截图反查时间线"), md_export.index("素材列表"))
        self.assertIn("待处理清单", self.service.export_project_library(project["id"], "md"))
        self.assertIn("建议：", self.service.export_project_library(project["id"], "md"))
        self.assertIn("已确认", md_export)
        self.assertIn("未知", md_export)
        self.assertIn("可用状态", md_export)
        self.assertIn("时间码", md_export)
        self.assertIn("可信度", md_export)
        self.assertIn("证据", md_export)
        self.assertIn('"duration_ms"', json_export)
        self.assertIn('"filters"', json_export)
        self.assertIn('"filter_summary"', json_export)
        self.assertIn('"by_usage_status"', json_export)
        self.assertIn('"usage_status_label"', json_export)
        self.assertIn('"timeline"', json_export)
        self.assertIn('"action_items"', json_export)
        self.assertIn('"action_filter": "rights_attention"', action_json_export)
        self.assertIn('"duration_timecode"', json_export)
        self.assertIn('"total_count": 2', json_export)
        self.assertIn('"total_count": 1', action_json_export)
        with self.assertRaises(ValueError):
            self.service.list_project_library(project["id"], action_filter="maybe")


    def test_update_project_library_review_status(self):
        project = self.service.create_project("review project")
        task = self.service.create_search_task("air conditioner")
        result = self.service.list_results(task["id"])[0]
        search_material = self.service.add_material(project["id"], result["id"], tags=["search"], note="search material")

        asset = self.service.analyze_image(self.query_frame_path)
        match = self.service.find_frame_match(asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)
        frame_material = self.service.add_frame_match_material(
            project["id"],
            match["id"],
            tags=["frame"],
            note="frame material",
            review_status="confirmed",
        )

        updated_search = self.service.update_material_review_status(
            project["id"],
            "search_result",
            search_material["id"],
            "rejected",
        )
        updated_frame = self.service.update_material_review_status(
            project["id"],
            "frame_match",
            frame_material["id"],
            "pending",
        )
        rejected = self.service.list_project_library(project["id"], review_status="rejected")
        pending = self.service.list_project_library(project["id"], review_status="pending")

        self.assertEqual(updated_search["review_status"], "rejected")
        self.assertEqual(updated_frame["review_status"], "pending")
        self.assertEqual(rejected["total_count"], 1)
        self.assertEqual(rejected["items"][0]["source_type"], "search_result")
        self.assertEqual(pending["total_count"], 1)
        self.assertEqual(pending["items"][0]["source_type"], "frame_match")

        with self.assertRaises(ValueError):
            self.service.update_material_review_status(project["id"], "frame_match", frame_material["id"], "maybe")
        with self.assertRaises(ValueError):
            self.service.update_material_review_status(project["id"], "unknown", frame_material["id"], "pending")
        with self.assertRaises(KeyError):
            self.service.update_material_review_status(project["id"], "frame_match", 999, "pending")

    def test_update_project_library_metadata(self):
        project = self.service.create_project("metadata project")
        task = self.service.create_search_task("air conditioner")
        result = self.service.list_results(task["id"])[0]
        search_material = self.service.add_material(project["id"], result["id"], tags=["old"], note="old note")

        asset = self.service.analyze_image(self.query_frame_path)
        match = self.service.find_frame_match(asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)
        frame_material = self.service.add_frame_match_material(project["id"], match["id"], tags=["old frame"], note="old frame note")

        updated_search = self.service.update_material_metadata(
            project["id"],
            "search_result",
            search_material["id"],
            tags=[" 空调 ", "可用", "空调", ""],
            note="  可用于开场素材  ",
        )
        updated_frame = self.service.update_material_metadata(
            project["id"],
            "frame_match",
            frame_material["id"],
            tags=["截图反查", "高分"],
            note="匹配帧可复核",
        )
        library = self.service.list_project_library(project["id"])
        by_type = {item["source_type"]: item for item in library["items"]}

        self.assertEqual(updated_search["tags"], ["空调", "可用"])
        self.assertEqual(updated_search["note"], "可用于开场素材")
        self.assertEqual(updated_frame["tags"], ["截图反查", "高分"])
        self.assertEqual(by_type["search_result"]["tags"], ["空调", "可用"])
        self.assertEqual(by_type["search_result"]["note"], "可用于开场素材")
        self.assertEqual(by_type["frame_match"]["tags"], ["截图反查", "高分"])
        self.assertEqual(by_type["frame_match"]["note"], "匹配帧可复核")

        with self.assertRaises(ValueError):
            self.service.update_material_metadata(project["id"], "unknown", search_material["id"], tags=[], note="")
        with self.assertRaises(ValueError):
            self.service.update_material_metadata(project["id"], "search_result", search_material["id"], tags=["x" * 41], note="")
        with self.assertRaises(ValueError):
            self.service.update_material_metadata(project["id"], "search_result", search_material["id"], tags=[], note="x" * 1001)

    def test_update_project_library_rights_status(self):
        project = self.service.create_project("rights project")
        task = self.service.create_search_task("air conditioner")
        result = self.service.list_results(task["id"])[0]
        search_material = self.service.add_material(project["id"], result["id"], tags=["search"], note="search material")

        asset = self.service.analyze_image(self.query_frame_path)
        match = self.service.find_frame_match(asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)
        frame_material = self.service.add_frame_match_material(project["id"], match["id"], tags=["frame"], note="frame material")

        updated_search = self.service.update_material_rights_status(
            project["id"],
            "search_result",
            search_material["id"],
            "needs_permission",
        )
        updated_frame = self.service.update_material_rights_status(
            project["id"],
            "frame_match",
            frame_material["id"],
            "cleared",
        )
        needs_permission = self.service.list_project_library(project["id"], rights_status="needs_permission")
        cleared = self.service.list_project_library(project["id"], rights_status="cleared")
        json_export = self.service.export_project_library(project["id"], "json", rights_status="cleared")

        self.assertEqual(updated_search["rights_status"], "needs_permission")
        self.assertEqual(updated_frame["rights_status"], "cleared")
        self.assertEqual(needs_permission["summary"]["all_count"], 2)
        self.assertEqual(needs_permission["summary"]["filtered_count"], 1)
        self.assertEqual(needs_permission["summary"]["by_rights_status"]["needs_permission"], 1)
        self.assertEqual(needs_permission["summary"]["by_rights_status"]["cleared"], 1)
        self.assertEqual(needs_permission["total_count"], 1)
        self.assertEqual(needs_permission["items"][0]["source_type"], "search_result")
        self.assertEqual(cleared["total_count"], 1)
        self.assertEqual(cleared["items"][0]["source_type"], "frame_match")
        self.assertIn('"rights_status": "cleared"', json_export)

        with self.assertRaises(ValueError):
            self.service.update_material_rights_status(project["id"], "frame_match", frame_material["id"], "maybe")
        with self.assertRaises(ValueError):
            self.service.list_project_library(project["id"], rights_status="maybe")
        with self.assertRaises(KeyError):
            self.service.update_material_rights_status(project["id"], "search_result", 999, "cleared")

    def test_project_library_keyword_filter(self):
        project = self.service.create_project("keyword project")
        task = self.service.create_search_task("air conditioner")
        result = self.service.list_results(task["id"])[0]
        self.service.add_material(project["id"], result["id"], tags=["opening", "heat"], note="find by note")

        asset = self.service.analyze_image(self.query_frame_path)
        match = self.service.find_frame_match(asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)
        self.service.add_frame_match_material(project["id"], match["id"], tags=["visual"], note="frame only")

        by_tag = self.service.list_project_library(project["id"], keyword="opening")
        by_note = self.service.list_project_library(project["id"], keyword="frame only")
        by_path = self.service.list_project_library(project["id"], keyword="stage2-self-made")
        by_timecode = self.service.list_project_library(project["id"], keyword="00:00:")
        by_duration = self.service.list_project_library(project["id"], keyword="00:00:00.")
        by_evidence = self.service.list_project_library(project["id"], keyword="精排")
        by_confidence = self.service.list_project_library(project["id"], keyword="可信")
        missing = self.service.list_project_library(project["id"], keyword="not-found-keyword")
        md_export = self.service.export_project_library(project["id"], "md", keyword="opening")

        self.assertEqual(by_tag["total_count"], 1)
        self.assertEqual(by_tag["items"][0]["source_type"], "search_result")
        self.assertEqual(by_tag["summary"]["all_count"], 2)
        self.assertEqual(by_tag["summary"]["filtered_count"], 1)
        self.assertEqual(by_note["total_count"], 1)
        self.assertEqual(by_note["items"][0]["source_type"], "frame_match")
        self.assertEqual(by_path["total_count"], 1)
        self.assertEqual(by_timecode["total_count"], 1)
        self.assertEqual(by_timecode["items"][0]["source_type"], "frame_match")
        self.assertEqual(by_duration["total_count"], 1)
        self.assertEqual(by_duration["items"][0]["source_type"], "frame_match")
        self.assertEqual(by_evidence["total_count"], 1)
        self.assertEqual(by_evidence["items"][0]["source_type"], "frame_match")
        self.assertEqual(by_confidence["total_count"], 1)
        self.assertEqual(by_confidence["items"][0]["source_type"], "frame_match")
        self.assertEqual(missing["total_count"], 0)
        self.assertIn("opening", md_export)
        self.assertNotIn("frame only", md_export)

    def test_project_library_sorts_by_match_time(self):
        project = self.service.create_project("time sort project")
        task = self.service.create_search_task("air conditioner")
        result = self.service.list_results(task["id"])[0]
        self.service.add_material(project["id"], result["id"], tags=["search"], note="no timestamp")

        early_asset = self.service.analyze_image(self.query_frame_path)
        late_asset = self.service.analyze_image(self.variant_paths["tone"])
        early_match = self.service.find_frame_match(early_asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)
        late_match = self.service.find_frame_match(late_asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)
        self.service.add_frame_match_material(project["id"], late_match["id"], tags=["late"], note="late")
        self.service.add_frame_match_material(project["id"], early_match["id"], tags=["early"], note="early")

        time_asc = self.service.list_project_library(project["id"], sort_by="time_asc")
        time_desc = self.service.list_project_library(project["id"], sort_by="time_desc")

        self.assertEqual(time_asc["items"][0]["source_type"], "frame_match")
        self.assertEqual(time_asc["items"][1]["source_type"], "frame_match")
        self.assertLessEqual(time_asc["items"][0]["selected_timestamp_ms"], time_asc["items"][1]["selected_timestamp_ms"])
        self.assertEqual(time_asc["items"][-1]["source_type"], "search_result")
        self.assertGreaterEqual(time_desc["items"][0]["selected_timestamp_ms"], time_desc["items"][1]["selected_timestamp_ms"])
        self.assertEqual(time_desc["items"][-1]["source_type"], "search_result")

    def test_project_library_filters_by_match_confidence(self):
        project = self.service.create_project("confidence project")
        task = self.service.create_search_task("air conditioner")
        result = self.service.list_results(task["id"])[0]
        self.service.add_material(project["id"], result["id"], tags=["search"], note="not a frame match")

        asset = self.service.analyze_image(self.query_frame_path)
        match = self.service.find_frame_match(asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)
        self.service.add_frame_match_material(project["id"], match["id"], tags=["frame"], note="confidence filter")
        confidence = self.service._match_confidence(match["combined_score"])

        filtered = self.service.list_project_library(project["id"], match_confidence=confidence)
        empty = self.service.list_project_library(project["id"], match_confidence="low" if confidence != "low" else "high")
        json_export = self.service.export_project_library(project["id"], "json", match_confidence=confidence)

        self.assertEqual(filtered["total_count"], 1)
        self.assertEqual(filtered["items"][0]["source_type"], "frame_match")
        self.assertEqual(filtered["items"][0]["match_confidence"], confidence)
        self.assertEqual(filtered["summary"]["all_count"], 2)
        self.assertEqual(filtered["summary"]["filtered_count"], 1)
        self.assertEqual(filtered["summary"]["by_match_confidence"][confidence], 1)
        self.assertEqual(empty["total_count"], 0)
        self.assertIn(f'"match_confidence": "{confidence}"', json_export)

        with self.assertRaises(ValueError):
            self.service.list_project_library(project["id"], match_confidence="maybe")

    def test_project_library_sorts_by_match_confidence(self):
        project = self.service.create_project("confidence sort project")
        task = self.service.create_search_task("air conditioner")
        result = self.service.list_results(task["id"])[0]
        self.service.add_material(project["id"], result["id"], tags=["search"], note="no confidence")

        asset = self.service.analyze_image(self.query_frame_path)
        match = self.service.find_frame_match(asset["id"], self.video_path, fps=1.0, threshold=ROBUSTNESS_THRESHOLD)
        self.service.add_frame_match_material(project["id"], match["id"], tags=["frame"], note="has confidence")

        desc = self.service.list_project_library(project["id"], sort_by="confidence_desc")
        asc = self.service.list_project_library(project["id"], sort_by="confidence_asc")

        self.assertEqual(desc["items"][0]["source_type"], "frame_match")
        self.assertIn(desc["items"][0]["match_confidence"], {"high", "medium", "low"})
        self.assertEqual(desc["items"][-1]["source_type"], "search_result")
        self.assertEqual(asc["items"][0]["source_type"], "frame_match")
        self.assertEqual(asc["items"][-1]["source_type"], "search_result")


if __name__ == "__main__":
    unittest.main()
