"""Prepare representative photographs for concrete unmatched concepts, with per-file licenses."""
import concurrent.futures,hashlib,html,io,json,re,time,urllib.parse,urllib.request
from pathlib import Path
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1]
QUERIES={'shorts':'shorts clothing','hoodie':'hooded sweatshirt','pajamas':'pyjamas clothing','toenail':'toenails foot','silk':'silk fabric','hem':'hem sewing','beanie':'knit cap','hairclip':'hair clip','doormat':'door mat','lotion':'skin lotion bottle','turnip':'turnip vegetable','badge':'name badge','archery':'archery sport','pound':'British pound coin','cumin':'cumin seeds','satchel':'school satchel','turmeric':'turmeric spice','porridge':'porridge oats','dishcloth':'dishcloth','oatmeal':'oatmeal','washcloth':'washcloth','foal':'horse foal','duckling':'duckling duck','unicycle':'unicycle','gosling':'gosling goose','cub':'bear cub','hinge':'door hinge','fawn':'deer fawn','snowball':'snowball snow','robin':'European robin bird','beanbag':'bean bag chair','crow':'crow bird','woodpecker':'woodpecker bird','jelly':'fruit jelly dessert','speedboat':'speedboat','smoothie':'fruit smoothie','kayak':'kayak boat','wagon':'railroad wagon','keyhole':'keyhole door','goldfish':'goldfish','doorbell':'doorbell button','marker':'felt tip markers','motorhome':'motorhome vehicle','showerhead':'shower head','gecko':'gecko lizard','bulldozer':'bulldozer vehicle','clipboard':'clipboard stationery','carton':'milk carton','schoolbag':'school bag backpack','packet':'packet food','crossroads':'road crossroads','junction':'road junction','layby':'road layby','milestone':'road milestone','bollard':'street bollard','protractor':'protractor geometry','mosaic':'mosaic art','sunlight':'sunlight trees','sunset':'sunset landscape','evening':'evening twilight','storm':'storm clouds lightning','first aid':'first aid kit','traffic':'traffic road','grocery':'groceries food','workbook':'school workbook','textbook':'school textbook','sketchbook':'drawing sketchbook','worksheet':'worksheet education','uniform':'school uniform','babysitter':'babysitter','puppy':'puppy dog','customer':'customer shop','guest':'guest welcome','colleague':'colleagues meeting','waist':'human waist','sprain':'ankle sprain','greasy':'greasy frying pan','washing up':'washing dishes','kayaking':'kayaking','jogging':'jogging runners','queue':'queue people','pattern':'geometric pattern','reservation':'reserved table sign','art':'painting art','destination':'destination road sign'}
def request(url):
    req=urllib.request.Request(url,headers={'User-Agent':'ArabicFamilyLearning/1.0 (https://github.com/matoug24/arabic)'})
    return urllib.request.urlopen(req,timeout=25).read()
def clean(s):return html.unescape(re.sub('<[^>]+>','',s or '')).strip()
def main():
    path=ROOT/'data/curriculum.json';entries=json.loads(path.read_text(encoding='utf-8'));dest=ROOT/'static/images';cache=ROOT/'data/commons';cache.mkdir(exist_ok=True)
    def get(w):
        if w['image'] or w['english'] not in QUERIES:return None
        query=QUERIES[w['english']];cachefile=cache/(str(w['id'])+'.json')
        try:
            params=dict(action='query',format='json',generator='search',gsrsearch=query+' filetype:bitmap',gsrnamespace=6,gsrlimit=4,prop='imageinfo',iiprop='url|extmetadata|size|mime',iiurlwidth=500)
            payload=json.loads(cachefile.read_text(encoding='utf-8')) if cachefile.exists() else json.loads(request('https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(params)))
            cachefile.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
            candidates=[]
            for page in payload.get('query',{}).get('pages',{}).values():
                if not page.get('imageinfo'):continue
                info=page['imageinfo'][0];meta=info.get('extmetadata',{});license=clean(meta.get('LicenseShortName',{}).get('value',''))
                if not (license.startswith(('CC BY','CC0','Public domain'))):continue
                if info.get('mime') not in ('image/jpeg','image/png','image/webp'):continue
                candidates.append((page,info,meta,license))
            if not candidates:return w['english']+': no verified-license image candidate'
            page,info,meta,license=min(candidates,key=lambda x:x[0].get('index',999))
            url=info.get('thumburl',info['url']);filename='commons-'+str(page['pageid'])+'.jpg'
            im=Image.open(io.BytesIO(request(url)));im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((500,500));im.save(dest/filename,quality=85)
            w.update(image='images/'+filename,image_candidate=None,image_source=info['descriptionurl'],image_creator=clean(meta.get('Artist',{}).get('value','Unknown creator; inspect original page')),image_license=license,image_match=query,image_review='Wikimedia concrete-concept search; license verified from original metadata; semantic review required before publication.',image_approved=False)
            return 'Prepared Commons photo: '+w['english']
        except Exception as exc:return w['english']+': '+str(exc)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(get,entries):
            if result:print(result,flush=True)
    path.write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8');print('Coverage:',sum(bool(w['image']) for w in entries),'of 2000')
if __name__=='__main__':main()
