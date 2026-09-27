import copy
import hashlib
import json
import re
import tempfile
import unittest
import wave
from pathlib import Path

from PIL import Image

import align_dialogue
import dialogue
import render
import verify_timeline


PROJECT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT.parent / "assets" / "dining-room"


def write_wav(path: Path, seconds: float = 2.0) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24_000)
        output.writeframes(b"\0\0" * round(seconds * 24_000))


class StaticProjectTests(unittest.TestCase):
    def test_script_is_16_alternating_caption_safe_turns(self):
        dialogue.validate_script()
        self.assertEqual(len(dialogue.TURNS), 16)
        self.assertEqual(sum(len(turn.cards) for turn in dialogue.TURNS), 38)

    def test_readable_dialogue_matches_canonical_script(self):
        markdown = (PROJECT / "DIALOGUE.md").read_text(encoding="utf-8")
        displayed = re.findall(r"^\d+\. `[^`]+`（(?:生徒|先生)）: (.+)$", markdown, re.MULTILINE)
        self.assertEqual(displayed, [turn.text for turn in dialogue.TURNS])

    def test_dining_images_keep_original_dimensions(self):
        for name in ("base.png", "left-speaking.png", "right-speaking.png"):
            with Image.open(ASSETS / name) as image:
                self.assertEqual(image.size, (941, 1672))

    def test_renderer_loads_completed_speaker_poses(self):
        left, right, base = render.load_poses(ASSETS)
        self.assertEqual((left.size, right.size, base.size), ((720, 1280), (720, 1280), (720, 1280)))

    def test_every_subtitle_line_fits_inside_600_pixels(self):
        widest = render.validate_subtitle_width(render.DEFAULT_FONT)
        self.assertLessEqual(widest["width"], 600)


class TimelineGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.audio = self.root / "audio.wav"
        write_wav(self.audio)
        self.audio_hash = hashlib.sha256(self.audio.read_bytes()).hexdigest()
        self.verified = {
            "audioSha256": self.audio_hash,
            "turns": [
                {
                    "id": turn.id,
                    "speakerId": turn.speaker_id,
                    "scriptText": turn.text,
                    "asrText": turn.text,
                    "textAssessment": {"status": "machine_compatible", "evidence": "test fixture"},
                    "start": index * 0.1,
                    "end": index * 0.1 + 0.08,
                    "review": {"status": "machine_reviewed", "subjectiveListening": False, "evidence": "test fixture"},
                }
                for index, turn in enumerate(dialogue.TURNS)
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_verified_turns_require_matching_audio_hash(self):
        changed = copy.deepcopy(self.verified)
        changed["audioSha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "audio hash"):
            align_dialogue.validate_verified_turns(self.audio, changed)

    def test_verified_turns_require_script_identity(self):
        changed = copy.deepcopy(self.verified)
        changed["turns"][3]["scriptText"] += "違い"
        with self.assertRaisesRegex(ValueError, "confirmed script"):
            align_dialogue.validate_verified_turns(self.audio, changed)

    def test_verified_turns_require_review_evidence(self):
        changed = copy.deepcopy(self.verified)
        changed["turns"][5]["review"] = {"status": "pending", "subjectiveListening": False, "evidence": ""}
        with self.assertRaisesRegex(ValueError, "review evidence"):
            align_dialogue.validate_verified_turns(self.audio, changed)

    def test_verified_turns_reject_unmeasured_placeholder(self):
        changed = copy.deepcopy(self.verified)
        changed["turns"][0]["start"] = None
        changed["turns"][0]["end"] = None
        with self.assertRaisesRegex(ValueError, "must be measured from the final audio"):
            align_dialogue.validate_verified_turns(self.audio, changed)

    def test_metadata_rejects_regenerated_audio(self):
        alignment = {"audioSha256": "0" * 64, "utterances": []}
        path = self.root / "alignment.json"
        path.write_text(json.dumps(alignment), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "audio hash"):
            render.build_metadata(self.audio, path)

    def test_complete_measured_timeline_passes_verifier(self):
        aligned_turns = []
        metadata_turns = []
        for index, turn in enumerate(dialogue.TURNS):
            start, end = index * 0.1, index * 0.1 + 0.08
            step = (end - start) / len(turn.cards)
            cards = []
            units = []
            for card_index, marked in enumerate(turn.cards):
                text = marked.replace("|", "")
                card_start = start + step * card_index
                card_end = start + step * (card_index + 1)
                predicted = card_start if card_index else start + 0.001
                cards.append({
                    "text": text,
                    "lines": marked.split("|"),
                    "predictedStart": predicted,
                    "subtitleStart": card_start,
                    "subtitleEnd": card_end,
                    "mappingStatus": "exact_first_char",
                    "score": 1.0,
                })
                units.append({
                    "text": text,
                    "lines": marked.split("|"),
                    "start": card_start,
                    "end": card_end,
                    "alignmentEvidence": {"predictedStart": predicted},
                })
            common = {
                "id": turn.id,
                "speakerId": turn.speaker_id,
                "speakerLabel": turn.speaker_label,
                "start": start,
                "end": end,
                "text": turn.text,
            }
            aligned_turns.append({**common, "cards": cards})
            metadata_turns.append({**common, "subtitleUnits": units})
        alignment = {"audio": "audio.wav", "audioSha256": self.audio_hash, "utterances": aligned_turns}
        metadata = {
            "audio": "audio.wav",
            "audioSha256": self.audio_hash,
            "timingBasis": {"alignmentFile": "dialogue_alignment.json"},
            "utterances": metadata_turns,
        }
        result = verify_timeline.validate(self.audio, alignment, metadata)
        self.assertEqual((result["turns"], result["cards"]), (16, 38))


if __name__ == "__main__":
    unittest.main()
