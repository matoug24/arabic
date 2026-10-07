"""Additive, restart-safe schema upgrades and immutable homework membership."""
import json
from datetime import datetime,timezone
from curriculum import classify

def stamp():return datetime.now(timezone.utc).isoformat()
def snapshot_assignment(db,a):
    if db.execute('SELECT 1 FROM assignment_cards WHERE assignment_id=?',(a['id'],)).fetchone():return
    rows=db.execute('SELECT id,data FROM words WHERE level=? AND position BETWEEN ? AND ? ORDER BY position',(a['level'],(a['day']-1)*20+1,a['day']*20)).fetchall()
    db.executemany('INSERT OR IGNORE INTO assignment_cards VALUES(?,?,?,?)',[(a['id'],i,r['id'],r['data']) for i,r in enumerate(rows)])

def rebuild_plan(db,uid):
    """Retain issued slots; fill remaining slots by new placement where possible."""
    fixed={}
    for a in db.execute('SELECT * FROM assignments WHERE user_id=? ORDER BY id',(uid,)).fetchall():
        snapshot_assignment(db,a)
        for row in db.execute('SELECT position,word_id FROM assignment_cards WHERE assignment_id=?',(a['id'],)):
            fixed[(a['level']-1)*200+(a['day']-1)*20+row['position']+1]=row['word_id']
    used=set(fixed.values());plan=dict(fixed);floating=[]
    for r in db.execute('SELECT id,level,position FROM words ORDER BY level,position'):
        slot=(r['level']-1)*200+r['position']
        if r['id'] in used:continue
        if slot in fixed:floating.append((slot,r['id']))
        else:plan[slot]=r['id']
    holes=set(range(1,2001))-set(plan)
    for desired,wid in floating:
        if not holes:raise ValueError('Curriculum plan cannot preserve 2,000 distinct slots')
        slot=min(holes,key=lambda s:(abs(s-desired),s));holes.remove(slot);plan[slot]=wid
    if len(plan)!=2000 or len(set(plan.values()))!=2000:raise ValueError('Plan must contain 2,000 unique entries')
    db.execute('DELETE FROM child_plan WHERE user_id=?',(uid,))
    db.executemany('INSERT INTO child_plan VALUES(?,?,?)',[(uid,slot,wid) for slot,wid in sorted(plan.items())])

def migrate(db,catalog):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS schema_meta(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE IF NOT EXISTS assignment_cards(assignment_id INTEGER REFERENCES assignments(id),position INTEGER,word_id INTEGER REFERENCES words(id),data TEXT,PRIMARY KEY(assignment_id,position));
    CREATE TABLE IF NOT EXISTS child_plan(user_id INTEGER REFERENCES users(id),slot INTEGER,word_id INTEGER REFERENCES words(id),PRIMARY KEY(user_id,slot),UNIQUE(user_id,word_id));
    CREATE TABLE IF NOT EXISTS placement_history(id INTEGER PRIMARY KEY,parent_id INTEGER,word_id INTEGER,other_id INTEGER,old_level INTEGER,old_position INTEGER,new_level INTEGER,new_position INTEGER,created TEXT);
    CREATE TABLE IF NOT EXISTS exploration_batches(id TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),category TEXT,topic TEXT,words TEXT,created TEXT,preview INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS topic_practice(user_id INTEGER REFERENCES users(id),word_id INTEGER REFERENCES words(id),completed TEXT,PRIMARY KEY(user_id,word_id));
    ''')
    version=db.execute("SELECT value FROM schema_meta WHERE key='taxonomy'").fetchone()
    if not version:
        for row in db.execute('SELECT id,data FROM words').fetchall():
            w=json.loads(row['data']);w['category']=classify(w,force=True);w['taxonomy_version']=2
            db.execute('UPDATE words SET data=? WHERE id=?',(json.dumps(w,ensure_ascii=False),row['id']))
        db.execute("INSERT INTO schema_meta VALUES('taxonomy','20-v1')")
    # Import prepared imagery only into an empty image slot. Never replace uploads or approvals.
    by_english={w['english']:w for w in catalog}
    for row in db.execute('SELECT id,data FROM words').fetchall():
        w=json.loads(row['data']);incoming=by_english.get(w['english'])
        managed=w.get('image','').startswith(('images/arasaac-','images/commons-','images/concept-','images/reviewed-'))
        if incoming and incoming.get('image') and (not w.get('image') or (managed and not w.get('image_approved') and w['image']!=incoming['image'])):
            for key in ('image','image_source','image_creator','image_license','image_candidate','image_match','image_review'):w[key]=incoming.get(key,'')
            w['image_approved']=False;w['published']=False
            db.execute('UPDATE words SET data=? WHERE id=?',(json.dumps(w,ensure_ascii=False),row['id']))
    for a in db.execute('SELECT * FROM assignments').fetchall():snapshot_assignment(db,a)
    for u in db.execute("SELECT id FROM users WHERE role='child'").fetchall():
        if not db.execute('SELECT 1 FROM child_plan WHERE user_id=?',(u['id'],)).fetchone():rebuild_plan(db,u['id'])
    db.execute("INSERT INTO schema_meta VALUES('version','2') ON CONFLICT(key) DO UPDATE SET value=excluded.value")
    db.commit()
