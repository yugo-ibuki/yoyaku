#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import wave
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from dialogue import TURNS


ROOT = Path(__file__).resolve().parent
SIZE = (720, 1280)
FPS = 24
DEFAULT_FONT = Path("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise ValueError(f"metadata input must be inside the project: {path}") from exc


def build_metadata(audio_path: Path, alignment_path: Path) -> dict[str, Any]:
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    if alignment.get("audioSha256") != sha256(audio_path):
        raise ValueError("alignment audio hash does not match render audio")
    if len(alignment.get("utterances", [])) != len(TURNS):
        raise ValueError("alignment must contain all 16 turns")
    utterances = []
    for expected, aligned in zip(TURNS, alignment["utterances"]):
        if (aligned.get("id"), aligned.get("speakerId"), aligned.get("text")) != (
            expected.id,
            expected.speaker_id,
            expected.text,
        ):
            raise ValueError(f"turn {expected.id} alignment differs from confirmed script")
        cards = aligned.get("cards", [])
        if [card.get("text") for card in cards] != [card.replace("|", "") for card in expected.cards]:
            raise ValueError(f"turn {expected.id} subtitle cards differ from confirmed script")
        utterances.append({
            "id": expected.id,
            "speakerId": expected.speaker_id,
            "speakerLabel": expected.speaker_label,
            "start": aligned["start"],
            "end": aligned["end"],
            "text": expected.text,
            "subtitleUnits": [
                {
                    "start": card["subtitleStart"],
                    "end": card["subtitleEnd"],
                    "text": card["text"],
                    "lines": card["lines"],
                    "alignmentEvidence": {
                        "predictedStart": card["predictedStart"],
                        "alignedFirstChar": card.get("alignedFirstChar"),
                        "score": card.get("score"),
                        "mappingStatus": card.get("mappingStatus"),
                    },
                }
                for card in cards
            ],
        })
    return {
        "version": 1,
        "audio": relative_to_root(audio_path),
        "audioSha256": sha256(audio_path),
        "timingBasis": {
            "alignmentFile": relative_to_root(alignment_path),
            "method": alignment.get("method"),
            "note": "Speaker turns were machine-reviewed from ASR, waveform silences, and pitch separation; subjective listening was not performed. Later caption cards begin at forced-aligned spoken characters.",
        },
        "video": {"width": SIZE[0], "height": SIZE[1], "fps": FPS},
        "utterances": utterances,
    }


def load_poses(source_dir: Path) -> tuple[Image.Image, Image.Image, Image.Image]:
    base = Image.open(source_dir / "base.png").convert("RGB")
    left_open = Image.open(source_dir / "left-speaking.png").convert("RGB")
    right_open = Image.open(source_dir / "right-speaking.png").convert("RGB")
    if {base.size, left_open.size, right_open.size} != {(941, 1672)}:
        raise ValueError("all three DINING/FOOD images must remain 941x1672")
    return (
        left_open.resize(SIZE, Image.Resampling.LANCZOS),
        right_open.resize(SIZE, Image.Resampling.LANCZOS),
        base.resize(SIZE, Image.Resampling.LANCZOS),
    )


def audio_duration(audio_path: Path) -> float:
    with wave.open(str(audio_path), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 24_000):
            raise ValueError("render audio must be mono 16-bit PCM WAV at 24 kHz")
        return audio.getnframes() / audio.getframerate()


def active_turn(metadata: dict[str, Any], time: float) -> dict[str, Any] | None:
    return next((turn for turn in metadata["utterances"] if turn["start"] <= time < turn["end"]), None)


def subtitle_at(metadata: dict[str, Any], time: float) -> tuple[dict[str, Any], dict[str, Any]] | None:
    turn = active_turn(metadata, time)
    if turn is None:
        return None
    unit = next((unit for unit in turn["subtitleUnits"] if unit["start"] <= time < unit["end"]), None)
    return (turn, unit) if unit else None


def draw_subtitle(frame: Image.Image, subtitle: tuple[dict[str, Any], dict[str, Any]] | None, fonts: tuple[Any, Any]) -> None:
    if subtitle is None:
        return
    turn, unit = subtitle
    label_font, text_font = fonts
    draw = ImageDraw.Draw(frame, "RGBA")
    lines = unit["lines"]
    box_h = 64 + 45 * len(lines)
    x0, x1 = 42, SIZE[0] - 42
    y0, y1 = SIZE[1] - 72 - box_h, SIZE[1] - 72
    draw.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=(12, 13, 18, 206), outline=(255, 255, 255, 34), width=2)
    color = (255, 188, 104, 255) if turn["speakerId"] == "left_student" else (158, 218, 255, 255)
    draw.text((x0 + 28, y0 + 15), turn["speakerLabel"], font=label_font, fill=color, stroke_width=1, stroke_fill=(0, 0, 0, 180))
    y = y0 + 57
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=text_font, stroke_width=2)
        draw.text(((SIZE[0] - (bbox[2] - bbox[0])) / 2, y), line, font=text_font, fill="white", stroke_width=3, stroke_fill=(0, 0, 0, 230))
        y += 45


