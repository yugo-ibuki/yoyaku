import importlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

class ProjectTests(unittest.TestCase):
    def test_pipeline_preserves_script_and_listener_pixels(self):
        self.assertTrue((PROJECT / 'render.py').exists(), 'self-contained renderer is required')
        dialogue = importlib.import_module('dialogue')
        render = importlib.import_module('render')
        doc = json.loads((PROJECT / 'turns.json').read_text())
        dialogue.validate_script()
        self.assertEqual([t.text for t in dialogue.TURNS], [t['text'] for t in doc['turns']])
        self.assertEqual([t.speaker_id for t in dialogue.TURNS], [['left_student', 'right_teacher'][i % 2] for i in range(len(doc['turns']))])
        self.assertTrue(all(not t.speaker_label for t in dialogue.TURNS))
        for turn in dialogue.TURNS:
            self.assertEqual(dialogue.display_prefix_to_tts(turn, turn.text)[0], turn.tts_text)
            self.assertEqual(render.source_footer(turn.id), ('出典：' + ' ／ '.join(render.SOURCE_LABELS[s] for s in turn.source_ids)) if turn.source_ids else '')
        render.validate_subtitle_width(render.DEFAULT_FONT)
        config = render.load_render_config(render.DEFAULT_CONFIG)
        frames = render.prepare_frames(render.DEFAULT_ASSETS, config)
        base = np.array(frames['base'])
        for speaker in (dialogue.LEFT, dialogue.RIGHT):
            actual = np.array(frames[speaker])
            x0,y0,x1,y1 = render.scaled_box(config['mouthRegions'][speaker]['box'])
            allowed = np.zeros(base.shape[:2], dtype=bool)
            allowed[y0-16:y1+16, x0-16:x1+16] = True
            self.assertTrue(np.any(actual != base), 'speaking mouth must visibly change')
            self.assertTrue(np.array_equal(actual[~allowed], base[~allowed]), 'listener/background must remain fixed')

    def test_municipality_names_are_rejected(self):
        guard = importlib.import_module("privacy_guard")
        for value in ("大阪市", "おおさかし", "Osaka", "https://www.city.osaka.lg.jp/x"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "company name"):
                    guard.assert_company_names_absent({"text": value}, "public captions")

    def test_qa_coverage_tracks_every_canonical_card_and_handoff(self):
        # Synthetic in-memory fixture only; never saved or used as audio timing.
        dialogue = importlib.import_module("dialogue")
        qa = importlib.import_module("extract_qa_frames")
        from collections import Counter
        fixture = {"utterances": [
            {"id": turn.id, "speakerId": turn.speaker_id, "start": index * 2 + 0.2,
             "end": index * 2 + 1.8, "mouthMotion": {"peakTime": index * 2 + 1},
             "subtitleUnits": [{"start": index * 2 + 0.3, "end": index * 2 + 1.7,
                                "text": card.replace("|", "")} for card in turn.cards]}
            for index, turn in enumerate(dialogue.TURNS)]}
        counts = Counter(item["kind"] for item in qa.samples(fixture, len(dialogue.TURNS) * 2))
        self.assertEqual(counts["subtitle-card"], sum(len(t.cards) for t in dialogue.TURNS))
        self.assertEqual(counts["handoff-before"], len(dialogue.TURNS) - 1)
        self.assertEqual(counts["handoff-after"], len(dialogue.TURNS) - 1)
        self.assertEqual(counts["speaker-peak"], len(dialogue.TURNS))
        self.assertEqual(counts["endpoint"], 2)

    def test_approved_script_and_prepared_tts_match_current_input(self):
        import hashlib
        dialogue = importlib.import_module("dialogue")
        approval = json.loads((PROJECT / "script-approval.json").read_text())
        self.assertTrue(approval["approved"])
        render=importlib.import_module("render")
        import tempfile
        with tempfile.TemporaryDirectory(dir=PROJECT) as tmp:
            path=Path(tmp)/"approval.json";wrong=dict(approval);wrong["approved"]=False
            path.write_text(json.dumps(wrong))
            with self.assertRaisesRegex(ValueError,"approved"):
                render.validate_approval(path)
        self.assertEqual(approval["canonicalScriptSha256"], hashlib.sha256((PROJECT / "turns.json").read_bytes()).hexdigest())
        studio = json.loads((PROJECT / "audio/studio-input.json").read_text())
        self.assertEqual([t["ttsText"] for t in studio["ttsTurns"]], [t.tts_text for t in dialogue.TURNS])
        self.assertFalse(studio["fillerEnabled"])
        for turn in dialogue.TURNS:
            self.assertNotIn("企業名を出さず",turn.tts_text)
            self.assertNotIn("まとめた一覧",turn.tts_text)
        self.assertEqual(studio["speechSettings"]["relativeTempoTarget"], 1.1)

    def test_numeric_heroes_follow_caption_boundaries(self):
        self.assertTrue((PROJECT / "numeric_overlays.py").exists(), "caption-linked numeric overlays required")
        overlays = importlib.import_module("numeric_overlays")
        dialogue = importlib.import_module("dialogue")
        # Deliberately nonuniform synthetic fixture, never saved as audio timing.
        turns=[]; cursor=0.3
        for turn in dialogue.TURNS:
            units=[]
            for index,card in enumerate(turn.cards):
                end=cursor+0.17+index*0.09
                units.append({"start":cursor,"end":end,"text":card.replace("|","")});cursor=end
            turns.append({"id":turn.id,"subtitleUnits":units});cursor+=0.21
        timeline=overlays.build_timeline(turns)
        self.assertEqual([x["stateId"] for x in timeline], ["listing","mail","members","travel","comparison"])
        for unit in timeline:
            turn=next(x for x in turns if x["id"]==unit["turnId"])
            self.assertEqual(unit["start"],turn["subtitleUnits"][unit["firstCard"]-1]["start"])
            self.assertEqual(unit["end"],turn["subtitleUnits"][unit["lastCard"]-1]["end"])
        self.assertIsNone(overlays.state_for_card(1,1))
        self.assertIsNone(overlays.state_for_card(8,1))
        self.assertEqual(overlays.state_for_card(4,1)["number"],"延べ約5,163万件")
        self.assertEqual(overlays.state_for_card(4,3)["qualifier"],"流出の可能性")
        self.assertEqual(overlays.state_for_card(4,5)["number"],"最大約445万人")
        self.assertEqual(overlays.state_for_card(2,3)["number"],"1,654件")

    def test_numeric_panel_leaves_faces_and_subtitles_clear(self):
        self.assertTrue((PROJECT / "numeric_overlays.py").exists(), "safe numeric panel required")
        overlays=importlib.import_module("numeric_overlays")
        render=importlib.import_module("render")
        from PIL import Image, ImageChops
        for state in overlays.STATES:
            blank=Image.new("RGB",(1280,720),(80,90,100));actual=blank.copy()
            overlays.draw_hero(actual,state,render.DEFAULT_FONT)
            x0,y0,x1,y1=ImageChops.difference(blank,actual).getbbox()
            self.assertGreaterEqual(y0,385)
            self.assertLessEqual(y1,535)
            self.assertLess(y1,572)
            self.assertTrue(np.array_equal(np.array(actual)[:360],np.array(blank)[:360]))
            for item in overlays.layout(state,render.DEFAULT_FONT):
                a,b,c,d=item["bbox"]
                self.assertGreaterEqual(a,overlays.PANEL[0]);self.assertLessEqual(c,overlays.PANEL[2])
                self.assertGreaterEqual(b,overlays.PANEL[1]);self.assertLessEqual(d,overlays.PANEL[3])

    def test_numeric_caption_onsets_require_review_even_with_high_ctc_score(self):
        review = importlib.import_module("review_machine_evidence")
        self.assertTrue(review.needs_review({"text":"617名の氏名", "score":0.937, "mappingStatus":"exact_first_char"}, 3))

    def test_company_names_are_absent_from_public_inputs_and_rejected_on_regression(self):
        self.assertTrue((PROJECT / "privacy_guard.py").exists(), "public-output privacy guard is required")
        guard = importlib.import_module("privacy_guard")
        dialogue = importlib.import_module("dialogue")
        render = importlib.import_module("render")
        from dataclasses import asdict
        payload = {"script": dialogue.SCRIPT,
                   "turns": [{**asdict(t), "text": t.text} for t in dialogue.TURNS],
                   "sourceLabels": render.SOURCE_LABELS,
                   "footers": [render.source_footer(t.id) for t in dialogue.TURNS],
                   "embeddedMetadata": render.VIDEO_TAGS}
        guard.assert_company_names_absent(payload, "public inputs")
        for forbidden in ["ココナラ", "ここなら", "ＣＯＣＯＮＡＬＡ", "https://coconala.co.jp/x", "ソースネクスト", "そーすねくすと", "Source Next", "https://www.sourcenext.com/x", "ソニー銀行", "そにー", "Sony", "https://sonybank.jp/x", "ユミルリンク", "Cuenote", "手間いらず", "TEMAIRAZU", "ClipMaster", "クリップマスター"]:
            with self.subTest(forbidden=forbidden):
                with self.assertRaisesRegex(ValueError, "company name"):
                    guard.assert_company_names_absent({"utterances": [{"text": forbidden}]}, "render metadata")

    def test_embedded_mp4_metadata_is_checked_from_the_container(self):
        import subprocess
        import tempfile
        render = importlib.import_module("render")
        verify = importlib.import_module("verify_timeline")
        with tempfile.TemporaryDirectory(dir=PROJECT) as tmp:
            video = Path(tmp) / "metadata.mp4"
            command = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=size=1280x720:rate=24",
                       "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.25", "-c:v", "libx264", "-preset", "ultrafast",
                       "-c:a", "aac", "-map_metadata", "-1"]
            for key, value in render.VIDEO_TAGS.items():
                command += ["-metadata", f"{key}={value}"]
            subprocess.run(command + [str(video)], check=True)
            self.assertEqual(verify.probe_video(video, 0.25)["video"], "h264")
            subprocess.run(command + ["-metadata", "title=Sony", str(video)], check=True)
            with self.assertRaisesRegex(ValueError, "company name"):
                verify.probe_video(video, 0.25)

    def test_modified_assets_and_stale_audio_fail_closed(self):
        self.assertTrue((PROJECT / 'render.py').exists(), 'self-contained renderer is required')
        render = importlib.import_module('render')
        config = render.load_render_config(render.DEFAULT_CONFIG)
        config['expectedAssets']['base.png'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'asset hash mismatch'):
            render.load_assets(render.DEFAULT_ASSETS, config)
        import tempfile
        with tempfile.TemporaryDirectory(dir=PROJECT) as tmp:
            root=Path(tmp)
            audio=root/'audio.wav'; audio.write_bytes(b'new audio')
            alignment=root/'alignment.json'
            alignment.write_text(json.dumps({'audioSha256':'0'*64}))
            with self.assertRaisesRegex(ValueError, 'audio hash mismatch'):
                render.build_metadata(audio, alignment, render.DEFAULT_ASSETS, render.DEFAULT_CONFIG)
            import wave, hashlib
            dialogue=importlib.import_module("dialogue")
            with wave.open(str(audio),"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000)
                wav.writeframes(b"\0" * (121 * 24000 * 2))
            alignment.write_text(json.dumps({"audioSha256":hashlib.sha256(audio.read_bytes()).hexdigest(),
                                             "utterances":[{} for _ in dialogue.TURNS]}))
            with self.assertRaisesRegex(ValueError,"duration limit"):
                render.build_metadata(audio, alignment, render.DEFAULT_ASSETS, render.DEFAULT_CONFIG)

if __name__ == '__main__':
    unittest.main()
