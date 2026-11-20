#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path

import numpy as np
import torch
from scipy.signal import resample_poly
from transformers import AutoModelForCTC, AutoProcessor


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("CTC cross-check requires mono 16-bit PCM WAV")
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
        return samples, audio.getframerate()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-check selected adopted-audio spans with an independent Japanese CTC model.")
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--span", action="append", required=True, help="label:start:end")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    processor = AutoProcessor.from_pretrained(str(args.model), local_files_only=True)
    model = AutoModelForCTC.from_pretrained(str(args.model), local_files_only=True)
    model.eval()
    samples, rate = load_audio(args.audio)
    target_rate = int(processor.feature_extractor.sampling_rate)
    results = []
    for raw in args.span:
        label, start_text, end_text = raw.rsplit(":", 2)
        start, end = float(start_text), float(end_text)
        if not 0 <= start < end <= len(samples) / rate:
            raise ValueError(f"invalid CTC span: {raw}")
        part = samples[round(start * rate):round(end * rate)]
        if rate != target_rate:
            part = resample_poly(part, target_rate, rate).astype(np.float32)
        values = processor(part, sampling_rate=target_rate, return_tensors="pt").input_values
        with torch.inference_mode():
            ids = torch.argmax(model(values).logits, dim=-1)
        results.append({"label": label, "start": start, "end": end, "text": processor.batch_decode(ids)[0]})
    document = {
        "audio": str(args.audio),
        "audioSha256": sha256(args.audio),
        "engine": args.model.name,
        "note": "Independent CTC output is supporting machine evidence, not full subjective listening.",
        "segments": results,
    }
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
