#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DEFAULT_FONT = Path("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def samples(metadata: dict[str, Any], video_duration: float) -> list[dict[str, Any]]:
    turns = metadata["utterances"]
    result: list[dict[str, Any]] = [{
        "kind": "endpoint",
        "time": min(1 / 48, video_duration / 2),
        "expectedMouth": "both:closed before first measured turn",
        "label": "冒頭",
    }]
    for turn in turns:
        result.append({
            "kind": "speaker-peak",
            "turnId": turn["id"],
            "speakerId": turn["speakerId"],
            "time": float(turn["mouthMotion"]["peakTime"]),
            "expectedMouth": f"{turn['speakerId']}:open listener:closed",
            "label": f"T{turn['id']:02d} {turn['speakerId']}",
        })
        for card_number, card in enumerate(turn["subtitleUnits"], 1):
            start, end = float(card["start"]), float(card["end"])
            result.append({
                "kind": "subtitle-card",
                "turnId": turn["id"],
                "cardNumber": card_number,
                "time": (start + end) / 2,
                "expectedText": card["text"],
                "expectedMouth": "speaker RMS-gated; listener unchanged",
                "label": f"T{turn['id']:02d} C{card_number:02d}",
            })
    for left, right in zip(turns, turns[1:]):
        result.extend([
            {
                "kind": "handoff-before",
                "afterTurn": left["id"],
                "time": max(float(left["start"]), float(left["end"]) - 1 / 48),
                "expectedMouth": f"{left['speakerId']} tail; listener unchanged",
                "label": f"T{left['id']:02d}→T{right['id']:02d} 前",
            },
            {
                "kind": "handoff-after",
                "turnId": right["id"],
                "time": min(float(right["end"]), float(right["start"]) + 1 / 48),
                "expectedMouth": f"{right['speakerId']} onset; listener unchanged",
                "label": f"T{left['id']:02d}→T{right['id']:02d} 後",
            },
        ])
    if video_duration - float(turns[-1]["end"]) >= 0.04:
        result.append({
            "kind": "silence",
            "time": (float(turns[-1]["end"]) + video_duration) / 2,
            "expectedMouth": "both:closed",
            "label": "末尾無音",
        })
    result.append({
        "kind": "endpoint",
        # The container can be slightly longer than the final video-frame PTS
        # because AAC extends past the last frame. Step back two frames.
        "time": max(0.0, video_duration - 2 / 24),
        "expectedMouth": "both:closed at final frame",
        "label": "末尾",
    })
    for state in metadata.get("numericOverlays", []):
        result.append({"kind":"numeric-overlay", "turnId":state["turnId"], "time":(state["start"]+state["end"])/2,
                       "expectedNumber":state["number"], "expectedQualifier":state["qualifier"],
                       "stateId":state["stateId"], "label":"数字 " + state["stateId"]})
    return sorted(result, key=lambda item: item["time"])


def make_sheet(items: list[dict[str, Any]], frame_dir: Path, output: Path, font_path: Path) -> None:
    columns, tile_w, image_h, label_h = 4, 320, 180, 32
    canvas = Image.new("RGB", (columns * tile_w, math.ceil(len(items) / columns) * (image_h + label_h)), (13, 17, 24))
    draw, font = ImageDraw.Draw(canvas), ImageFont.truetype(str(font_path), 17)
    for index, item in enumerate(items):
        image = Image.open(frame_dir / item["file"]).convert("RGB").resize((tile_w, image_h), Image.Resampling.LANCZOS)
        x, y = (index % columns) * tile_w, (index // columns) * (image_h + label_h)
        canvas.paste(image, (x, y))
        draw.text((x + 7, y + image_h + 5), f"{item['label']} {item['time']:.3f}s", font=font, fill="white")
    canvas.save(output)


def make_paginated_sheets(
    items: list[dict[str, Any]], frame_dir: Path, output_dir: Path, font_path: Path, page_size: int = 12,
) -> list[str]:
    columns, tile_w, image_h, label_h = 2, 640, 360, 42
    font = ImageFont.truetype(str(font_path), 23)
    files: list[str] = []
    for page_number, offset in enumerate(range(0, len(items), page_size), 1):
        page = items[offset:offset + page_size]
        rows = math.ceil(len(page) / columns)
        canvas = Image.new("RGB", (columns * tile_w, rows * (image_h + label_h)), (13, 17, 24))
        draw = ImageDraw.Draw(canvas)
        for index, item in enumerate(page):
            image = Image.open(frame_dir / item["file"]).convert("RGB").resize((tile_w, image_h), Image.Resampling.LANCZOS)
            x, y = (index % columns) * tile_w, (index // columns) * (image_h + label_h)
            canvas.paste(image, (x, y))
            draw.text((x + 9, y + image_h + 7), f"{item['label']} {item['time']:.3f}s", font=font, fill="white")
        name = f"contact-sheet-{page_number:02d}.png"
        canvas.save(output_dir / name)
        files.append(name)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract speaker-peak and silence frames for visual QA.")
    parser.add_argument("--video", type=Path, default=ROOT / "privacy-breaches-2026-sep-oct-scale-cats.mp4")
    parser.add_argument("--metadata", type=Path, default=ROOT / "dialogue_metadata.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "qa")
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    items = samples(metadata, duration(args.video))
    frame_dir = args.output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(items, 1):
        file = f"{index:03d}-{item['kind']}-{item.get('turnId', item.get('afterTurn', 0)):02d}-{item.get('cardNumber', 0):02d}.png"
        frame_path = frame_dir / file
        # Re-extract even when a pathname exists: a new adopted audio/video
        # invalidates every previous QA frame and filename alone is no proof.
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{item['time']:.3f}", "-i", str(args.video), "-frames:v", "1", "-vf", "scale=1280:720", str(frame_path)],
            check=True,
        )
        item["file"], item["sha256"] = file, sha256(frame_path)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    make_sheet(items, frame_dir, args.output_dir / "contact-sheet.png", args.font)
    paginated = make_paginated_sheets(items, frame_dir, args.output_dir, args.font)
    manifest = {
        "video": args.video.name,
        "videoSha256": sha256(args.video),
        "metadata": args.metadata.name,
        "metadataSha256": sha256(args.metadata),
        "reviewStatus": "frames_extracted_pending_full_visual_review",
        "paginatedContactSheets": paginated,
        "coverage": {
            "subtitleCards": sum(item["kind"] == "subtitle-card" for item in items),
            "handoffBefore": sum(item["kind"] == "handoff-before" for item in items),
            "handoffAfter": sum(item["kind"] == "handoff-after" for item in items),
            "speakerPeaks": sum(item["kind"] == "speaker-peak" for item in items),
            "endpoints": sum(item["kind"] == "endpoint" for item in items),
            "numericStates": sum(item["kind"] == "numeric-overlay" for item in items),
        },
        "samples": items,
    }
    (args.output_dir / "frame-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output_dir / "contact-sheet.png")


if __name__ == "__main__":
    main()
