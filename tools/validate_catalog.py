"""Deployment preflight: every planned entry must have an attributed local picture."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from curriculum import CATEGORIES
d=json.loads((ROOT/'data/curriculum.json').read_text(encoding='utf-8'))
assert len(d)==2000 and len({w['id'] for w in d})==2000 and len({w['lemma'] for w in d})==2000
assert len(CATEGORIES)==20 and set(w['category'] for w in d)<=set(CATEGORIES)
for level in range(1,11):assert sorted(w['position'] for w in d if w['level']==level)==list(range(1,201))
missing=[]
for w in d:
    if not w.get('image') or not (ROOT/'static'/w['image']).is_file() or not all(w.get(k) for k in ('image_source','image_creator','image_license')):missing.append(w['english'])
if missing:raise SystemExit('Missing/ unattributed picture: '+', '.join(missing))
print('Catalog OK: 2,000 unique entries, 20 categories, ten 200-entry levels, 2,000 local attributed images.')
