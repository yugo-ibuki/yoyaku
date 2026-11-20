#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path

import numpy as np
import torch
from scipy.signal import resample_poly
from transformers import AutoModelForCTC, AutoProcessor


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as audio:
        rate = audio.getframerate()
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    return samples, rate


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-check selected audio spans with an independent Japanese CTC ASR model.")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--span", action="append", required=True, help="label:start:end")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    processor = AutoProcessor.from_pretrained(str(args.model), local_files_only=True)
    model = AutoModelForCTC.from_pretrained(str(args.model), local_files_only=True)
    model.eval()
    samples, rate = load_audio(args.audio)
    target_rate = int(processor.feature_extractor.sampling_rate)
    results = []
    for raw in args.span:
        label, start_text, end_text = raw.split(":")
        start, end = float(start_text), float(end_text)
        part = samples[round(start * rate):round(end * rate)]
        if rate != target_rate:
            part = resample_poly(part, target_rate, rate).astype(np.float32)
        values = processor(part, sampling_rate=target_rate, return_tensors="pt").input_values
        with torch.inference_mode():
            ids = torch.argmax(model(values).logits, dim=-1)
        results.append({"label": label, "start": start, "end": end, "text": processor.batch_decode(ids)[0]})
    args.output.write_text(json.dumps({"engine": args.model.name, "segments": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
