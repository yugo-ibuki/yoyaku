#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path

import numpy as np


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as audio:
        rate = audio.getframerate()
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    return samples, rate


def pitch_evidence(samples: np.ndarray, rate: int, start: float, end: float) -> dict:
    part = samples[round(start * rate):round(end * rate)]
    frame_size = round(rate * 0.04)
    hop = round(rate * 0.01)
    min_lag, max_lag = round(rate / 400), round(rate / 60)
    pitches = []
    rms_values = []
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
    parser = argparse.ArgumentParser(description="Record reproducible pitch evidence for the alternating generated voices.")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--turns", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    turns = json.loads(args.turns.read_text(encoding="utf-8"))["turns"]
    samples, rate = load_audio(args.audio)
    results = []
    for turn in turns:
        results.append({
            "id": turn["id"],
            "speakerId": turn["speakerId"],
            "start": turn["start"],
            "end": turn["end"],
            **pitch_evidence(samples, rate, float(turn["start"]), float(turn["end"])),
        })
    groups = {}
    for speaker in {turn["speakerId"] for turn in turns}:
        values = [item["medianPitchHz"] for item in results if item["speakerId"] == speaker and item["medianPitchHz"]]
        groups[speaker] = {"turns": len(values), "medianOfTurnMediansHz": round(float(np.median(values)), 1)}
    document = {
        "method": "40 ms autocorrelation frames, 10 ms hop, 60-400 Hz search, normalized peak >= 0.35, RMS >= 0.012",
        "note": "Pitch separation supports alternating voice identity; it does not establish perceived age or gender by itself.",
        "speakers": groups,
        "turns": results,
    }
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
