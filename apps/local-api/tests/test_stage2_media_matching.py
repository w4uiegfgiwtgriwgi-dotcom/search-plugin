import subprocess
import unittest
from pathlib import Path

from vmf_api.service import LocalApiService


FIXTURE_DIR = Path("tests/fixtures/stage2")


def run_ffmpeg(args):
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


class Stage2MediaMatchingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        cls.video_path = FIXTURE_DIR / "stage2-self-made-testsrc.mp4"
        cls.query_frame_path = FIXTURE_DIR / "stage2-air-query.png"
        run_ffmpeg([
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=1:duration=3",
            str(cls.video_path),
        ])
        run_ffmpeg([
            "-ss",
            "1",
            "-i",
            str(cls.video_path),
            "-frames:v",
            "1",
            str(cls.query_frame_path),
        ])

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
        self.assertTrue(Path(match["local_frame_path"]).exists())
        self.assertEqual(match["evidence_json"]["frame_count"], 3)


if __name__ == "__main__":
    unittest.main()
