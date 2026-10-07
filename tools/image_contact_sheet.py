import json
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'test-output'; out.mkdir(exist_ok=True)
entries=json.loads((ROOT/'data/curriculum.json').read_text(encoding='utf-8'))[:200]
for page in range(4):
    sheet=Image.new('RGB',(1000,1200),'#fffef9'); draw=ImageDraw.Draw(sheet)
    for i,w in enumerate(entries[page*50:(page+1)*50]):
        x=(i%5)*200;y=(i//5)*120
        if w['image']:
            with Image.open(ROOT/'static'/w['image']) as im:
                im=im.convert('RGBA');im.thumbnail((145,90));sheet.paste(im,(x+25,y),im)
        draw.text((x+10,y+94),f'{w["id"]}. {w["english"]}',fill='#193b3a')
    sheet.save(out/f'images-{page+1}.jpg')
