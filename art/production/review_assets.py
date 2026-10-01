"""Render review sheets and measure small-icon transparency; never alter masters."""
from pathlib import Path
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art' / 'static-v1'
data = json.loads((OUT / 'manifest.json').read_text('utf-8'))
font_path = Path('C:/Windows/Fonts/msyh.ttc')
font = ImageFont.truetype(str(font_path), 16)
small = ImageFont.truetype(str(font_path), 11)
review = OUT / 'review'
review.mkdir(exist_ok=True)
labels = {'common':'共同','taixuan':'太玄','tianqing':'天倾','xueyan':'血魇','xingge':'行歌'}
metrics = []
for group, label in labels.items():
    rows = [r for r in data['assets'] if r['group'] == group and r['status'] == 'complete' and r['kind'] != 'illustration']
    if not rows:
        continue
    cols, cell_w, cell_h = 5, 220, 260
    sheet = Image.new('RGB', (cols * cell_w, 60 + math.ceil(len(rows)/cols) * cell_h), '#101817')
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 15), f'{label} · 母版缩略与实际 64px 对照', font=font, fill='#d8b875')
    for i, row in enumerate(rows):
        x, y = (i % cols) * cell_w, 60 + (i // cols) * cell_h
        draw.rectangle((x+5,y+5,x+cell_w-5,y+cell_h-5),outline='#36413f')
        with Image.open(OUT / row['master']) as original:
            preview = original.convert('RGBA')
            preview.thumbnail((160,160),Image.Resampling.LANCZOS)
            sheet.paste(preview,(x+(cell_w-preview.width)//2,y+8),preview)
        folder = 'class_hotbar_64' if row['kind']=='badge' else 'hotbar_64'
        with Image.open(OUT / 'exports' / folder / (row.get('basename',row['id'])+'.png')) as icon:
            rgba = icon.convert('RGBA')
            sheet.paste(rgba,(x+18,y+180),rgba)
            alpha = rgba.getchannel('A')
            bbox = alpha.getbbox()
            visible = sum(v > 32 for v in alpha.get_flattened_data())
            metrics.append({'id':row['id'],'alpha_bbox_64':bbox,'visible_pixels_over_32':visible})
        draw.text((x+92,y+180),row['name'],font=font,fill='#eee8dc')
        draw.text((x+92,y+207),'实际 64px',font=small,fill='#a6b6ad')
        draw.text((x+12,y+239),row['id'],font=small,fill='#a6b6ad')
    sheet.save(review / (group+'-contact.png'))
(review/'small-icon-metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'sheets':len(list(review.glob('*-contact.png'))),'icons_checked':len(metrics)},ensure_ascii=True))
