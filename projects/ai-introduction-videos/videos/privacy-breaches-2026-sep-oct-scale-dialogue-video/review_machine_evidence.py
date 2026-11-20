#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import wave
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_dbfs(samples: np.ndarray, rate: int, time: float) -> float:
    start = max(0, round((time - 0.015) * rate))
    part = samples[start:start + round(0.04 * rate)]
    if not len(part):
        return -180.0
    rms = math.sqrt(float(np.mean(part * part)))
    return round(20 * math.log10(max(rms, 1e-9)), 2)


def needs_review(card: dict, card_index: int) -> bool:
    if card_index == 0:
        return False
    return (
        card.get("score") is None
        or float(card["score"]) < 0.5
        or str(card.get("text", ""))[:1].isdigit()
        or card.get("mappingStatus") != "exact_first_char"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply explicit, adopted-audio-specific reviews to low-confidence caption boundaries.")
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--alignment", required=True, type=Path)
    parser.add_argument("--reviews", required=True, type=Path)
    args = parser.parse_args()
    alignment = json.loads(args.alignment.read_text(encoding="utf-8"))
    reviews = json.loads(args.reviews.read_text(encoding="utf-8"))
    audio_hash = sha256(args.audio)
    if alignment.get("audioSha256") != audio_hash or reviews.get("audioSha256") != audio_hash:
        raise ValueError("audio hash mismatch invalidates alignment reviews")
    with wave.open(str(args.audio), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("review requires mono 16-bit PCM WAV")
        rate = audio.getframerate()
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    review_map = {(int(item["turnId"]), int(item["cardNumber"])): item for item in reviews.get("reviews", [])}
    required = []
    for utterance in alignment.get("utterances", []):
        cards = utterance.get("cards", [])
        for index, card in enumerate(cards):
            key = (int(utterance["id"]), index + 1)
            if not needs_review(card, index):
                continue
            required.append(key)
            item = review_map.get(key)
            if not item or item.get("status") != "reviewed" or not item.get("evidence"):
                raise ValueError(f"missing explicit low-confidence review for turn {key[0]} card {key[1]}")
            if item.get("subjectiveListening") not in {True, False}:
                raise ValueError(f"turn {key[0]} card {key[1]} must state subjectiveListening")
            chosen = float(item["chosenStart"])
            if index == 0 or not float(utterance["start"]) < chosen < float(utterance["end"]):
                raise ValueError(f"invalid corrected boundary for turn {key[0]} card {key[1]}")
            previous = cards[index - 1]
            if chosen <= float(previous["subtitleStart"]):
                raise ValueError(f"corrected boundary reverses turn {key[0]} card {key[1]}")
            previous["subtitleEnd"] = round(chosen, 3)
            original_predicted = card["predictedStart"]
            card["predictedStart"] = round(chosen, 3)
            card["subtitleStart"] = round(chosen, 3)
            card["manualReview"] = {
                "status": "reviewed",
                "originalPredictedStart": original_predicted,
                "subjectiveListening": item["subjectiveListening"],
                "chosenStart": round(chosen, 3),
                "localWaveformDbfs": local_dbfs(samples, rate, chosen),
                "evidence": item["evidence"],
            }
    unused = sorted(set(review_map) - set(required))
    if unused:
        raise ValueError(f"review file contains boundaries that are not low-confidence: {unused}")
    alignment["lowConfidenceReview"] = {
        "reviewFile": args.reviews.name,
        "reviewFileSha256": sha256(args.reviews),
        "requiredCount": len(required),
        "status": "complete",
    }
    args.alignment.write_text(json.dumps(alignment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.alignment)


if __name__ == "__main__":
    main()
