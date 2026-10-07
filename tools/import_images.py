"""Import prepared image metadata into existing drafts, preserving parent edits."""
import json,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    catalog=json.loads((ROOT/'data/curriculum.json').read_text(encoding='utf-8')); path=ROOT/'instance/learning.sqlite3'
    if not path.exists(): print('No database yet. First launch will import the complete catalog.');return
    db=sqlite3.connect(path);count=0
    for entry in catalog:
        row=db.execute('SELECT data FROM words WHERE english=?',(entry['english'],)).fetchone()
        if not row: continue
        w=json.loads(row[0])
        if w['image'] or not entry['image']:continue
        for k in ['image','image_source','image_creator','image_license','image_candidate']:w[k]=entry[k]
        w['image_approved']=False;w['published']=False
        db.execute('UPDATE words SET data=? WHERE id=?',(json.dumps(w,ensure_ascii=False),w['id']));count+=1
    db.commit();db.close();print('Imported images into',count,'drafts. Parent images and recordings preserved.')
if __name__=='__main__':main()
