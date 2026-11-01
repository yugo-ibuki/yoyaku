---
name: create-animal-dialogue-video
description: Use when creating or adapting a dialogue video whose visible speakers are animals, including variations in species, cast size, roles, scene, style, voices, subtitles, and source materials.
---

# Create Animal Dialogue Video

## Overview

Create a reproducible animal dialogue video from an explicit brief instead of inheriting the cast, layout, timing, or voices from an earlier example. Preserve the identity and composition of user-provided characters, then use the final audio as the timing source of truth.

## Define the brief

Before generating assets, resolve or leave visibly unknown these inputs:

- purpose, aspect ratio, resolution, frame rate, target duration, visual style, camera behavior
- species and number of characters; each character's identity, markings, clothing, role, screen position, and visible subtitle label
- each character's voice direction, speaking expression, mouth/beak motion, listening expression, and allowed body motion
- background, lighting, props, composition, caption-safe area, and unwanted elements
- script, pronunciation notes, final or provisional audio, subtitle rules, and any source image/video

Do not invent missing details that would materially change character identity, composition, or dialogue. Voice direction such as age, gender presentation, pitch, or texture is production metadata. The visible subtitle label must use the user-approved name or role, such as `司書` or `利用者`; never expose voice metadata as a label.

If source media is provided, retain the same character identity, markings, wardrobe, relative positions, and overall composition unless the user requests a change. Record intentional deviations.

Use [references/prompt-templates-ja.md](references/prompt-templates-ja.md) for copy-ready Japanese intake, still-image, and completed-video prompts. Fill every bracket that affects output; keep unresolved brackets explicit instead of guessing.

For the teacher-and-student cat series under `projects/ai-introduction-videos/` only, apply the shared speech settings with [`prepare_speech_input.py`](../../../projects/ai-introduction-videos/prepare_speech_input.py) and [`settings/speech.json`](../../../projects/ai-introduction-videos/settings/speech.json) before using AI Studio. Keep each other animal or role on its own brief, and prefer an explicit per-project pace request over the shared teacher setting.

## Keep the dialogue concise

Follow an explicit user-specified duration first. Otherwise, aim to finish within 2 minutes by focusing on the key points. Allow up to 3 minutes only when essential content would be inadequately explained within 2 minutes, and record that reason in the production notes; do not make 3 minutes the usual target.

For explanatory dialogue, make a short runtime carry a clear, substantial explanation. According to the topic, retain key numbers or scale, concrete examples, what they mean, and necessary actions or precautions. Cut repetition and long preambles while preserving core information and previously required practical advice. Use a clear progression, helpful comparisons, and natural character reactions, including subjective impressions when they aid understanding. Listing numbers or terms, or rushing delivery, does not create substance. Select these elements for the topic; do not require numbers, advice, or jokes in every turn or impose them on fiction.

Before generating audio, review repetition, the number of examples, and explanatory detail to leave room for natural delivery. After generation, measure the actual audio and final MP4 durations. If the applicable limit is exceeded, shorten the content under the script-approval stage below and create a shorter adopted audio through clean sentence-boundary edits or regeneration as appropriate. Keep delivery natural and sentences complete. Continue deriving subtitle and mouth-motion timing from the adopted audio.

## Write dialogue with light humor

When drafting an explanatory dialogue, add a little natural humor that fits the characters and scene: a playful everyday analogy, a small misunderstanding followed by a witty reply, or an animal-specific reaction. Let the humor help the viewer understand the topic, while keeping source facts, limitations, and availability accurate; make invented examples recognizable as examples.

Use humor sparingly. Do not force a joke into every turn, repeat animal catchphrases, or interrupt the explanation with unrelated gags. Respect a user's requested tone and supplied script. Apply this guidance when writing or revising a script; do not rewrite an already confirmed script or regenerate in-progress audio solely to add humor.

## Stages and required script approval

1. **Research and draft:** For source-based explanations, record reference URLs, publication dates, adopted facts, confirmed findings versus possibilities, and their mapping to dialogue lines. For incident roundups, explain the selection scope; the number of examples introduced is not the total number of cases in the period. Present the full script, its sources when applicable, and estimated duration to the user before production. Keep production constraints such as “企業名を出さずに” in production notes rather than spoken dialogue.
2. **Await the user's confirmation:** Explicit confirmation of that presented script version is required. Until it arrives, continue only research, script revision, and reading existing materials; do not generate TTS, edit audio, generate new images, or render video. Approval of another version, a general request to generate a video, and silence are not approval of this script. Record the approved script path and SHA-256 or version, confirmation time, reply summary, and evidence in the run record.
3. **Lock and produce:** After confirmation, freeze the approved script and proceed to audio, synchronization, video, and validation. Changes to dialogue meaning or structure, including shortening or reordering, must be presented again for confirmation before production resumes. Pronunciation-only spelling adjustments may proceed when meaning is unchanged; record both forms and the reason.

## Production workflow

1. Save or identify the source brief, script, reference media, and permissions. Distinguish user-provided, generated, transformed, and final files.
2. Create a character and scene specification from the brief. Use a stable character ID separate from the visible role label.
3. After the script-approval stage, generate or select the base visual. Confirm character count, identity, positions, unobstructed mouths/beaks, composition, style, aspect ratio, and subtitle-safe area before animating.
4. Produce one final audio track from the user-approved script and voice assignments. If the audio changes, invalidate all derived timing.
5. **REQUIRED SUB-SKILL:** Use `sync-dialogue-video` to establish speaker turns from actual audio, force-align confirmed text, drive subtitles and mouth motion from the verified timeline, and validate the final MP4.
6. Render expressions and mouth/beak states for each species without changing character identity. During a turn, animate only the verified speaker's speech mechanism; listeners may blink, breathe, shift gaze, or react subtly.
7. Package the final video with the exact final audio, script, character/scene specification, timing evidence, source or generation prompts, tool/model settings when known, and a provenance manifest.

Never derive timing from character count, text length, equal spacing, a requested total duration, or uniform blocks. A target duration is a planning constraint; measured final audio determines the actual timeline.

## Adapt examples safely

An existing project may demonstrate a pipeline, but its constants are not defaults. Reconfigure character count, species, positions, image assets, voice assignments, duration, script, timeline, canvas, frame rate, and validation thresholds for the current brief.

`projects/ai-introduction-videos/videos/fractal-engineering-dialogue-video/` is a two-cat, 16-turn reproduction example with project-specific assets and values. Treat its `render.py` as an example renderer, not a generic animal-video generator.

## Completion gate

Report these as separate states:

- user confirmation recorded for the adopted script version and presented source mapping
- base image selected or generated and visually checked
- final audio created and hashed
- script and speaker mapping confirmed
- alignment and low-confidence boundaries reviewed
- subtitles and mouth/beak motion rendered from the same verified turns
- final video streams, duration, handoffs, captions, and inactive listeners checked
- reproduction inputs and provenance saved

An exported file is not proof of synchronization. Do not claim publication, upload, commit, push, or replacement of source media unless that action was requested and verified.
