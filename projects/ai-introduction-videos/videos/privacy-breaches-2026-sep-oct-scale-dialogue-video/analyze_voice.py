#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("voice analysis requires mono 16-bit PCM WAV")
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
        return samples, audio.getframerate()


def evidence(samples: np.ndarray, rate: int, start: float, end: float) -> dict:
    part = samples[round(start * rate):round(end * rate)]
    frame_size, hop = round(rate * 0.04), round(rate * 0.01)
    min_lag, max_lag = round(rate / 400), round(rate / 60)
    pitches, rms_values = [], []
    for offset in range(0, max(0, len(part) - frame_size), hop):
        frame = part[offset:offset + frame_size]
        rms = float(np.sqrt(np.mean(frame * frame)))
        rms_values.append(rms)
        if rms < 0.012:
            continue
        centered = (frame - frame.mean()) * np.hanning(frame_size)
        corr = np.correlate(centered, centered, mode="full")[frame_size - 1:]
        if corr[0] <= 1e-9:
            continue
        region = corr[min_lag:max_lag + 1] / corr[0]
        lag = min_lag + int(np.argmax(region))
        if float(region[lag - min_lag]) >= 0.35:
            pitches.append(rate / lag)
    return {
        "medianPitchHz": None if not pitches else round(float(np.median(pitches)), 1),
        "pitchP25Hz": None if not pitches else round(float(np.percentile(pitches, 25)), 1),
        "pitchP75Hz": None if not pitches else round(float(np.percentile(pitches, 75)), 1),
        "voicedFrames": len(pitches),
        "medianRms": round(float(np.median(rms_values)), 5) if rms_values else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Record reproducible pitch and RMS evidence for each reviewed turn.")
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--turns", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    document = json.loads(args.turns.read_text(encoding="utf-8"))
    if document.get("audioSha256") != sha256(args.audio):
        raise ValueError("voice evidence audio hash mismatch")
    turns = document["turns"]
    samples, rate = load_audio(args.audio)
    results = [
        {"id": turn["id"], "speakerId": turn["speakerId"], "start": turn["start"], "end": turn["end"], **evidence(samples, rate, float(turn["start"]), float(turn["end"]))}
        for turn in turns
    ]
    groups = {}
    for speaker in sorted({turn["speakerId"] for turn in turns}):
        values = [item["medianPitchHz"] for item in results if item["speakerId"] == speaker and item["medianPitchHz"]]
        groups[speaker] = {"turns": len(values), "medianOfTurnMediansHz": None if not values else round(float(np.median(values)), 1)}
    output = {
        "audio": str(args.audio),
        "audioSha256": sha256(args.audio),
        "method": "40 ms autocorrelation frames, 10 ms hop, 60-400 Hz, normalized peak >= 0.35, RMS >= 0.012",
        "note": "Pitch separation supports alternating voice identity but does not prove perceived age, gender, or subjective quality.",
        "speakers": groups,
        "turns": results,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
