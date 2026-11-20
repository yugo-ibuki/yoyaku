#!/usr/bin/env python3
"""Create static layout samples without pretending to know speech timings."""
from pathlib import Path
import json
from PIL import ImageFont
from dialogue import LEFT, RIGHT, TURNS
from render import DEFAULT_ASSETS, DEFAULT_CONFIG, DEFAULT_FONT, draw_subtitle, draw_context, load_render_config, prepare_frames, sha256, validate_subtitle_width
from numeric_overlays import draw_hero, state_for_card

ROOT=Path(__file__).resolve().parent


def main() -> None:
    config=load_render_config(DEFAULT_CONFIG);frames=prepare_frames(DEFAULT_ASSETS,config)
    validate_subtitle_width(DEFAULT_FONT);font=ImageFont.truetype(str(DEFAULT_FONT),30)
    output=ROOT/'qa/initial-samples';output.mkdir(parents=True,exist_ok=True)
    samples=[('base-frame.png',None,None),('left-speaking-frame.png',1,1),('right-speaking-frame.png',2,3),
             ('hero-mail-frame.png',4,1),('hero-members-frame.png',4,3),('hero-travel-frame.png',4,5),
             ('hero-comparison-frame.png',6,1),('cta-frame.png',8,1),('cta-links-frame.png',8,5)]
    manifest=[]
    for name,turn_id,card_number in samples:
        turn=None if turn_id is None else next(t for t in TURNS if t.id==turn_id)
        frame=frames['base' if turn is None else turn.speaker_id].copy()
        if turn is not None:
            card=turn.cards[card_number-1]
            draw_hero(frame,state_for_card(turn_id,card_number),DEFAULT_FONT)
            draw_subtitle(frame,({'speakerId':turn.speaker_id,'speakerLabel':''},{'text':card.replace('|',''),'lines':card.split('|')}),font)
        draw_context(frame,turn_id,DEFAULT_FONT);path=output/name;frame.save(path)
        manifest.append({'file':name,'sha256':sha256(path),'turnId':turn_id,'cardNumber':card_number})
    (output/'manifest.json').write_text(json.dumps({'status':'static_layout_samples_no_audio_timing','renderConfigSha256':sha256(DEFAULT_CONFIG),'canonicalScriptSha256':sha256(ROOT/'turns.json'),'frames':manifest},ensure_ascii=False,indent=2)+'\n')
    print(output/'manifest.json')


if __name__=='__main__':
    main()
