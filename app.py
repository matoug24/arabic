"""Private family Arabic learning. SQLite state, original parent recordings."""
import functools, io, json, os, re, secrets, sqlite3, time, unicodedata, uuid, zipfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from PIL import Image, ImageOps
from werkzeug.middleware.proxy_fix import ProxyFix
from curriculum import CATEGORIES
from migrations import migrate, rebuild_plan, snapshot_assignment

ROOT=Path(__file__).resolve().parent
def normal(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text.strip()) if not unicodedata.combining(c) and c not in 'ـ\u200e\u200f').strip()
def arabic_feedback(answer, expected):
    """Minimum edit alignment. Spans remain in logical order within one RTL run."""
    a,b=list(normal(answer)),list(normal(expected)); n,m=len(a),len(b)
    dp=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1): dp[i][0]=i
    for j in range(m+1): dp[0][j]=j
    for i in range(1,n+1):
        for j in range(1,m+1): dp[i][j]=min(dp[i-1][j]+1,dp[i][j-1]+1,dp[i-1][j-1]+(a[i-1]!=b[j-1]))
    segments=[]; i,j=n,m
    while i or j:
        if i and j and dp[i][j]==dp[i-1][j-1]+(a[i-1]!=b[j-1]):
            segments.append({'text':a[i-1], 'kind':'ok' if a[i-1]==b[j-1] else 'wrong','expected':b[j-1]}); i-=1; j-=1
        elif i and dp[i][j]==dp[i-1][j]+1:
            segments.append({'text':a[i-1],'kind':'extra','expected':''}); i-=1
        else:
            segments.append({'text':'ـ','kind':'missing','expected':b[j-1]}); j-=1
    return list(reversed(segments))

