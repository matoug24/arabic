"""Full-catalog image integrity audit and 40 contact sheets. Optional QA-only resvg_py."""
import argparse,hashlib,io,json,sys,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.qa-deps'))
import resvg_py
def main():
    p=argparse.ArgumentParser();p.add_argument('--corrections-only',action='store_true');args=p.parse_args()
    data=json.loads((ROOT/'data/curriculum.json').read_text(encoding='utf-8'));out=ROOT/'test-output/image-review';out.mkdir(parents=True,exist_ok=True);manifest=[]
    if args.corrections_only:
        corrected=set(json.loads((ROOT/'data/image_corrections.json').read_text(encoding='utf-8')));data=[w for w in data if w['english'] in corrected]
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14) if Path('C:/Windows/Fonts/arial.ttf').exists() else ImageFont.load_default()
    for page in range(math.ceil(len(data)/50)):
        sheet=Image.new('RGB',(1200,1600),'#fffef9');draw=ImageDraw.Draw(sheet)
        for i,w in enumerate(data[page*50:(page+1)*50]):
            x=(i%5)*240;y=(i//5)*160;p=ROOT/'static'/w['image']
            raw=p.read_bytes()
            if p.suffix=='.svg':raw=resvg_py.svg_to_bytes(svg_string=raw.decode('utf-8'))
            with Image.open(io.BytesIO(raw)) as original:
                rgba=original.convert('RGBA');im=Image.new('RGB',rgba.size,'white');im.paste(rgba,mask=rgba.getchannel('A'));pixel_hash=hashlib.sha256(im.tobytes()).hexdigest();im.thumbnail((220,130));sheet.paste(im,(x+(240-im.width)//2,y))
            draw.text((x+6,y+134),f'{w["id"]}. {w["english"]}',font=font,fill='#193b3a')
            manifest.append(dict(id=w['id'],english=w['english'],image=w['image'],sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pixel_hash=pixel_hash,source=w['image_source'],creator=w['image_creator'],license=w['image_license'],review='Pending full-sheet visual review'))
        sheet.save(out/f'{"corrections" if args.corrections_only else "catalog"}-{page+1:02}.jpg',quality=90)
    (ROOT/'data'/('corrected_image_review.json' if args.corrections_only else 'image_review.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print('Contact sheets and integrity/provenance manifest prepared for',len(data),'entries.')
if __name__=='__main__':main()
