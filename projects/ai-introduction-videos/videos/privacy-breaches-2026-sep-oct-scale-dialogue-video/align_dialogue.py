#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path
from typing import Any

from dialogue import TURNS, display_prefix_to_tts


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        if audio.getcomptype() != "NONE" or audio.getsampwidth() != 2 or audio.getnchannels() != 1:
            raise ValueError("final audio must be mono uncompressed 16-bit PCM WAV")
        return audio.getnframes() / audio.getframerate()


def validate_verified_turns(audio_path: Path, document: dict[str, Any]) -> list[dict[str, Any]]:
    if document.get("audioSha256") != sha256(audio_path):
        raise ValueError("verified turns audio hash does not match final audio")
    items = document.get("turns", [])
    if len(items) != len(TURNS):
        raise ValueError(f"expected {len(TURNS)} verified turns")
    duration, previous_end = audio_duration(audio_path), 0.0
    for expected, item in zip(TURNS, items):
        if (item.get("id"), item.get("speakerId"), item.get("scriptText"), item.get("ttsText")) != (
            expected.id, expected.speaker_id, expected.text, expected.tts_text
        ):
            raise ValueError(f"turn {expected.id} identity or script mismatch")
        if not item.get("observedText"):
            raise ValueError(f"turn {expected.id} observed text is required")
        assessment = item.get("textAssessment", {})
        if assessment.get("status") not in {"confirmed_match", "reviewed_asr_disagreement"} or not assessment.get("evidence"):
            raise ValueError(f"turn {expected.id} needs audio/script assessment evidence")
        review = item.get("review", {})
        if review.get("status") not in {"machine_reviewed", "human_reviewed"} or not review.get("evidence"):
            raise ValueError(f"turn {expected.id} needs boundary review evidence")
        if review["status"] == "machine_reviewed" and review.get("subjectiveListening") is not False:
            raise ValueError(f"turn {expected.id} machine review must keep subjectiveListening=false")
        if item.get("start") is None or item.get("end") is None:
            raise ValueError(f"turn {expected.id} bounds must be measured from the adopted audio")
        start, end = float(item["start"]), float(item["end"])
        if start < previous_end or start >= end or end > duration + 0.002:
            raise ValueError(f"turn {expected.id} has invalid or overlapping bounds")
        previous_end = end
    return items


def find_aligned_char(chars: list[dict[str, Any]], index: int, limit: int) -> tuple[dict[str, Any], str]:
    if index < len(chars) and chars[index].get("start") is not None:
        return chars[index], "exact_first_char"
    for offset in range(index + 1, min(limit, len(chars))):
        if chars[offset].get("start") is not None:
            return chars[offset], "first_char_unmapped_used_next_char"
    raise ValueError("subtitle card has no aligned character; review is required")


def align(audio_path: Path, verified_path: Path) -> dict[str, Any]:
    reviewed = validate_verified_turns(audio_path, json.loads(verified_path.read_text(encoding="utf-8")))
    try:
        import whisperx
    except ImportError as exc:
        raise RuntimeError("WhisperX is required for final-audio forced alignment") from exc
    model, metadata = whisperx.load_align_model(language_code="ja", device="cpu", model_cache_only=True)
    segments = [
        {"start": float(item["start"]), "end": float(item["end"]), "text": turn.tts_text}
        for turn, item in zip(TURNS, reviewed)
    ]
    result = whisperx.align(
        segments,
        model,
        metadata,
        whisperx.load_audio(str(audio_path)),
        "cpu",
        return_char_alignments=True,
    )
    if len(result.get("segments", [])) != len(TURNS):
        raise RuntimeError("forced alignment did not return every turn")
    utterances = []
    for turn, bounds, aligned in zip(TURNS, reviewed, result["segments"]):
        chars = aligned.get("chars", [])
        if "".join(item.get("char", "") for item in chars) != turn.tts_text:
            raise RuntimeError(f"turn {turn.id} alignment characters differ from exact TTS input")
        display_cursor, cards = 0, []
        for marked in turn.cards:
            text = marked.replace("|", "")
            spoken_prefix, rules = display_prefix_to_tts(turn, turn.text[:display_cursor])
            spoken_through, _ = display_prefix_to_tts(turn, turn.text[:display_cursor + len(text)])
            tts_index, tts_limit = len(spoken_prefix), len(spoken_through)
            found, status = find_aligned_char(chars, tts_index, tts_limit)
            cards.append({
                "text": text,
                "lines": marked.split("|"),
                "predictedStart": round(float(found["start"]), 3),
                "alignedFirstChar": found.get("char"),
                "score": None if found.get("score") is None else round(float(found["score"]), 3),
                "mappingStatus": status,
                "pronunciationMapping": {
                    "displayStartIndex": display_cursor,
                    "ttsStartIndex": tts_index,
                    "ttsAlignedChar": found.get("char"),
                    "rulesAppliedInPrefix": rules,
                    "basis": "explicit_turn_scoped_display_to_tts_replacements",
                },
            })
            display_cursor += len(text)
        for index, card in enumerate(cards):
            card["subtitleStart"] = round(float(bounds["start"]), 3) if index == 0 else card["predictedStart"]
            card["subtitleEnd"] = cards[index + 1]["predictedStart"] if index + 1 < len(cards) else round(float(bounds["end"]), 3)
        utterances.append({
            "id": turn.id,
            "speakerId": turn.speaker_id,
            "speakerLabel": turn.speaker_label,
            "start": round(float(bounds["start"]), 3),
            "end": round(float(bounds["end"]), 3),
            "text": turn.text,
            "alignedTtsText": turn.tts_text,
            "observedText": bounds["observedText"],
            "textAssessment": bounds["textAssessment"],
            "turnReview": bounds["review"],
            "cards": cards,
        })
    return {
        "version": 1,
        "audio": audio_path.resolve().relative_to(ROOT).as_posix(),
        "audioSha256": sha256(audio_path),
        "verifiedTurns": verified_path.resolve().relative_to(ROOT).as_posix(),
        "verifiedTurnsSha256": sha256(verified_path),
        "method": "speaker turns reviewed from this audio's transcript and waveform; exact TTS input force-aligned with WhisperX; display-card starts mapped through explicit pronunciation replacements",
        "utterances": utterances,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Force-align exact captions inside reviewed adopted-audio turns.")
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--verified-turns", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "dialogue_alignment.json")
    args = parser.parse_args()
    args.output.write_text(json.dumps(align(args.audio, args.verified_turns), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
