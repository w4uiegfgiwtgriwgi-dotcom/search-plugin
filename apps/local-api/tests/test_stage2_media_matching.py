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


if __name__ == "__main__":
    unittest.main()