def create_app(config=None):
    app=Flask(__name__,instance_relative_config=True)
    state=Path(os.environ.get('ARABIC_STATE_DIR',ROOT/'instance'))
    app.config.update(DATABASE=str(state/'learning.sqlite3'),UPLOAD_DIR=str(state/'media'),MAX_CONTENT_LENGTH=12*1024*1024,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.environ.get('ARABIC_PRODUCTION')=='1',PRODUCTION=os.environ.get('ARABIC_PRODUCTION')=='1',SETUP_TOKEN_FILE=str(state/'setup-token'),TIMEZONE='America/Toronto',PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    if config: app.config.update(config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True,exist_ok=True)
    Path(app.config['UPLOAD_DIR']).mkdir(parents=True,exist_ok=True)
    secret_path=Path(app.config['DATABASE']).parent/'session-secret'
    if not secret_path.exists():
        with secret_path.open('x') as f:f.write(secrets.token_hex(32))
        secret_path.chmod(0o600)
    app.secret_key=app.config.get('SECRET_KEY') or secret_path.read_text().strip()
    if app.config['PRODUCTION']:
        app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1)
        app.config['TRUSTED_HOSTS']=[os.environ.get('ARABIC_DOMAIN','arabic.matoug.com'),'127.0.0.1','localhost']
    def db():
        if 'db' not in g:
            g.db=sqlite3.connect(app.config['DATABASE'],timeout=20); g.db.row_factory=sqlite3.Row; g.db.execute('PRAGMA foreign_keys=ON'); g.db.execute('PRAGMA journal_mode=WAL')
        return g.db
    def query(sql,args=()): return db().execute(sql,args).fetchall()
    def one(sql,args=()): return db().execute(sql,args).fetchone()
    def change(sql,args=()):
        cur=db().execute(sql,args); db().commit(); return cur
    @app.teardown_appcontext
    def close_db(error):
        if 'db' in g: g.db.close()
    with app.app_context():
        db().executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE COLLATE NOCASE,name TEXT,hash TEXT,role TEXT CHECK(role IN ('parent','child')),enabled INTEGER DEFAULT 1,review_only INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS words(id INTEGER PRIMARY KEY,english TEXT UNIQUE,level INTEGER,position INTEGER,data TEXT,UNIQUE(level,position));
        CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),level INTEGER,day INTEGER,created TEXT,completed TEXT,position INTEGER DEFAULT 0,UNIQUE(user_id,level,day));
        CREATE TABLE IF NOT EXISTS practice(user_id INTEGER REFERENCES users(id),assignment_id INTEGER REFERENCES assignments(id),word_id INTEGER REFERENCES words(id),completed TEXT,PRIMARY KEY(user_id,assignment_id,word_id));
        CREATE TABLE IF NOT EXISTS exploration(user_id INTEGER REFERENCES users(id),word_id INTEGER REFERENCES words(id),visited TEXT,PRIMARY KEY(user_id,word_id));
        CREATE TABLE IF NOT EXISTS review_queue(user_id INTEGER REFERENCES users(id),word_id INTEGER REFERENCES words(id),reason TEXT,updated TEXT,PRIMARY KEY(user_id,word_id));
        CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),assignment_id INTEGER,day TEXT,words TEXT,completed TEXT,UNIQUE(user_id,assignment_id,day));
        CREATE TABLE IF NOT EXISTS review_practice(review_id INTEGER REFERENCES reviews(id),word_id INTEGER REFERENCES words(id),PRIMARY KEY(review_id,word_id));
        CREATE TABLE IF NOT EXISTS quizzes(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),assignment_id INTEGER,kind TEXT,level INTEGER,created TEXT,completed TEXT,questions TEXT);
        CREATE TABLE IF NOT EXISTS answers(id INTEGER PRIMARY KEY,quiz_id INTEGER REFERENCES quizzes(id),q INTEGER,word_id INTEGER,modality TEXT,answer TEXT,correct INTEGER,first INTEGER,created TEXT,feedback TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS first_answer ON answers(quiz_id,q) WHERE first=1;
        CREATE TABLE IF NOT EXISTS level_reviews(user_id INTEGER REFERENCES users(id),level INTEGER,quiz_id INTEGER,completed TEXT,PRIMARY KEY(user_id,level));
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),word_id INTEGER,kind TEXT,source TEXT,seconds REAL DEFAULT 0,created TEXT);
        CREATE TABLE IF NOT EXISTS heartbeats(user_id INTEGER PRIMARY KEY,last REAL);
        CREATE TABLE IF NOT EXISTS login_failures(ip TEXT PRIMARY KEY,count INTEGER,last REAL);
        ''')
        catalog=json.loads((ROOT/'data/curriculum.json').read_text(encoding='utf-8'))
        if not one('SELECT id FROM words LIMIT 1'):
            db().executemany('INSERT INTO words VALUES(?,?,?,?,?)',[(w['id'],w['english'],w['level'],w['position'],json.dumps(w,ensure_ascii=False)) for w in catalog]); db().commit()
        migrate(db(),catalog)
    def setting(key,default):
        r=one('SELECT value FROM settings WHERE key=?',(key,)); return r['value'] if r else default
    def now(): return datetime.now(ZoneInfo(setting('timezone',app.config['TIMEZONE'])))
    def stamp(): return now().isoformat()
    def today(): return now().date().isoformat()
    def word(wid):
        r=one('SELECT data FROM words WHERE id=?',(wid,))
        if not r: abort(404)
        return json.loads(r['data'])
    def words(sql='',args=()): return [json.loads(r['data']) for r in query('SELECT data FROM words '+sql,args)]
    def ready(w):
        return bool(w['published'] and w['english'] and w['meaning'] and w['image'] and w['image_approved'] and w['audio'] and w['arabic_approved'] and w['arabic'] and media_exists(w['audio']) and media_exists(w['image']))
    def media_exists(path):
        base=Path(app.config['UPLOAD_DIR']) if path.startswith('uploads/') else ROOT/'static'
        relative=path.removeprefix('uploads/')
        p=(base/relative).resolve()
        return p.is_relative_to(base.resolve()) and p.is_file()
    def current_level(uid):
        return min(10,1+len(query('SELECT level FROM level_reviews WHERE user_id=?',(uid,))))
    def eligible(w):
        return g.user['role']=='parent' or (ready(w) and (w['level']<=current_level(g.user['id']) or one('SELECT word_id FROM exploration WHERE user_id=? AND word_id=?',(g.user['id'],w['id'])) or one('SELECT b.id FROM exploration_batches b JOIN json_each(b.words) j ON j.value=? WHERE b.user_id=? AND b.preview=0',(w['id'],g.user['id'])) or one('SELECT c.word_id FROM assignment_cards c JOIN assignments a ON c.assignment_id=a.id WHERE a.user_id=? AND c.word_id=?',(g.user['id'],w['id']))))
    def require(role=None):
        def deco(fn):
            @functools.wraps(fn)
            def wrapped(*args,**kwargs):
                if not g.user: return redirect(url_for('login')) if not request.path.startswith('/api/') else (jsonify(error='Sign in required'),401)
                if role and g.user['role']!=role: abort(403)
                return fn(*args,**kwargs)
            return wrapped
        return deco
    @app.before_request
    def secure():
        session.setdefault('csrf',secrets.token_urlsafe(32))
        g.user=one('SELECT * FROM users WHERE id=? AND enabled=1',(session.get('uid',-1),))
        if request.method in ('POST','PUT','DELETE'):
            token=request.headers.get('X-CSRF-Token') or request.form.get('csrf')
            if not token or not secrets.compare_digest(token,session['csrf']): abort(400, 'Please refresh this page and try again.')
    @app.after_request
    def headers(res):
        res.headers['X-Content-Type-Options']='nosniff'; res.headers['X-Frame-Options']='DENY'; res.headers['Referrer-Policy']='same-origin'
        res.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'"
        if request.endpoint!='static': res.headers['Cache-Control']='no-store'
        return res
    def child_link(name):
        return url_for('parent_preview',page=name) if g.user and g.user['role']=='parent' and request.path.startswith('/admin/preview') else url_for(name)
    @app.context_processor
    def context(): return dict(user=g.user,csrf=session['csrf'],categories=CATEGORIES,asset_url=asset_url,ready=ready,child_link=child_link)
    def asset_url(path):
        if path.startswith('uploads/'): return url_for('uploaded',filename=path[8:])
        return url_for('static',filename=path)
    @app.route('/media/<path:filename>')
    @require()
    def uploaded(filename):
        if g.user['role']!='parent':
            available=[w for w in words() if eligible(w)]
            available.extend(json.loads(r['data']) for r in query('SELECT c.data FROM assignment_cards c JOIN assignments a ON a.id=c.assignment_id WHERE a.user_id=?',(g.user['id'],)) if ready(word(json.loads(r['data'])['id'])))
            if not any('uploads/'+filename in (w['image'],w['audio'],w.get('sentence_audio','')) for w in available): abort(403)
        return send_from_directory(app.config['UPLOAD_DIR'],filename)
    @app.route('/setup',methods=['GET','POST'])
    def setup():
        if one('SELECT id FROM users LIMIT 1'): return redirect(url_for('login'))
        if app.config['PRODUCTION']:
            if not request.is_secure:abort(403,'Parent setup requires HTTPS.')
            path=Path(app.config['SETUP_TOKEN_FILE'])
            if not path.is_file():abort(403,'Setup is disabled. Generate a one-time token on the server.')
            if request.method=='POST' and not secrets.compare_digest(request.form.get('setup_token',''),path.read_text().strip()):abort(403,'Invalid setup token.')
        elif request.remote_addr not in ('127.0.0.1','::1'): abort(403)
        if request.method=='POST':
            username=request.form.get('username','').strip(); password=request.form.get('password','')
            if not username or len(password)<12: flash('Choose a username and a password of at least 12 characters.','error')
            else:
                uid=change('INSERT INTO users(username,name,hash,role) VALUES(?,?,?,?)',(username,'Parent',generate_password_hash(password),'parent')).lastrowid
                session.clear(); session['uid']=uid; session['csrf']=secrets.token_urlsafe(32); session.permanent=True
                if app.config['PRODUCTION']:Path(app.config['SETUP_TOKEN_FILE']).unlink(missing_ok=True)
                return redirect(url_for('admin'))
        return render_template('auth.html',setup=True,production_setup=app.config['PRODUCTION'])
    @app.get('/healthz')
    def health():
        try:one('SELECT value FROM schema_meta WHERE key=?',('version',));return jsonify(status='ok')
        except sqlite3.Error:return jsonify(status='unavailable'),503
    @app.route('/login',methods=['GET','POST'])
    def login():
        if not one('SELECT id FROM users LIMIT 1'): return redirect(url_for('setup'))
        if request.method=='POST':
            ip=request.remote_addr; failures=one('SELECT * FROM login_failures WHERE ip=?',(ip,))
            if failures and failures['count']>=10 and time.time()-failures['last']<300: abort(429,'Too many attempts. Try again in five minutes.')
            u=one('SELECT * FROM users WHERE username=? AND enabled=1',(request.form.get('username',''),))
            if u and check_password_hash(u['hash'],request.form.get('password','')):
                change('DELETE FROM login_failures WHERE ip=?',(ip,)); session.clear(); session['uid']=u['id']; session['csrf']=secrets.token_urlsafe(32); session.permanent=True
                return redirect(url_for('home'))
            change('INSERT INTO login_failures VALUES(?,1,?) ON CONFLICT(ip) DO UPDATE SET count=CASE WHEN ?-last>300 THEN 1 ELSE count+1 END,last=excluded.last',(ip,time.time(),time.time()))
            flash('Username or password is incorrect.','error')
        return render_template('auth.html',setup=False)
    @app.post('/logout')
    def logout(): session.clear(); return redirect(url_for('login'))
    @app.get('/')
    @require()
    def home():
        if g.user['role']=='parent': return redirect(url_for('admin'))
        uid=g.user['id']; level=current_level(uid); completed=one('SELECT COUNT(*) n FROM assignments WHERE user_id=? AND completed IS NOT NULL',(uid,))['n']
        learned=one('SELECT COUNT(DISTINCT word_id) n FROM practice WHERE user_id=?',(uid,))['n']
        return render_template('home.html',level=level,completed=completed,learned=learned)
    def assignment():
        uid=g.user['id']; lvl=current_level(uid)
        active=one('SELECT * FROM assignments WHERE user_id=? AND completed IS NULL ORDER BY id LIMIT 1',(uid,))
        if active: return active, 'Continue where you left off.'
        last=one('SELECT * FROM assignments WHERE user_id=? ORDER BY id DESC LIMIT 1',(uid,))
        if g.user['review_only']: return None,'Today is a review day. Explore or revisit your words.'
        if last and last['completed'] and last['completed'][:10]>=today(): return last,'Homework complete. Your next assignment opens tomorrow.'
        count=one('SELECT COUNT(*) n FROM assignments WHERE user_id=? AND level=? AND completed IS NOT NULL',(uid,lvl))['n']
        if count>=10: return last,'Ten assignments complete! Take your end-level review to continue.'
        if not one('SELECT slot FROM child_plan WHERE user_id=?',(uid,)):rebuild_plan(db(),uid);db().commit()
        start=(lvl-1)*200+count*20+1
        batch=[word(r['word_id']) for r in query('SELECT word_id FROM child_plan WHERE user_id=? AND slot BETWEEN ? AND ? ORDER BY slot',(uid,start,start+19))]
        if len(batch)!=20 or not all(ready(w) for w in batch): return None,'Your parent is preparing the next 20 words. You can explore any ready words meanwhile.'
        aid=change('INSERT INTO assignments(user_id,level,day,created) VALUES(?,?,?,?)',(uid,lvl,count+1,stamp())).lastrowid
        db().executemany('INSERT INTO assignment_cards VALUES(?,?,?,?)',[(aid,i,w['id'],json.dumps(w,ensure_ascii=False)) for i,w in enumerate(batch)]);db().commit()
        return one('SELECT * FROM assignments WHERE id=?',(aid,)),'20 new words, one at a time.'
    def assignment_words(a):
        snapshot_assignment(db(),a);db().commit()
        return [json.loads(r['data']) for r in query('SELECT data FROM assignment_cards WHERE assignment_id=? ORDER BY position',(a['id'],)) if ready(word(json.loads(r['data'])['id']))]
    def public_card(w):
        examples=[dict(id=e['id'],label=e['label'],audio=url_for('example_media',eid=e['id'])) for e in query('SELECT * FROM word_examples WHERE word_id=? ORDER BY created,id',(w['id'],)) if media_exists(e['audio'])]
        return {k:w.get(k,'') for k in ('id','english','meaning','arabic','category','topic','level','sentence')} | {'image':asset_url(w['image']) if w['image'] else url_for('static',filename='missing-picture.svg'),'audio':asset_url(w['audio']) if w['audio'] else '', 'sentence_audio':asset_url(w['sentence_audio']) if w.get('sentence_audio') else '', 'examples':examples, 'credit':w['image_creator']+' · '+w['image_license'],'credit_url':w['image_source']}
    @app.get('/example-media/<eid>')
    @require()
    def example_media(eid):
        e=one('SELECT * FROM word_examples WHERE id=?',(eid,))
        if not e:abort(404)
        if not eligible(word(e['word_id'])):abort(403)
        return send_from_directory(app.config['UPLOAD_DIR'],e['audio'].removeprefix('uploads/'))
    def owned_assignment(aid):
        a=one('SELECT * FROM assignments WHERE id=? AND user_id=?',(aid,g.user['id']))
        if not a: abort(404)
        return a
    @app.get('/daily')
    @require('child')
    def daily():
        a,message=assignment(); cards=assignment_words(a) if a else []
        done=[r['word_id'] for r in query('SELECT word_id FROM practice WHERE user_id=? AND assignment_id=?',(g.user['id'],a['id']))] if a else []
        cards=[w for w in cards if ready(w)]
        payload=dict(cards=[public_card(w) for w in cards],source='homework',assignment=a['id'] if a else None,position=a['position'] if a else 0,done=done,completed=bool(a and a['completed']))
        return render_template('practice.html',title='Daily homework',message=message,payload=payload,quiz=a['id'] if a and a['completed'] else None)
    @app.post('/api/practice')
    @require('child')
    def practice():
        data=request.get_json(); a=owned_assignment(int(data['assignment'])); wid=int(data['word']); batch=assignment_words(a)
        if wid not in [w['id'] for w in batch] or not ready(word(wid)): abort(403)
        pos=max(0,min(19,int(data.get('position',0))))
        change('UPDATE assignments SET position=? WHERE id=?',(pos,a['id']))
        if data.get('complete'):
            change('INSERT OR IGNORE INTO practice VALUES(?,?,?,?)',(g.user['id'],a['id'],wid,stamp()))
        count=one('SELECT COUNT(*) n FROM practice WHERE assignment_id=?',(a['id'],))['n']
        if count==20 and not a['completed']: change('UPDATE assignments SET completed=? WHERE id=?',(stamp(),a['id']))
        return jsonify(completed=count==20,count=count)
    def review_set():
        uid=g.user['id']; a=one('SELECT * FROM assignments WHERE user_id=? ORDER BY id DESC LIMIT 1',(uid,))
        if not a: return None,[]
        r=one('SELECT * FROM reviews WHERE user_id=? AND assignment_id=? AND day=?',(uid,a['id'],today()))
        if r: return r,[word(wid) for wid in json.loads(r['words']) if ready(word(wid))]
        finished=query('SELECT id FROM assignments WHERE user_id=? AND completed IS NOT NULL AND id<>? ORDER BY id DESC',(uid,a['id']))
        # Review words must come from completed work, never future homework.
        candidates=[]
        for row in query('SELECT q.word_id FROM review_queue q JOIN practice p ON q.user_id=p.user_id AND q.word_id=p.word_id JOIN assignments a ON a.id=p.assignment_id WHERE q.user_id=? AND a.completed IS NOT NULL GROUP BY q.word_id ORDER BY q.updated DESC',(uid,)): candidates.append(row['word_id'])
        recent=[x['id'] for x in finished[:3]]
        older=[x['id'] for x in finished[3:]]
        rng=secrets.SystemRandom()
        def practiced(ids):
            result=[]
            for aid in ids: result.extend(r['word_id'] for r in query('SELECT word_id FROM practice WHERE assignment_id=?',(aid,)))
            rng.shuffle(result); return result
        old=practiced(older); new=practiced(recent)
        if old: candidates.extend(old[:1])
        candidates.extend(new); candidates.extend(old)
        ids=list(dict.fromkeys(wid for wid in candidates if ready(word(wid))))[:5]
        rid=change('INSERT INTO reviews(user_id,assignment_id,day,words) VALUES(?,?,?,?)',(uid,a['id'],today(),json.dumps(ids))).lastrowid
        return one('SELECT * FROM reviews WHERE id=?',(rid,)),[word(wid) for wid in ids]
    @app.get('/review')
    @require('child')
    def review():
        r,batch=review_set(); done=[x['word_id'] for x in query('SELECT word_id FROM review_practice WHERE review_id=?',(r['id'],))] if r else []
        return render_template('practice.html',title='A little review',message='Up to five extra words from completed homework. Revisit them without changing your homework progress.',payload=dict(cards=[public_card(w) for w in batch],source='review',review=r['id'] if r else None,position=0,done=done))
    @app.post('/api/review-practice')
    @require('child')
    def review_practice():
        d=request.get_json(); r=one('SELECT * FROM reviews WHERE id=? AND user_id=?',(d['review'],g.user['id']))
        if not r or d['word'] not in json.loads(r['words']): abort(403)
        change('INSERT OR IGNORE INTO review_practice VALUES(?,?)',(r['id'],d['word']))
        n=one('SELECT COUNT(*) n FROM review_practice WHERE review_id=?',(r['id'],))['n']
        if n==len(json.loads(r['words'])): change('UPDATE reviews SET completed=? WHERE id=?',(stamp(),r['id']))
        return jsonify(completed=n==len(json.loads(r['words'])))
    def explore_view(preview=False):
        category=request.args.get('category');topic=request.args.get('topic');available=[];topics=[]
        if category in CATEGORIES:
            all_matching=[w for w in words() if w['category']==category and (preview or ready(w))]
            topics=sorted({w['topic'] for w in all_matching});available=[w for w in all_matching if not topic or w['topic']==topic]
        last=one('SELECT words FROM exploration_batches WHERE user_id=? AND category=? AND topic=? AND preview=? ORDER BY created DESC LIMIT 1',(g.user['id'],category,topic or '',int(preview)))
        previous=set(json.loads(last['words'])) if last else set();fresh=[w for w in available if w['id'] not in previous];rng=secrets.SystemRandom()
        selected=rng.sample(fresh,min(10,len(fresh)))
        if len(selected)<min(10,len(available)):
            old=[w for w in available if w['id'] in previous];selected.extend(rng.sample(old,min(10-len(selected),len(old))))
        rng.shuffle(selected);batch_id=str(uuid.uuid4())
        if selected:change('INSERT INTO exploration_batches VALUES(?,?,?,?,?,?,?)',(batch_id,g.user['id'],category,topic or '',json.dumps([w['id'] for w in selected]),stamp(),int(preview)))
        done=[] if preview else [r['word_id'] for r in query('SELECT word_id FROM topic_practice WHERE user_id=?',(g.user['id'],)) if r['word_id'] in {w['id'] for w in selected}]
        payload=dict(cards=[public_card(w) for w in selected],source='preview' if preview else 'explore',batch=batch_id,position=0,done=done)
        params=dict(category=category,topic=topic,topics=topics,payload=payload,preview=False,batch_level=None,more=1 if available else None,available_count=len(available),preview_mode=preview)
        if preview:params['user']=dict(name='Explorer',role='child')
        return render_template('explore.html',**params)
    @app.get('/explore')
    @require('child')
    def explore():return explore_view()
    @app.post('/api/exploration-practice')
    @require('child')
    def topic_practice():
        d=request.get_json();b=one('SELECT * FROM exploration_batches WHERE id=? AND user_id=? AND preview=0',(d.get('batch'),g.user['id']))
        if not b or d.get('word') not in json.loads(b['words']) or not ready(word(d['word'])):abort(403)
        change('INSERT INTO topic_practice VALUES(?,?,?) ON CONFLICT(user_id,word_id) DO UPDATE SET completed=excluded.completed',(g.user['id'],d['word'],stamp()))
        return jsonify(ok=True)
    @app.get('/my-words')
    @require('child')
    def my_words():
        uid=g.user['id']; ids={r['word_id'] for r in query('SELECT word_id FROM practice WHERE user_id=? UNION SELECT word_id FROM exploration WHERE user_id=?',(uid,uid))}; batch=[word(wid) for wid in sorted(ids) if ready(word(wid))]
        return render_template('my_words.html',words=batch)
    @app.get('/word/<int:wid>')
    @require('child')
    def revisit(wid):
        w=word(wid)
        if not eligible(w): abort(403)
        return render_template('practice.html',title='My words',message='Revisit a word whenever you like.',payload=dict(cards=[public_card(w)],source='my_words',position=0,done=[]))
    @app.post('/api/practice-again')
    @require('child')
    def again():
        wid=int(request.get_json()['word']); w=word(wid)
        if not eligible(w): abort(403)
        change('INSERT INTO review_queue VALUES(?,?,?,?) ON CONFLICT(user_id,word_id) DO UPDATE SET reason=excluded.reason,updated=excluded.updated',(g.user['id'],wid,'Practice again',stamp()))
        return jsonify(ok=True)
    @app.get('/journey')
    @require('child')
    def journey():
        uid=g.user['id']; levels=[]
        for lvl in range(1,11):
            assignments=one('SELECT COUNT(*) n FROM assignments WHERE user_id=? AND level=? AND completed IS NOT NULL',(uid,lvl))['n']
            cleared=bool(one('SELECT * FROM level_reviews WHERE user_id=? AND level=?',(uid,lvl)))
            levels.append(dict(level=lvl,assignments=assignments,cleared=cleared,review=assignments==10 and not cleared))
        return render_template('journey.html',levels=levels)
    def make_quiz(aid=None,kind='daily',lvl=None):
        uid=g.user['id']
        if kind=='daily':
            a=owned_assignment(aid)
            if not a['completed']: abort(409,'Finish your homework first.')
            lvl=a['level']; pool=[w for w in assignment_words(a) if ready(w)]
        else:
            lvl=current_level(uid)
            if one('SELECT COUNT(*) n FROM assignments WHERE user_id=? AND level=? AND completed IS NOT NULL',(uid,lvl))['n']!=10: abort(409)
            pool=[w for a in query('SELECT * FROM assignments WHERE user_id=? AND level=? AND completed IS NOT NULL',(uid,lvl)) for w in assignment_words(a) if ready(w)]
        existing=one('SELECT * FROM quizzes WHERE user_id=? AND assignment_id IS ? AND kind=? AND level=? AND completed IS NULL ORDER BY id DESC LIMIT 1',(uid,aid,kind,lvl))
        if existing: return existing['id']
        if len(pool)<5: abort(409,'Five ready words are needed.')
        rng=secrets.SystemRandom(); chosen=rng.sample(pool,5)
        familiar_ids={r['word_id'] for r in query('SELECT word_id FROM practice WHERE user_id=? UNION SELECT word_id FROM exploration WHERE user_id=?',(uid,uid))}
        familiar=[word(wid) for wid in familiar_ids if ready(word(wid))]
        questions=[]; count=int(setting('quiz_choices','4')); audio_picture=setting('audio_picture','0')=='1'
        for i,w in enumerate(chosen):
            typ=('audio_picture' if audio_picture else 'audio_english') if i<3 else ('picture_arabic' if i==3 else 'writing')
            key='arabic' if typ=='picture_arabic' else ('image' if typ=='audio_picture' else 'english')
            qs=dict(word=w['id'],type=typ,options=[],correct='',expected=w['arabic'],variants=w['variants'],audio=w['audio'],image=w['image'],english=w['english'],image_credit=w['image_creator']+' · '+w['image_license'])
            if typ!='writing':
                unique={normal(w[key])}; distractors=[]
                candidates=[x for x in familiar if x['id']!=w['id']]; rng.shuffle(candidates); candidates.sort(key=lambda x:(x['category']!=w['category'],x['pos']!=w['pos']))
                for x in candidates:
                    if typ=='picture_arabic' and x['image']==w['image']: continue
                    if {normal(s) for s in [w['arabic']]+w['variants']} & {normal(s) for s in [x['arabic']]+x['variants']}:continue
                    label=normal(x[key])
                    if label in unique or (key=='arabic' and (label in map(normal,w['variants']) or normal(w['arabic']) in map(normal,x['variants']))): continue
                    unique.add(label); distractors.append(x)
                    if len(distractors)==count-1: break
                if len(distractors)<count-1: abort(409,'Your parent needs to prepare more distinct familiar answer choices.')
                opts=[w]+distractors; rng.shuffle(opts)
                for x in opts:
                    token=secrets.token_urlsafe(12); qs['options'].append(dict(token=token,label=x[key]))
                    if x['id']==w['id']: qs['correct']=token
            questions.append(qs)
        return change('INSERT INTO quizzes(user_id,assignment_id,kind,level,created,questions) VALUES(?,?,?,?,?,?)',(uid,aid,kind,lvl,stamp(),json.dumps(questions,ensure_ascii=False))).lastrowid
    @app.post('/quiz/start')
    @require('child')
    def quiz_start():
        kind=request.form.get('kind','daily'); kind='level' if kind=='level' else 'daily'
        aid=int(request.form['assignment']) if kind=='daily' else None
        qid=make_quiz(aid,kind)
        return redirect(url_for('quiz_page',qid=qid))
    def owned_quiz(qid):
        q=one('SELECT * FROM quizzes WHERE id=? AND user_id=?',(qid,g.user['id']))
        if not q: abort(404)
        return q
    @app.get('/quiz/<int:qid>')
    @require('child')
    def quiz_page(qid):
        q=owned_quiz(qid)
        return render_template('quiz.html',qid=qid,completed=bool(q['completed']),kind=q['kind'])
    @app.get('/api/quiz/<int:qid>')
    @require('child')
    def quiz_data(qid):
        q=owned_quiz(qid); questions=json.loads(q['questions']); first=query('SELECT * FROM answers WHERE quiz_id=? AND first=1 ORDER BY q',(qid,))
        idx=len(first)
        if idx==5: return jsonify(completed=True,score=sum(r['correct'] for r in first),total=5,passed=q['kind']!='level' or sum(r['correct'] for r in first)>=4)
        x=questions[idx]; options=[]
        for o in x['options']:
            label=url_for('quiz_media',qid=qid,index=idx,kind='choice',token=o['token']) if x['type']=='audio_picture' else o['label']
            options.append(dict(token=o['token'],label=label))
        # No word id, English, spelling, picture, correct token or variants in audio prompts.
        return jsonify(index=idx,total=5,type=x['type'],options=options,audio=url_for('quiz_media',qid=qid,index=idx,kind='audio') if x['type'].startswith('audio') else '',image=url_for('quiz_media',qid=qid,index=idx,kind='image') if not x['type'].startswith('audio') else '',credit=x['image_credit'] if not x['type'].startswith('audio') else '')
    @app.get('/quiz-media/<int:qid>/<int:index>/<kind>')
    @require('child')
    def quiz_media(qid,index,kind):
        q=owned_quiz(qid); qs=json.loads(q['questions'])
        if not 0<=index<5: abort(404)
        x=qs[index]; answered=one('SELECT id FROM answers WHERE quiz_id=? AND q=? AND first=1',(qid,index))
        current=one('SELECT COUNT(*) n FROM answers WHERE quiz_id=? AND first=1',(qid,))['n']
        if index>current: abort(403)
        if kind=='image':
            if x['type'].startswith('audio') and not answered: abort(403)
            path=x['image']
        elif kind=='audio':
            if not x['type'].startswith('audio') and not answered: abort(403)
            path=x['audio']
        elif kind=='choice' and x['type']=='audio_picture':
            match=next((o for o in x['options'] if o['token']==request.args.get('token')),None)
            if not match: abort(404)
            path=match['label']
        else: abort(404)
        base=Path(app.config['UPLOAD_DIR']) if path.startswith('uploads/') else ROOT/'static'
        return send_from_directory(base,path.removeprefix('uploads/'))
    @app.post('/api/quiz/<int:qid>/answer')
    @require('child')
    def quiz_answer(qid):
        q=owned_quiz(qid); data=request.get_json(); idx=int(data['index']); qs=json.loads(q['questions'])
        if not 0<=idx<5: abort(400)
        current=one('SELECT COUNT(*) n FROM answers WHERE quiz_id=? AND first=1',(qid,))['n']
        if idx>current: abort(409)
        x=qs[idx]; answer=str(data.get('answer',''))[:200]
        previous=one('SELECT * FROM answers WHERE quiz_id=? AND q=? AND first=1',(qid,idx)); retry=bool(data.get('retry'))
        if previous and not retry: return jsonify(error='Already answered. Use correction to retry.'),409
        if retry and not previous: abort(400)
        if x['type']=='writing':
            correct=normal(answer) in {normal(s) for s in [x['expected']]+x['variants']}
            # English / Latin responses are never accepted.
            correct=correct and bool(re.search('[\u0621-\u064a]',answer)) and not bool(re.search('[A-Za-z]',answer))
            expected=min([x['expected']]+x['variants'],key=lambda s:sum(seg['kind']!='ok' for seg in arabic_feedback(answer,s)))
            feedback=arabic_feedback(answer,expected)
        else:
            if answer not in [o['token'] for o in x['options']]: abort(400)
            correct=answer==x['correct']; feedback=[]
        first=0 if previous else 1; modality='writing' if x['type']=='writing' else ('listening' if x['type'].startswith('audio') else 'reading')
        try: change('INSERT INTO answers(quiz_id,q,word_id,modality,answer,correct,first,created,feedback) VALUES(?,?,?,?,?,?,?,?,?)',(qid,idx,x['word'],modality,answer,int(correct),first,stamp(),json.dumps(feedback,ensure_ascii=False)))
        except sqlite3.IntegrityError: return jsonify(error='Answer already saved'),409
        if first and not correct:
            change('INSERT INTO review_queue VALUES(?,?,?,?) ON CONFLICT(user_id,word_id) DO UPDATE SET reason=excluded.reason,updated=excluded.updated',(g.user['id'],x['word'],'Quiz mistake',stamp()))
        if first and correct:
            change('DELETE FROM review_queue WHERE user_id=? AND word_id=?',(g.user['id'],x['word']))
        results=query('SELECT correct FROM answers WHERE quiz_id=? AND first=1',(qid,)); finished=len(results)==5
        if finished and not q['completed']:
            change('UPDATE quizzes SET completed=? WHERE id=?',(stamp(),qid))
            if q['kind']=='level' and sum(r['correct'] for r in results)>=4:
                change('INSERT OR IGNORE INTO level_reviews VALUES(?,?,?,?)',(g.user['id'],q['level'],qid,stamp()))
        return jsonify(correct=bool(correct),first=bool(first),feedback=feedback,expected=x['expected'],english=x['english'],credit=x['image_credit'],audio=url_for('quiz_media',qid=qid,index=idx,kind='audio'),image=url_for('quiz_media',qid=qid,index=idx,kind='image'),finished=finished)
    @app.post('/api/events')
    @require('child')
    def events():
        d=request.get_json(); uid=g.user['id']; kind=d.get('kind'); source=d.get('source'); wid=d.get('word')
        if kind not in ('visit','audio_start','audio_end','active') or source not in ('homework','review','explore','my_words','quiz'): abort(400)
        if source=='quiz':
            q=owned_quiz(int(d.get('quiz',0))); idx=int(d.get('index',0)); qs=json.loads(q['questions'])
            current=one('SELECT COUNT(*) n FROM answers WHERE quiz_id=? AND first=1',(q['id'],))['n']
            if not 0<=idx<5 or idx>current: abort(403)
            wid=qs[idx]['word']
        else:
            wid=int(wid or 0); w=word(wid)
            if not eligible(w): abort(403)
            if source=='homework':
                a=owned_assignment(int(d.get('assignment',0)))
                if wid not in [w['id'] for w in assignment_words(a)]: abort(403)
            elif source=='review':
                r=one('SELECT * FROM reviews WHERE id=? AND user_id=?',(d.get('review'),uid))
                if not r or wid not in json.loads(r['words']): abort(403)
            elif source=='explore':
                if not one('SELECT b.id FROM exploration_batches b JOIN json_each(b.words) j ON j.value=? WHERE b.user_id=? AND b.preview=0',(wid,uid)):abort(403)
                if kind=='visit':change('INSERT INTO exploration VALUES(?,?,?) ON CONFLICT(user_id,word_id) DO UPDATE SET visited=excluded.visited',(uid,wid,stamp()))
        eid=str(d.get('id',''))
        try: uuid.UUID(eid)
        except ValueError: abort(400)
        if one('SELECT id FROM events WHERE id=?',(eid,)): return jsonify(ok=True,duplicate=True)
        seconds=0
        if kind=='active':
            clock=time.time(); last=one('SELECT last FROM heartbeats WHERE user_id=?',(uid,)); elapsed=clock-last['last'] if last else 0
            seconds=max(0,min(float(d.get('seconds',0)),10,elapsed)) if elapsed<=16 else 0
            change('INSERT INTO heartbeats VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET last=excluded.last',(uid,clock))
        # A completed listen must reference one saved start, once.
        if kind=='audio_end':
            start=one('SELECT * FROM events WHERE id=? AND user_id=? AND word_id=? AND kind=?',(d.get('play_id',''),uid,wid,'audio_start'))
            if not start or start['source']!=source: abort(400)
            eid='end:'+start['id']
        change('INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?)',(eid,uid,wid,kind,source,seconds,stamp()))
        return jsonify(ok=True)
    @app.get('/admin')
    @require('parent')
    def admin():
        lvl=max(1,min(10,int(request.args.get('level',1)))); search=request.args.get('q','').lower(); state=request.args.get('state','')
        batch=words('WHERE level=? ORDER BY position',(lvl,)); all_words=words()
        counts={k:sum(bool(w[k]) for w in batch) for k in ('image','image_approved','audio','arabic_approved')}; counts['published']=sum(ready(w) for w in batch)
        if search: batch=[w for w in batch if search in (w['english']+' '+w['arabic']+' '+w['topic']).lower()]
        if state=='missing': batch=[w for w in batch if not ready(w)]
        return render_template('admin.html',words=batch,level=lvl,counts=counts,total_ready=sum(ready(w) for w in all_words),search=search,state=state)
    @app.get('/admin/preview')
    @app.get('/admin/preview/<page>')
    @require('parent')
    def parent_preview(page='home'):
        sample=words('WHERE level=1 ORDER BY position LIMIT 20')
        payload=dict(cards=[public_card(w) for w in sample],source='preview',position=0,done=[])
        preview_user=dict(name='Explorer',role='child')
        if page=='home': return render_template('home.html',level=1,completed=0,learned=0,preview_mode=True,user=preview_user)
        if page in ('daily','review'): return render_template('practice.html',title='Daily homework preview' if page=='daily' else 'Review preview',message='Parent preview only. Drafts may be missing your recordings or approved Arabic. Navigation is interactive; no child progress is saved.',payload=payload,preview_mode=True,user=preview_user)
        if page=='my_words': return render_template('my_words.html',words=sample,preview_mode=True,user=preview_user)
        if page=='journey': return render_template('journey.html',levels=[dict(level=l,assignments=0,cleared=False,review=False) for l in range(1,11)],preview_mode=True,user=preview_user)
        if page=='explore':
            return explore_view(preview=True)
        abort(404)
    def validate_arabic(text): return bool(text and re.search('[\u0621-\u064a]',text) and not re.search('[A-Za-z]',text))
    @app.route('/admin/word/<int:wid>',methods=['GET','POST'])
    @require('parent')
    def edit_word(wid):
        w=word(wid)
        if request.method=='POST':
            old=w.copy()
            for key in ('english','meaning','arabic','category','topic','pos','sentence','image_source','image_creator','image_license','content_note'): w[key]=request.form.get(key,w.get(key,''))[:4000].strip()
            if 'spellings' in request.form:
                spellings=list(dict.fromkeys(s.strip() for s in request.form['spellings'].splitlines() if s.strip()))
                w['arabic']=spellings[0] if spellings else ''
                w['variants']=spellings[1:]
            elif 'variants' in request.form:
                w['variants']=[s.strip() for s in request.form['variants'].splitlines() if s.strip()]
            if 'forms' in request.form:
                w['forms']=[s.strip() for s in request.form['forms'].splitlines() if s.strip()]
            w['arabic_approved']='arabic_approved' in request.form
            w['image_approved']='image_approved' in request.form
            w['published']='published' in request.form
            if w['category'] not in CATEGORIES: abort(400)
            if w['arabic_approved'] and (not validate_arabic(w['arabic']) or any(not validate_arabic(x) for x in w['variants'])):
                flash('Approved spellings must use Arabic letters.','error'); return redirect(url_for('edit_word',wid=wid))
            lvl=int(request.form.get('level',w['level'])); pos=int(request.form.get('position',w['position']))
            if not 1<=lvl<=10 or not 1<=pos<=200: abort(400)
            w.update(level=lvl,position=pos,day=(pos-1)//20+1)
            if w['published'] and not ready(w): flash('Publication requires an approved image, approved Arabic and a saved parent recording.','error'); w['published']=False
            try:
                if (lvl,pos)!=(old['level'],old['position']):
                    # Migration snapshots and issued slots remain immutable; only future plans change.
                    other=one('SELECT * FROM words WHERE level=? AND position=?',(lvl,pos)); ow=json.loads(other['data'])
                    db().execute('UPDATE words SET position=-1 WHERE id=?',(wid,))
                    ow.update(level=old['level'],position=old['position'],day=old['day'])
                    db().execute('UPDATE words SET level=?,position=?,data=? WHERE id=?',(ow['level'],ow['position'],json.dumps(ow,ensure_ascii=False),ow['id']))
                    db().execute('INSERT INTO placement_history(parent_id,word_id,other_id,old_level,old_position,new_level,new_position,created) VALUES(?,?,?,?,?,?,?,?)',(g.user['id'],wid,ow['id'],old['level'],old['position'],lvl,pos,stamp()))
                db().execute('UPDATE words SET english=?,level=?,position=?,data=? WHERE id=?',(w['english'],lvl,pos,json.dumps(w,ensure_ascii=False),wid))
                if (lvl,pos)!=(old['level'],old['position']):
                    for u in query("SELECT id FROM users WHERE role='child'"):rebuild_plan(db(),u['id'])
                    flash(f'Moved {w["english"]} to level {lvl}, slot {pos}; {ow["english"]} takes its previous slot. Issued homework and quiz history are unchanged. Future homework has been rebalanced without duplicate entries.','success')
                db().commit()
                flash('Card saved.','success')
            except sqlite3.IntegrityError:
                db().rollback(); flash('That English entry already exists. Keep the 2,000 entries distinct.','error')
            return redirect(url_for('edit_word',wid=wid))
        return render_template('edit.html',w=w,examples=query('SELECT * FROM word_examples WHERE word_id=? ORDER BY created,id',(wid,)),payload={'cards':[public_card(w)],'source':'preview','position':0,'done':[]})
    @app.get('/api/admin/move-preview')
    @require('parent')
    def move_preview():
        w=word(int(request.args['word']));lvl=int(request.args['level']);pos=int(request.args['position']);other=one('SELECT data FROM words WHERE level=? AND position=?',(lvl,pos))
        if not other:abort(400)
        ow=json.loads(other['data']);issued=one('SELECT COUNT(DISTINCT a.user_id) n FROM assignment_cards c JOIN assignments a ON c.assignment_id=a.id WHERE c.word_id IN (?,?)',(w['id'],ow['id']))['n']
        return jsonify(other=ow['english'],issued_children=issued,message=f'Swap with “{ow["english"]}”. Both levels remain at 200 entries. Issued assignments for {issued} child account(s) stay unchanged; future slots are rebalanced. Already assigned words will not be assigned again.')
    @app.post('/admin/word/<int:wid>/upload/<kind>')
    @require('parent')
    def upload(wid,kind):
        w=word(wid)
        if kind not in ('audio','image','sentence_audio'): abort(400)
        f=request.files.get('file')
        if not f: abort(400)
        data=f.read(); dest=Path(app.config['UPLOAD_DIR']); name=uuid.uuid4().hex
        if kind=='image':
            try:
                im=Image.open(io.BytesIO(data)); im.load()
                if im.width*im.height>16000000: abort(400)
                im=ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((800,800)); filename=name+'.jpg'; im.save(dest/filename,quality=88)
            except (OSError,Image.DecompressionBombError): abort(400,'Use a valid PNG, JPEG or WebP image.')
            w['image_approved']=False
        else:
            path=save_audio(data);filename=path.removeprefix('uploads/')
        # Keep old recordings for backup/history; never overwrite them.
        w[kind]='uploads/'+filename; w['published']=False
        change('UPDATE words SET data=? WHERE id=?',(json.dumps(w,ensure_ascii=False),wid))
        return jsonify(ok=True,url=asset_url(w[kind]),message='Saved. Review the card and publish when ready.')
    def save_audio(data):
        # Signature validation is shared by pronunciation and optional examples.
        if data.startswith(b'\x1a\x45\xdf\xa3'):ext='.webm'
        elif data.startswith(b'OggS'):ext='.ogg'
        elif data.startswith(b'RIFF') and data[8:12]==b'WAVE':ext='.wav'
        elif len(data)>12 and data[4:8]==b'ftyp':ext='.m4a'
        elif data.startswith(b'ID3') or data[:2] in (b'\xff\xfb',b'\xff\xf3',b'\xff\xf2'):ext='.mp3'
        else:abort(400,'Upload a real WebM, Ogg, WAV, M4A or MP3 recording.')
        if len(data)<100:abort(400,'Recording is empty.')
        filename=uuid.uuid4().hex+ext;path=Path(app.config['UPLOAD_DIR'])/filename
        path.write_bytes(data);path.chmod(0o600)
        return 'uploads/'+filename
    @app.post('/admin/word/<int:wid>/examples')
    @app.post('/admin/word/<int:wid>/examples/<eid>')
    @require('parent')
    def edit_example(wid,eid=None):
        word(wid)
        existing=one('SELECT * FROM word_examples WHERE id=? AND word_id=?',(eid,wid)) if eid else None
        if eid and not existing:abort(404)
        action=request.form.get('action','save')
        if action not in ('save','delete'):abort(400)
        if action=='delete':
            if not existing:abort(404)
            change('DELETE FROM word_examples WHERE id=?',(eid,))
            # Retain original media privately for backups, as with replaced pronunciation.
            flash('Example removed.','success')
            return redirect(url_for('edit_word',wid=wid))
        f=request.files.get('file')
        if not existing and not f:abort(400,'Record or upload an example first.')
        label=request.form.get('label',existing['label'] if existing else '').strip()
        if len(label)>160:abort(400,'Use a label of at most 160 characters.')
        audio=save_audio(f.read()) if f else existing['audio']
        if existing:change('UPDATE word_examples SET label=?,audio=?,updated=? WHERE id=?',(label,audio,stamp(),eid))
        else:
            eid=uuid.uuid4().hex
            change('INSERT INTO word_examples VALUES(?,?,?,?,?,?)',(eid,wid,label,audio,stamp(),stamp()))
        if f:return jsonify(ok=True,id=eid,url=url_for('example_media',eid=eid))
        flash('Example label saved.','success')
        return redirect(url_for('edit_word',wid=wid))
    @app.route('/admin/children',methods=['GET','POST'])
    @require('parent')
    def children():
        if request.method=='POST':
            uid=request.form.get('id'); name=request.form.get('name','').strip(); username=request.form.get('username','').strip(); password=request.form.get('password','')
            if not name or not username or (not uid and len(password)<8) or (password and len(password)<8): flash('Name, username and an 8-character password are required for a new child.','error')
            else:
                try:
                    if uid:
                        u=one('SELECT * FROM users WHERE id=? AND role=?',(uid,'child'))
                        if not u: abort(404)
                        change('UPDATE users SET name=?,username=?,hash=?,enabled=?,review_only=? WHERE id=?',(name,username,generate_password_hash(password) if password else u['hash'],int('enabled' in request.form),int('review_only' in request.form),uid))
                    else: change('INSERT INTO users(username,name,hash,role) VALUES(?,?,?,?)',(username,name,generate_password_hash(password),'child'))
                    flash('Child account saved.','success')
                except sqlite3.IntegrityError: flash('That username is already taken.','error')
            return redirect(url_for('children'))
        return render_template('children.html',children=query("SELECT * FROM users WHERE role='child' ORDER BY id"))
    @app.route('/admin/settings',methods=['GET','POST'])
    @require('parent')
    def settings():
        if request.method=='POST':
            tz=request.form.get('timezone','America/Toronto')
            try: ZoneInfo(tz)
            except Exception: flash('Use an IANA timezone, such as America/Toronto.','error'); return redirect(url_for('settings'))
            choices=request.form.get('quiz_choices','4')
            if choices not in ('4','5'): abort(400)
            for k,v in [('timezone',tz),('quiz_choices',choices),('audio_picture','1' if 'audio_picture' in request.form else '0')]: change('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,v))
            flash('Settings saved.','success')
        return render_template('settings.html',timezone=setting('timezone','America/Toronto'),choices=setting('quiz_choices','4'),audio_picture=setting('audio_picture','0')=='1')
    def analytics(uid,period):
        cutoff=(now()-timedelta(days=6)).date().isoformat() if period=='week' else (today() if period=='today' else '0000')
        activity=query('SELECT * FROM events WHERE user_id=? AND created>=?',(uid,cutoff))
        answers=query('SELECT a.*,q.kind quiz_kind FROM answers a JOIN quizzes q ON a.quiz_id=q.id WHERE q.user_id=? AND a.created>=?',(uid,cutoff))
        rows={}; trends={}
        def row(wid):
            if wid not in rows: rows[wid]=dict(id=wid,english=word(wid)['english'],visits=0,plays=0,listens=0,seconds=0,attempts=0,first=0,correct=0,last='',sources={},modalities={},later_correct=0,mastery='Practicing')
            return rows[wid]
        for e in activity:
            r=row(e['word_id']); r['last']=max(r['last'],e['created']); s=r['sources'].setdefault(e['source'],dict(visits=0,plays=0,listens=0,seconds=0)); day=e['created'][:10]; t=trends.setdefault(day,dict(seconds=0,new=set(),review=set(),first=0,correct=0,later=0))
            if e['kind']=='visit': r['visits']+=1; s['visits']+=1
            if e['kind']=='audio_start': r['plays']+=1; s['plays']+=1
            if e['kind']=='audio_end': r['listens']+=1; s['listens']+=1
            if e['kind']=='active': r['seconds']+=e['seconds']; s['seconds']+=e['seconds']; t['seconds']+=e['seconds']
            if e['kind']=='visit' and e['source']=='review': t['review'].add(e['word_id'])
        for p in query('SELECT word_id,completed FROM practice WHERE user_id=? AND completed>=?',(uid,cutoff)):
            day=p['completed'][:10]; trends.setdefault(day,dict(seconds=0,new=set(),review=set(),first=0,correct=0,later=0))['new'].add(p['word_id'])
        for a in answers:
            r=row(a['word_id']); r['attempts']+=1; r['first']+=a['first']; r['correct']+=a['correct'] if a['first'] else 0; r['last']=max(r['last'],a['created']); m=r['modalities'].setdefault(a['modality'],dict(first=0,correct=0,retries=0)); m['first']+=a['first']; m['correct']+=a['correct'] if a['first'] else 0; m['retries']+=not a['first']
            t=trends.setdefault(a['created'][:10],dict(seconds=0,new=set(),review=set(),first=0,correct=0,later=0)); t['first']+=a['first']; t['correct']+=a['correct'] if a['first'] else 0
            if a['first'] and a['correct'] and one('SELECT a.id FROM answers a JOIN quizzes q ON a.quiz_id=q.id WHERE q.user_id=? AND a.word_id=? AND a.first=1 AND a.created<? AND substr(a.created,1,10)<substr(?,1,10) LIMIT 1',(uid,a['word_id'],a['created'],a['created'])):
                r['later_correct']+=1; t['later']+=1
        for r in rows.values():
            evidence=query('SELECT DISTINCT substr(a.created,1,10) day,a.modality FROM answers a JOIN quizzes q ON a.quiz_id=q.id WHERE q.user_id=? AND a.word_id=? AND a.first=1 AND a.correct=1',(uid,r['id']))
            if len({e['day'] for e in evidence})>=3 and len({e['modality'] for e in evidence})>=2: r['mastery']='Growing confidence'
            r['accuracy']=round(100*r['correct']/r['first']) if r['first'] else None
        chart=[dict(day=d,minutes=round(t['seconds']/60,1),new=len(t['new']),review=len(t['review']),accuracy=round(100*t['correct']/t['first']) if t['first'] else None,later=t['later']) for d,t in sorted(trends.items())]
        qu=query('SELECT * FROM quizzes WHERE user_id=? AND created>=?',(uid,cutoff))
        return dict(rows=list(rows.values()),chart=chart,seconds=sum(r['seconds'] for r in rows.values()),distinct=sum(r['visits']>0 for r in rows.values()),visits=sum(r['visits'] for r in rows.values()),first=sum(r['first'] for r in rows.values()),correct=sum(r['correct'] for r in rows.values()),quiz_started=len(qu),quiz_completed=sum(bool(q['completed']) for q in qu),retries=sum(not a['first'] for a in answers),cutoff=cutoff)
    @app.get('/admin/analytics')
    @require('parent')
    def analytics_page():
        cs=query("SELECT id,name FROM users WHERE role='child'"); uid=int(request.args.get('child',cs[0]['id'] if cs else 0)); period=request.args.get('period','week'); filt=request.args.get('filter','')
        if uid and uid not in [c['id'] for c in cs]: abort(404)
        result=analytics(uid,period); result['rows']=[r for r in result['rows'] if not filt or (filt=='replays' and r['plays']>=3) or (filt=='mistakes' and r['first']-r['correct']>=2) or (filt=='untested' and r['visits'] and not r['first']) or (filt=='retention' and r['later_correct'])]
        return render_template('analytics.html',children=cs,child=uid,period=period,filter=filt,result=result)
    @app.get('/admin/analytics/<int:uid>/word/<int:wid>')
    @require('parent')
    def word_analytics(uid,wid):
        if not one("SELECT id FROM users WHERE id=? AND role='child'",(uid,)): abort(404)
        result=analytics(uid,'all'); r=next((r for r in result['rows'] if r['id']==wid),None)
        attempts=[dict(a,segments=json.loads(a['feedback'])) for a in query('SELECT a.*,q.kind quiz_kind FROM answers a JOIN quizzes q ON a.quiz_id=q.id WHERE q.user_id=? AND a.word_id=? ORDER BY a.id',(uid,wid))]
        return render_template('word_analytics.html',w=word(wid),r=r,attempts=attempts)
    @app.get('/admin/export')
    @require('parent')
    def export():
        # Consistent SQLite backup includes progress and password hashes; parent only.
        buf=io.BytesIO(); backup=Path(app.config['DATABASE']).parent/('backup-'+uuid.uuid4().hex+'.sqlite3')
        connection=sqlite3.connect(backup); db().backup(connection); connection.close()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            z.write(backup,'learning.sqlite3'); z.writestr('curriculum.json',json.dumps(words(),ensure_ascii=False,indent=2)); z.writestr('RESTORE.txt','Stop the app. Back up instance first. Replace instance/learning.sqlite3 and instance/media from this archive. Images in static/images ship with the project. This backup contains private account hashes and progress; keep it private. Session secrets are deliberately excluded. Read README for complete restore instructions.')
            for p in Path(app.config['UPLOAD_DIR']).glob('*'):
                if p.is_file(): z.write(p,'media/'+p.name)
        backup.unlink(); buf.seek(0)
        return send_file(buf,mimetype='application/zip',as_attachment=True,download_name='arabic-family-backup-'+today()+'.zip')
    @app.get('/credits')
    def credits(): return render_template('credits.html')
    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def error(e):
        if request.path.startswith('/api/') or '/upload/' in request.path or (request.endpoint=='edit_example' and request.headers.get('X-CSRF-Token')): return jsonify(error=e.description),e.code
        return render_template('error.html',error=e),e.code
    app.helpers=dict(db=db,word=word,ready=ready,analytics=analytics)
    return app

if __name__=='__main__':
    app=create_app()
    print('Local family preview: http://127.0.0.1:5000 — create your parent account on first visit.')
    app.run(host='127.0.0.1',port=5000,debug=False)