def validate_subtitle_width(font_path: Path, max_width: int = 600) -> dict[str, Any]:
    font = ImageFont.truetype(str(font_path), 31)
    draw = ImageDraw.Draw(Image.new("RGB", SIZE))
    widest = {"width": 0, "turn": None, "text": ""}
    for turn in TURNS:
        for card in turn.cards:
            for line in card.split("|"):
                bbox = draw.textbbox((0, 0), line, font=font, stroke_width=3)
                width = bbox[2] - bbox[0]
                if width > widest["width"]:
                    widest = {"width": width, "turn": turn.id, "text": line}
                if width > max_width:
                    raise ValueError(f"turn {turn.id} subtitle line exceeds {max_width}px: {line}")
    return widest


def camera_frame(source: Image.Image, time: float, duration: float, speaker_id: str | None) -> Image.Image:
    zoom = 1.018 + 0.009 * math.sin(2 * math.pi * time / 13.0) + 0.006 * (time / duration)
    crop_w, crop_h = round(SIZE[0] / zoom), round(SIZE[1] / zoom)
    bias = -4 if speaker_id == "left_student" else 4 if speaker_id == "right_teacher" else 0
    cx = SIZE[0] / 2 + bias + 2.5 * math.sin(2 * math.pi * time / 9.7)
    cy = SIZE[1] / 2 - 2.0 * math.sin(2 * math.pi * time / 4.8)
    box = (round(cx - crop_w / 2), round(cy - crop_h / 2), round(cx + crop_w / 2), round(cy + crop_h / 2))
    return source.crop(box).resize(SIZE, Image.Resampling.BILINEAR)


def render(audio_path: Path, alignment_path: Path, source_dir: Path, output: Path, metadata_path: Path, font_path: Path) -> None:
    metadata = build_metadata(audio_path, alignment_path)
    validate_subtitle_width(font_path)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    duration = audio_duration(audio_path)
    frame_count = math.ceil(duration * FPS)
    left_speaking, right_speaking, base = load_poses(source_dir)
    fonts = (ImageFont.truetype(str(font_path), 24), ImageFont.truetype(str(font_path), 31))
    command = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", "720x1280", "-framerate", str(FPS), "-i", "-", "-i", str(audio_path), "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-t", f"{duration:.6f}", "-movflags", "+faststart", str(output)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for index in range(frame_count):
            time = min(index / FPS, duration)
            turn = active_turn(metadata, time)
            speaker_id = turn["speakerId"] if turn else None
            source = left_speaking if speaker_id == "left_student" else right_speaking if speaker_id == "right_teacher" else base
            frame = camera_frame(source, time, duration, speaker_id)
            draw_subtitle(frame, subtitle_at(metadata, time), fonts)
            fade = min(1.0, time / 0.45, (duration - time) / 0.45)
            if fade < 1:
                frame = Image.blend(Image.new("RGB", SIZE, (12, 10, 9)), frame, max(0.0, fade))
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("ffmpeg render failed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the verified two-cat dialogue timeline.")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--alignment", type=Path, default=ROOT / "dialogue_alignment.json")
    parser.add_argument("--source-dir", type=Path, default=ROOT.parent / "assets" / "dining-room")
    parser.add_argument("--output", type=Path, default=ROOT / "claude-code-cloud-sessions-cats.mp4")
    parser.add_argument("--metadata", type=Path, default=ROOT / "dialogue_metadata.json")
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    metadata = build_metadata(args.audio, args.alignment)
    if args.metadata_only:
        args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        render(args.audio, args.alignment, args.source_dir, args.output, args.metadata, args.font)
    print(args.metadata if args.metadata_only else args.output)


if __name__ == "__main__":
    main()
