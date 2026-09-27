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

from dialogue import TURNS


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


def require_relative(value: str, field: str) -> None:
    if Path(value).is_absolute() or value.startswith("~"):
        raise ValueError(f"{field} must be a portable relative path")


def check_contiguous(turn_id: int, start: float, end: float, cards: list[dict[str, Any]], start_key: str, end_key: str) -> None:
    if not cards:
        raise ValueError(f"turn {turn_id} has no subtitle cards")
    if not close(cards[0][start_key], start) or not close(cards[-1][end_key], end):
        raise ValueError(f"turn {turn_id} subtitle coverage differs from turn bounds")
    for previous, current in zip(cards, cards[1:]):
        if not close(previous[end_key], current[start_key]):
            raise ValueError(f"turn {turn_id} subtitle gap or overlap")
    if any(float(card[start_key]) >= float(card[end_key]) for card in cards):
        raise ValueError(f"turn {turn_id} has an empty subtitle card")


def validate(audio_path: Path, alignment: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    require_relative(alignment["audio"], "alignment.audio")
    require_relative(metadata["audio"], "metadata.audio")
    require_relative(metadata["timingBasis"]["alignmentFile"], "metadata.timingBasis.alignmentFile")
    audio_hash = sha256(audio_path)
    if alignment.get("audioSha256") != audio_hash or metadata.get("audioSha256") != audio_hash:
        raise ValueError("audio hash mismatch invalidates alignment and metadata")
    aligned = alignment.get("utterances", [])
    rendered = metadata.get("utterances", [])
    if len(aligned) != len(TURNS) or len(rendered) != len(TURNS):
        raise ValueError("timeline must contain all 16 turns")

    previous_end = 0.0
    speaker_counts: Counter[str] = Counter()
    card_count = 0
    for expected, source, output in zip(TURNS, aligned, rendered):
        identity = (expected.id, expected.speaker_id, expected.speaker_label, expected.text)
        if (source.get("id"), source.get("speakerId"), source.get("speakerLabel"), source.get("text")) != identity:
            raise ValueError(f"turn {expected.id} alignment differs from confirmed script")
        if (output.get("id"), output.get("speakerId"), output.get("speakerLabel"), output.get("text")) != identity:
            raise ValueError(f"turn {expected.id} metadata differs from confirmed script")
        start, end = float(source["start"]), float(source["end"])
        if start < previous_end - EPSILON or start >= end:
            raise ValueError(f"turn {expected.id} bounds overlap or reverse")
        if not close(output["start"], start) or not close(output["end"], end):
            raise ValueError(f"turn {expected.id} rendered bounds mismatch")
        previous_end = end
        speaker_counts[expected.speaker_id] += 1

        cards = source["cards"]
        units = output["subtitleUnits"]
        expected_cards = [card.replace("|", "") for card in expected.cards]
        if [card.get("text") for card in cards] != expected_cards or [unit.get("text") for unit in units] != expected_cards:
            raise ValueError(f"turn {expected.id} cards differ from confirmed script")
        check_contiguous(expected.id, start, end, cards, "subtitleStart", "subtitleEnd")
        check_contiguous(expected.id, start, end, units, "start", "end")
        for index, (card, unit) in enumerate(zip(cards, units)):
            wanted_start = start if index == 0 else float(card["predictedStart"])
            if not close(unit["start"], wanted_start):
                raise ValueError(f"turn {expected.id} card {index + 1} is detached from forced alignment")
            evidence = unit.get("alignmentEvidence", {})
            if not close(evidence.get("predictedStart"), card["predictedStart"]):
                raise ValueError(f"turn {expected.id} card {index + 1} evidence mismatch")
            low_confidence = (
                card.get("score") is not None and float(card["score"]) < 0.5
            ) or card.get("mappingStatus") != "exact_first_char"
            review = card.get("manualReview", {})
            if low_confidence and (review.get("status") != "reviewed" or not review.get("evidence")):
                raise ValueError(f"turn {expected.id} card {index + 1} needs manual review")
        card_count += len(cards)

    with wave.open(str(audio_path), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 24_000):
            raise ValueError("audio must be mono 16-bit PCM WAV at 24 kHz")
        duration = audio.getnframes() / audio.getframerate()
    if previous_end > duration + EPSILON:
        raise ValueError("last turn ends after final audio")
    if dict(speaker_counts) != {"left_student": 8, "right_teacher": 8}:
        raise ValueError("speaker mapping/count mismatch")
    return {"turns": len(TURNS), "cards": card_count, "speakers": dict(speaker_counts), "audioSha256": audio_hash, "audioDuration": duration}


def probe_video(video_path: Path, expected_duration: float) -> dict[str, Any]:
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels", "-of", "json", str(video_path)]
    data = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)
    streams = {stream["codec_type"]: stream for stream in data["streams"]}
    video, audio = streams.get("video", {}), streams.get("audio", {})
    duration = float(data["format"]["duration"])
    if (video.get("codec_name"), video.get("width"), video.get("height"), video.get("r_frame_rate")) != ("h264", 720, 1280, "24/1"):
        raise ValueError("video must be H.264 720x1280 at 24fps")
    if (audio.get("codec_name"), audio.get("sample_rate"), audio.get("channels")) != ("aac", "24000", 1):
        raise ValueError("video audio must be AAC 24 kHz mono")
    if abs(duration - expected_duration) > 0.05:
        raise ValueError("video duration differs from final audio")
    return {"duration": duration, "video": "h264", "audio": "aac"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify final audio, alignment, metadata, and video.")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--alignment", type=Path, default=ROOT / "dialogue_alignment.json")
    parser.add_argument("--metadata", type=Path, default=ROOT / "dialogue_metadata.json")
    parser.add_argument("--video", type=Path, default=ROOT / "claude-code-cloud-sessions-cats.mp4")
    parser.add_argument("--skip-video", action="store_true")
    args = parser.parse_args()
    result = validate(
        args.audio,
        json.loads(args.alignment.read_text(encoding="utf-8")),
        json.loads(args.metadata.read_text(encoding="utf-8")),
    )
    if not args.skip_video:
        result["video"] = probe_video(args.video, result["audioDuration"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
