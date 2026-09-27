import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_timeline", PROJECT / "verify_timeline.py")
verify_timeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(verify_timeline)


def write_wav(path: Path, seconds: float = 2.0) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24_000)
        output.writeframes(b"\0\0" * round(seconds * 24_000))


class VerifyTimelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.audio = self.root / "dialogue.wav"
        write_wav(self.audio)
        audio_hash = hashlib.sha256(self.audio.read_bytes()).hexdigest()
        self.alignment = {
            "audio": "dialogue.wav",
            "audioSha256": audio_hash,
            "utterances": [
                {
                    "id": 1,
                    "speaker": "left",
                    "speakerLabel": "生徒",
                    "start": 0.0,
                    "end": 0.9,
                    "text": "質問です",
                    "cards": [{"text": "質問です", "predictedStart": 0.1, "subtitleStart": 0.0, "subtitleEnd": 0.9}],
                },
                {
                    "id": 2,
                    "speaker": "right",
                    "speakerLabel": "先生",
                    "start": 1.0,
                    "end": 1.9,
                    "text": "答えます",
                    "cards": [{"text": "答えます", "predictedStart": 1.1, "subtitleStart": 1.0, "subtitleEnd": 1.9}],
                },
            ],
        }
        self.metadata = {
            "audio": "dialogue.wav",
            "timingBasis": {"alignmentFile": "dialogue_alignment.json"},
            "utterances": [
                {
                    "id": 1,
                    "speaker": "left",
                    "speakerLabel": "生徒",
                    "start": 0.0,
                    "end": 0.9,
                    "text": "質問です",
                    "subtitleUnits": [{"text": "質問です", "start": 0.0, "end": 0.9, "alignmentEvidence": {"predictedStart": 0.1}}],
                },
                {
                    "id": 2,
                    "speaker": "right",
                    "speakerLabel": "先生",
                    "start": 1.0,
                    "end": 1.9,
                    "text": "答えます",
                    "subtitleUnits": [{"text": "答えます", "start": 1.0, "end": 1.9, "alignmentEvidence": {"predictedStart": 1.1}}],
                },
            ],
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def validate(self, alignment=None, metadata=None):
        return verify_timeline.validate(
            self.audio,
            alignment or self.alignment,
            metadata or self.metadata,
            expected_turns=2,
            expected_cards=2,
            expected_speakers={"left": 1, "right": 1},
        )

    def test_accepts_contiguous_subtitles_tied_to_audio_hash(self):
        self.assertEqual(self.validate()["cards"], 2)

    def test_rejects_audio_regenerated_without_realignment(self):
        changed = copy.deepcopy(self.alignment)
        changed["audioSha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "audio hash"):
            self.validate(alignment=changed)

    def test_rejects_card_gap(self):
        alignment = copy.deepcopy(self.alignment)
        metadata = copy.deepcopy(self.metadata)
        for document, key in ((alignment, "cards"), (metadata, "subtitleUnits")):
            document["utterances"][0]["text"] = "質問をします"
            document["utterances"][0][key] = [
                {"text": "質問", "predictedStart": 0.1, "subtitleStart": 0.0, "subtitleEnd": 0.4} if key == "cards" else {"text": "質問", "start": 0.0, "end": 0.4, "alignmentEvidence": {"predictedStart": 0.1}},
                {"text": "をします", "predictedStart": 0.6, "subtitleStart": 0.6, "subtitleEnd": 0.9} if key == "cards" else {"text": "をします", "start": 0.6, "end": 0.9, "alignmentEvidence": {"predictedStart": 0.6}},
            ]
        with self.assertRaisesRegex(ValueError, "gap or overlap"):
            self.validate(alignment=alignment, metadata=metadata)

    def test_rejects_transcript_or_speaker_drift(self):
        metadata = copy.deepcopy(self.metadata)
        metadata["utterances"][1]["speaker"] = "left"
        with self.assertRaisesRegex(ValueError, "speaker mismatch"):
            self.validate(metadata=metadata)

    def test_rejects_caption_start_detached_from_alignment(self):
        alignment = copy.deepcopy(self.alignment)
        metadata = copy.deepcopy(self.metadata)
        for document, key in ((alignment, "cards"), (metadata, "subtitleUnits")):
            document["utterances"][1]["text"] = "答えを話します"
            document["utterances"][1][key] = [
                {"text": "答えを", "predictedStart": 1.1, "subtitleStart": 1.0, "subtitleEnd": 1.5} if key == "cards" else {"text": "答えを", "start": 1.0, "end": 1.6, "alignmentEvidence": {"predictedStart": 1.1}},
                {"text": "話します", "predictedStart": 1.5, "subtitleStart": 1.5, "subtitleEnd": 1.9} if key == "cards" else {"text": "話します", "start": 1.6, "end": 1.9, "alignmentEvidence": {"predictedStart": 1.5}},
            ]
        with self.assertRaisesRegex(ValueError, "forced alignment"):
            self.validate(alignment=alignment, metadata=metadata)

    def test_rejects_absolute_personal_paths(self):
        alignment = copy.deepcopy(self.alignment)
        alignment["audio"] = "/Users/example/private/dialogue.wav"
        with self.assertRaisesRegex(ValueError, "portable relative path"):
            self.validate(alignment=alignment)

    def test_rejects_low_confidence_boundary_without_manual_review(self):
        alignment = copy.deepcopy(self.alignment)
        alignment["utterances"][1]["cards"][0]["score"] = 0.1
        with self.assertRaisesRegex(ValueError, "manual review"):
            self.validate(alignment=alignment)


if __name__ == "__main__":
    unittest.main()
