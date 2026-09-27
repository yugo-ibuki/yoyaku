#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import wave
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EPSILON = 0.002


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= EPSILON


def require_portable_path(value: str, field: str) -> None:
    if Path(value).is_absolute() or value.startswith("~"):
        raise ValueError(f"{field} must be a portable relative path: {value}")


def check_units(turn_id: int, start: float, end: float, units: list[dict[str, Any]], start_key: str, end_key: str) -> None:
    if not units:
        raise ValueError(f"turn {turn_id} has no subtitle cards")
    if not close(units[0][start_key], start) or not close(units[-1][end_key], end):
        raise ValueError(f"turn {turn_id} subtitle coverage does not match turn bounds")
    for previous, current in zip(units, units[1:]):
        if not close(previous[end_key], current[start_key]):
            raise ValueError(f"turn {turn_id} subtitle gap or overlap")
    if any(float(unit[start_key]) >= float(unit[end_key]) for unit in units):
        raise ValueError(f"turn {turn_id} has an empty or reversed subtitle card")


def validate(
    audio_path: Path,
    alignment: dict[str, Any],
    metadata: dict[str, Any],
    *,
    expected_turns: int,
    expected_cards: int,
    expected_speakers: dict[str, int],
) -> dict[str, Any]:
    require_portable_path(alignment["audio"], "alignment.audio")
    require_portable_path(metadata["audio"], "metadata.audio")
    require_portable_path(metadata["timingBasis"]["alignmentFile"], "metadata.timingBasis.alignmentFile")
    if alignment["audioSha256"] != sha256(audio_path):
        raise ValueError("alignment audio hash does not match the final audio hash")

    aligned_turns = alignment["utterances"]
    rendered_turns = metadata["utterances"]
    if len(aligned_turns) != expected_turns or len(rendered_turns) != expected_turns:
        raise ValueError(f"expected {expected_turns} turns")
    aligned_by_id = {turn["id"]: turn for turn in aligned_turns}
    rendered_by_id = {turn["id"]: turn for turn in rendered_turns}
    if set(aligned_by_id) != set(rendered_by_id) or len(aligned_by_id) != expected_turns:
        raise ValueError("turn IDs are missing or duplicated")

    speaker_counts = Counter(turn["speaker"] for turn in aligned_turns)
    if dict(speaker_counts) != expected_speakers:
        raise ValueError(f"wrong speaker counts: {dict(speaker_counts)}")

    total_cards = 0
    previous_end = -1.0
    for turn_id in sorted(aligned_by_id):
        aligned = aligned_by_id[turn_id]
        rendered = rendered_by_id[turn_id]
        if aligned["speaker"] != rendered["speaker"] or aligned["speakerLabel"] != rendered["speakerLabel"]:
            raise ValueError(f"turn {turn_id} speaker mismatch")
        if aligned["text"] != rendered["text"]:
            raise ValueError(f"turn {turn_id} transcript mismatch")
        if aligned["start"] < previous_end - EPSILON:
            raise ValueError(f"turn {turn_id} overlaps the preceding turn")
        if not close(aligned["start"], rendered["start"]) or not close(aligned["end"], rendered["end"]):
            raise ValueError(f"turn {turn_id} bounds mismatch")
        previous_end = aligned["end"]

        cards = aligned["cards"]
        units = rendered["subtitleUnits"]
        if len(cards) != len(units):
            raise ValueError(f"turn {turn_id} card count mismatch")
        if "".join(card["text"] for card in cards) != aligned["text"]:
            raise ValueError(f"turn {turn_id} aligned card transcript mismatch")
        if "".join(unit["text"] for unit in units) != rendered["text"]:
            raise ValueError(f"turn {turn_id} rendered card transcript mismatch")
        check_units(turn_id, aligned["start"], aligned["end"], cards, "subtitleStart", "subtitleEnd")
        check_units(turn_id, rendered["start"], rendered["end"], units, "start", "end")
        for index, (card, unit) in enumerate(zip(cards, units)):
            if card["text"] != unit["text"]:
                raise ValueError(f"turn {turn_id} card {index + 1} transcript mismatch")
            expected_start = aligned["start"] if index == 0 else card["predictedStart"]
            if not close(unit["start"], expected_start):
                raise ValueError(f"turn {turn_id} card {index + 1} start deviates from forced alignment")
            if not close(unit["alignmentEvidence"]["predictedStart"], card["predictedStart"]):
                raise ValueError(f"turn {turn_id} card {index + 1} forced alignment evidence mismatch")
            low_confidence = (card.get("score") is not None and float(card["score"]) < 0.5) or (
                card.get("mappingStatus") is not None and card["mappingStatus"] != "exact_first_char"
            )
            review = card.get("manualReview", {})
            if low_confidence and (review.get("status") != "reviewed" or not review.get("evidence")):
                raise ValueError(f"turn {turn_id} card {index + 1} low-confidence boundary requires manual review evidence")
        total_cards += len(cards)

    if total_cards != expected_cards:
        raise ValueError(f"expected {expected_cards} cards, got {total_cards}")
    with wave.open(str(audio_path), "rb") as audio:
        duration = audio.getnframes() / audio.getframerate()
    if previous_end > duration + EPSILON:
        raise ValueError("last turn extends beyond the final audio")
    return {"turns": len(aligned_turns), "cards": total_cards, "speakers": dict(speaker_counts), "audioSha256": sha256(audio_path), "audioDuration": duration}


def probe_video(path: Path, expected_duration: float) -> dict[str, Any]:
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(completed.stdout)
    streams = {stream["codec_type"]: stream for stream in data["streams"]}
    video = streams.get("video", {})
    audio = streams.get("audio", {})
    duration = float(data["format"]["duration"])
    if video.get("codec_name") != "h264" or (video.get("width"), video.get("height"), video.get("r_frame_rate")) != (720, 1280, "24/1"):
        raise ValueError("final video stream is not H.264 720x1280 at 24 fps")
    if audio.get("codec_name") != "aac" or audio.get("sample_rate") != "24000" or audio.get("channels") != 1:
        raise ValueError("final audio stream is not AAC 24 kHz mono")
    if abs(duration - expected_duration) > 0.05:
        raise ValueError("final MP4 duration differs from the source audio")
    return {"duration": duration, "video": video["codec_name"], "audio": audio["codec_name"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate audio, alignment, subtitles, speakers, and the final MP4.")
    parser.add_argument("--audio", type=Path, default=ROOT / "dialogue-new.wav")
    parser.add_argument("--alignment", type=Path, default=ROOT / "dialogue_alignment.json")
    parser.add_argument("--metadata", type=Path, default=ROOT / "dialogue_metadata.json")
    parser.add_argument("--video", type=Path, default=ROOT / "fractal-engineering-cats-aligned.mp4")
    parser.add_argument("--skip-video", action="store_true", help="Validate timing inputs before the expensive video render")
    args = parser.parse_args()
    result = validate(
        args.audio,
        json.loads(args.alignment.read_text(encoding="utf-8")),
        json.loads(args.metadata.read_text(encoding="utf-8")),
        expected_turns=16,
        expected_cards=34,
        expected_speakers={"left": 8, "right": 8},
    )
    if not args.skip_video:
        result["video"] = probe_video(args.video, result["audioDuration"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
