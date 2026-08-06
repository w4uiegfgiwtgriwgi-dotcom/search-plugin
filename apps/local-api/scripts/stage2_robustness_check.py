from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from vmf_api.service import LocalApiService  # noqa: E402

FIXTURE_DIR = API_ROOT / "tests" / "fixtures" / "stage2"
VIDEO_PATH = FIXTURE_DIR / "stage2-self-made-testsrc.mp4"
QUERY_FRAME_PATH = FIXTURE_DIR / "stage2-air-query.png"
THRESHOLD = 0.45


def run_ffmpeg(args: list[str], required: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=False, capture_output=True, text=True)
    if required and result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result


def ensure_fixtures() -> dict[str, Path]:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(["-f", "lavfi", "-i", "testsrc=size=160x90:rate=1:duration=3", str(VIDEO_PATH)])
    run_ffmpeg(["-ss", "1", "-i", str(VIDEO_PATH), "-frames:v", "1", str(QUERY_FRAME_PATH)])

    variants = {
        "compressed": FIXTURE_DIR / "stage2-air-query-compressed.jpg",
        "scaled": FIXTURE_DIR / "stage2-air-query-scaled.png",
        "tone": FIXTURE_DIR / "stage2-air-query-tone.png",
        "text": FIXTURE_DIR / "stage2-air-query-text.png",
        "occlusion": FIXTURE_DIR / "stage2-air-query-occlusion.png",
    }
    run_ffmpeg(["-i", str(QUERY_FRAME_PATH), "-q:v", "8", str(variants["compressed"])])
    run_ffmpeg(["-i", str(QUERY_FRAME_PATH), "-vf", "scale=96:54", str(variants["scaled"])])
    run_ffmpeg(["-i", str(QUERY_FRAME_PATH), "-vf", "eq=brightness=0.08:saturation=0.8", str(variants["tone"])])
    text_result = run_ffmpeg([
        "-i",
        str(QUERY_FRAME_PATH),
        "-vf",
        "drawtext=text='MOCK':x=8:y=h-24:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.55",
        str(variants["text"]),
    ], required=False)
    if text_result.returncode != 0:
        run_ffmpeg(["-i", str(QUERY_FRAME_PATH), "-vf", "drawbox=x=6:y=h-24:w=70:h=18:color=black@0.85:t=fill", str(variants["text"])])
    run_ffmpeg(["-i", str(QUERY_FRAME_PATH), "-vf", "drawbox=x=18:y=18:w=48:h=28:color=black@0.9:t=fill", str(variants["occlusion"])])
    return variants


def check_variants() -> list[dict[str, object]]:
    variants = ensure_fixtures()
    service = LocalApiService(":memory:")
    rows: list[dict[str, object]] = []
    try:
        for name, image_path in variants.items():
            asset = service.analyze_image(image_path)
            match = service.find_frame_match(asset["id"], VIDEO_PATH, fps=1.0, threshold=THRESHOLD)
            rows.append({
                "variant": name,
                "combined_score": round(float(match["combined_score"]), 3),
                "phash_score": round(float(match["phash_score"]), 3),
                "match_type": match["match_type"],
                "passed": float(match["combined_score"]) >= THRESHOLD,
            })
    finally:
        service.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()

    rows = check_variants()
    if args.markdown:
        print("| 变形场景 | 综合分 | pHash 分 | 结果 |")
        print("| --- | ---: | ---: | --- |")
        for row in rows:
            result = "通过" if row["passed"] else "未通过"
            print(f"| {row['variant']} | {row['combined_score']} | {row['phash_score']} | {result} |")
    else:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0 if all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
