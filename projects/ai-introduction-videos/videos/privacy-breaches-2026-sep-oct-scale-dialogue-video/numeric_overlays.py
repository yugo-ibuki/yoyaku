"""Large numeric panels driven only by verified subtitle-card boundaries."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont

PANEL = (80, 385, 1200, 535)
STATES = (
    {'stateId':'listing','turnId':2,'cards':(1,2,3),'label':'9〜10月の関連事案','number':'1,654件','qualifier':'公表・掲載事案数／漏洩のおそれ等を含む','sourceValue':1654,'unit':'件'},
    {'stateId':'mail','turnId':4,'cards':(1,),'label':'メール配信','number':'延べ約5,163万件','qualifier':'','sourceValue':51628280,'unit':'延べ件'},
    {'stateId':'members','turnId':4,'cards':(2,3),'label':'会員情報','number':'約2,252万件','qualifier':'流出の可能性','sourceValue':22519960,'unit':'件'},
    {'stateId':'travel','turnId':4,'cards':(4,5),'label':'宿泊予約','number':'最大約445万人','qualifier':'閲覧・取得の可能性','sourceValue':4450000,'unit':'最大人数'},
    {'stateId':'comparison','turnId':6,'cards':(1,2),'label':'規模の実感','number':'5,163万件','qualifier':'1秒に1件でも1年以上','sourceValue':51630000,'unit':'件'},
)


def state_for_card(turn_id: int, card_number: int) -> dict[str, Any] | None:
    return next((deepcopy(s) for s in STATES if s['turnId']==turn_id and card_number in s['cards']),None)


def build_timeline(utterances: list[dict]) -> list[dict]:
    result=[]
    for turn in utterances:
        for index,card in enumerate(turn['subtitleUnits'],1):
            state=state_for_card(turn['id'],index)
            if state is None:
                continue
            start,end=float(card['start']),float(card['end'])
            if start>=end:
                raise ValueError('numeric overlay requires measured nonempty subtitle interval')
            if result and result[-1]['stateId']==state['stateId'] and result[-1]['turnId']==turn['id']:
                if abs(result[-1]['end']-start)>.002:
                    raise ValueError('numeric overlay subtitle coverage has a gap')
                result[-1].update(end=end,lastCard=index)
            else:
                result.append({k:v for k,v in state.items() if k!='cards'} | {'start':start,'end':end,'firstCard':index,'lastCard':index})
    return result


def overlay_at(metadata: dict, time: float) -> dict | None:
    return next((s for s in metadata.get('numericOverlays',[]) if s['start']<=time<s['end']),None)


def layout(state: dict, font_path: Path) -> list[dict]:
    draw=ImageDraw.Draw(Image.new('RGB',(1280,720)))
    number_size=88
    while number_size>=72:
        number_font=ImageFont.truetype(str(font_path),number_size)
        if draw.textlength(state['number'],font=number_font)<=PANEL[2]-PANEL[0]-40:
            break
        number_size-=2
    if number_size<72:
        raise ValueError('numeric value does not fit at readable hero size')
    result=[]
    for text,size,y in [(state['label'],20,391),(state['number'],number_size,415),(state['qualifier'],18,510)]:
        if not text:
            continue
        font=ImageFont.truetype(str(font_path),size)
        box=draw.textbbox((640,y),text,font=font,anchor='mt',stroke_width=1)
        if not (PANEL[0]<=box[0]<box[2]<=PANEL[2] and PANEL[1]<=box[1]<box[3]<=PANEL[3]):
            raise ValueError(f'numeric panel text leaves safe area: {text} {box}')
        result.append({'text':text,'fontSize':size,'xy':(640,y),'bbox':box})
    return result


def draw_hero(frame: Image.Image, state: dict | None, font_path: Path) -> None:
    if state is None:
        return
    items=layout(state,font_path)
    draw=ImageDraw.Draw(frame,'RGBA')
    draw.rounded_rectangle((PANEL[0],PANEL[1],PANEL[2]-1,PANEL[3]-1),radius=12,fill=(9,15,23,220))
    for item in items:
        font=ImageFont.truetype(str(font_path),item['fontSize'])
        draw.text(item['xy'],item['text'],font=font,anchor='mt',fill=(255,248,231,255),stroke_width=1,stroke_fill=(0,0,0,220))
