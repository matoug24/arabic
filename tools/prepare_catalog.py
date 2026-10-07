import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from curriculum import classify
path=ROOT/'data/curriculum.json';words=json.loads(path.read_text(encoding='utf-8'))
for w in words:w['category']=classify(w,force=True);w['taxonomy_version']=2
path.write_text(json.dumps(words,ensure_ascii=False,indent=2),encoding='utf-8')
print('20-topic taxonomy applied to',len(words),'entries')
