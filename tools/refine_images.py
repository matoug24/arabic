"""Editorial corrections after visual inspection of the first 200 matches."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPLACEMENTS={'plane':6924,'game':9810,'room':32422,'class':33072,'read':7141,'kitchen':10752,'chicken':4952,'desk':11302,'lesson':39047,'hobby':11653,'parent':35059,'their':12274,'park':2859,'who':9853,'letter':3050}
def main():
    path=ROOT/'data/curriculum.json';words=json.loads(path.read_text(encoding='utf-8'))
    for w in words:
        if w['level']==1 and w['english'] in REPLACEMENTS:
            w['image_candidate']=REPLACEMENTS[w['english']];w['image']='';w['image_approved']=False
            w['content_note']='Image match edited after contact-sheet inspection; approve the chosen sense for your family.'
        if w['level']==1 and w['english']=='uniform':
            w['content_note']='No clear generic school-uniform pictogram found. Needs a representative licensed photograph or your own image.'
    path.write_text(json.dumps(words,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
