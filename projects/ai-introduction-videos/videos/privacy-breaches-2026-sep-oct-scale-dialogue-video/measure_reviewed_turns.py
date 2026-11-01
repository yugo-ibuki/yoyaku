#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import wave
from pathlib import Path
from typing import Any

import numpy as np

from dialogue import TURNS


ROOT = Path(__file__).resolve().parent
THRESHOLD_DBFS = -38.0
WINDOW_SECONDS = 0.020
HOP_SECONDS = 0.005


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_energy(path: Path) -> tuple[np.ndarray, float, int, float]:
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getcomptype() != "NONE":
            raise ValueError("turn measurement requires mono uncompressed 16-bit PCM WAV")
        rate = audio.getframerate()
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    window, hop = round(WINDOW_SECONDS * rate), round(HOP_SECONDS * rate)
    rms = np.array([
        math.sqrt(float(np.mean(samples[index:index + window] ** 2)))
        for index in range(0, len(samples) - window + 1, hop)
    ])
    dbfs = 20 * np.log10(np.maximum(rms, 1e-9))
    return dbfs, hop / rate, rate, len(samples) / rate


def active_bound(dbfs: np.ndarray, step: float, search_start: float, search_end: float) -> tuple[float, float]:
    first = max(0, math.ceil(search_start / step))
    last = min(len(dbfs), math.ceil(search_end / step))
    indices = np.where(dbfs[first:last] > THRESHOLD_DBFS)[0] + first
    if not len(indices):
        raise ValueError(f"no active audio in {search_start:.3f}-{search_end:.3f}")
    return round(float(indices[0] * step), 3), round(float(indices[-1] * step + WINDOW_SECONDS), 3)


def fragment(segment: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    first, last = spec.get("wordStart"), spec.get("wordEnd")
    if first is None:
        return {"start": segment["start"], "end": segment["end"], "text": segment["text"]}
    words = segment.get("words", [])[int(first):None if last is None else int(last)]
    if not words:
        raise ValueError(f"empty ASR word slice: {spec}")
    return {
        "start": words[0]["start"],
        "end": words[-1]["end"],
        "text": "".join(word["text"] for word in words).strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure audio-specific reviewed turns from an explicit fresh-ASR mapping plan.")
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--asr", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--turns-output", type=Path, default=ROOT / "verified_turns.json")
    parser.add_argument("--waveform-output", type=Path, default=ROOT / "audio" / "waveform-evidence.json")
    args = parser.parse_args()
    audio_hash = sha256(args.audio)
    asr_hash = sha256(args.asr)
    asr = json.loads(args.asr.read_text(encoding="utf-8"))
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if asr.get("audioSha256") != audio_hash or plan.get("audioSha256") != audio_hash:
        raise ValueError("audio hash mismatch invalidates ASR turn plan")
    if plan.get("asrSha256") != asr_hash:
        raise ValueError("ASR hash mismatch invalidates turn plan")
    plan_turns = plan.get("turns", [])
    if len(plan_turns) != len(TURNS):
        raise ValueError(f"turn plan must contain {len(TURNS)} turns")
    segments = asr.get("segments", [])
    dbfs, step, rate, duration = load_energy(args.audio)
    measured, waveform, previous_end = [], [], 0.0
    for expected, item in zip(TURNS, plan_turns):
        if (item.get("id"), item.get("speakerId")) != (expected.id, expected.speaker_id):
            raise ValueError(f"turn {expected.id} plan identity mismatch")
        slices = item.get("asrSlices", [])
        if not slices:
            raise ValueError(f"turn {expected.id} has no reviewed ASR slices")
        fragments = []
        for spec in slices:
            segment_index = int(spec["segment"])
            if not 0 <= segment_index < len(segments):
                raise ValueError(f"turn {expected.id} references missing ASR segment")
            fragments.append({"segment": segment_index, **fragment(segments[segment_index], spec)})
        search_start = max(previous_end, float(item.get("searchStart", float(fragments[0]["start"]) - 0.35)))
        search_end = min(duration, float(item.get("searchEnd", float(fragments[-1]["end"]) + 0.35)))
        if search_start >= search_end:
            raise ValueError(f"turn {expected.id} has an invalid reviewed search range")
        start, end = active_bound(dbfs, step, search_start, search_end)
        if start < previous_end:
            raise ValueError(f"turn {expected.id} overlaps previous turn")
        assessment = item.get("textAssessment", {})
        if assessment.get("status") not in {"confirmed_match", "reviewed_asr_disagreement"} or not assessment.get("evidence"):
            raise ValueError(f"turn {expected.id} lacks explicit machine text review")
        observed = "".join(part["text"] for part in fragments)
        gap = round(start - previous_end, 3)
        review_evidence = (
            f"fresh ASR slices {slices}; -38 dBFS 20 ms RMS/5 ms hop active range "
            f"{start:.3f}-{end:.3f}s; preceding inactive gap {gap:.3f}s; "
            f"speaker identity follows live-UI-verified alternating blocks and is cross-checked by voice evidence"
        )
        if item.get("boundaryReview"):
            review_evidence += f"; boundary-specific review: {item['boundaryReview']}"
        measured.append({
            "id": expected.id,
            "speakerId": expected.speaker_id,
            "scriptText": expected.text,
            "ttsText": expected.tts_text,
            "observedText": observed,
            "asrReferences": slices,
            "textAssessment": assessment,
            "start": start,
            "end": end,
            "review": {"status": "machine_reviewed", "subjectiveListening": False, "evidence": review_evidence},
        })
        waveform.append({
            "id": expected.id,
            "speakerId": expected.speaker_id,
            "asrSlices": slices,
            "asrRange": [fragments[0]["start"], fragments[-1]["end"]],
            "activeRange": [start, end],
            "precedingInactiveGapSeconds": gap,
            "boundaryConfidence": "high" if gap >= 0.35 else "reviewed_contiguous_handoff",
        })
        previous_end = end
    turns_document = {
        "version": 1,
        "audio": args.audio.resolve().relative_to(ROOT).as_posix(),
        "audioSha256": audio_hash,
        "asr": args.asr.resolve().relative_to(ROOT).as_posix(),
        "asrSha256": asr_hash,
        "plan": args.plan.resolve().relative_to(ROOT).as_posix(),
        "planSha256": sha256(args.plan),
        "audioInfo": {"channels": 1, "sampleWidth": 2, "sampleRate": rate, "duration": duration},
        "status": "machine_reviewed_no_subjective_listening",
        "turns": measured,
    }
    waveform_document = {
        "audio": args.audio.resolve().relative_to(ROOT).as_posix(),
        "audioSha256": audio_hash,
        "asrSha256": asr_hash,
        "method": {"thresholdDbfs": THRESHOLD_DBFS, "windowSeconds": WINDOW_SECONDS, "hopSeconds": HOP_SECONDS},
        "note": "Waveform energy supports audio-specific reviewed boundaries. It is not subjective listening evidence.",
        "turns": waveform,
    }
    args.turns_output.write_text(json.dumps(turns_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.waveform_output.write_text(json.dumps(waveform_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.turns_output)
    print(args.waveform_output)


if __name__ == "__main__":
    main()
