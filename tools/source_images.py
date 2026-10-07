"""Download exact-keyword ARASAAC matches; never auto-approve semantics."""
import argparse, concurrent.futures, json, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--level',type=int,default=1); ap.add_argument('--all',action='store_true'); args=ap.parse_args()
    path=ROOT/'data/curriculum.json'; entries=json.loads(path.read_text(encoding='utf-8'))
    dest=ROOT/'static/images'; dest.mkdir(parents=True,exist_ok=True)
    def get(e):
        if (not args.all and e['level']!=args.level) or not e['image_candidate']: return None
        if e['image'] and (ROOT/'static'/e['image']).exists():return None
        pid=e['image_candidate']; filename=f'arasaac-{pid}.png'; url=f'https://static.arasaac.org/pictograms/{pid}/{pid}_500.png'
        try:
            if not (dest/filename).exists():
                req=urllib.request.Request(url,headers={'User-Agent':'ArabicFamilyLearning/1.0 (private educational use)'})
                (dest/filename).write_bytes(urllib.request.urlopen(req,timeout=35).read())
            from PIL import Image
            with Image.open(dest/filename) as im:
                im.verify()
            e.update(image=f'images/{filename}',image_source=f'https://arasaac.org/pictograms/en/{pid}',image_creator='Sergio Palao / Government of Aragon / ARASAAC',image_license='CC BY-NC-SA 4.0',image_approved=False)
            return 'OK'
        except Exception as exc: return f'{e["english"]}: {exc}'
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        count=0
        for msg in pool.map(get,entries):
            if msg=='OK':
                count+=1
                if count%100==0:print('Downloaded',count,flush=True)
            elif msg: print(msg,flush=True)
    path.write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Images prepared:',sum(bool(e['image']) for e in entries if args.all or e['level']==args.level))
if __name__=='__main__': main()
