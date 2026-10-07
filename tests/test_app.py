import io, json, shutil, sqlite3, tempfile, unittest, uuid, wave
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.security import generate_password_hash
from app import create_app, arabic_feedback, normal

class FamilyAppTests(unittest.TestCase):
    def setUp(self):
        local=Path(__file__).resolve().parents[1]/'test-output';local.mkdir(exist_ok=True)
        self.root=local/('test-'+uuid.uuid4().hex);self.root.mkdir()
        self.app=create_app({'TESTING':True,'DATABASE':str(self.root/'test.sqlite3'),'UPLOAD_DIR':str(self.root/'media'),'SECRET_KEY':'test-only-not-for-serving'})
        self.c=self.app.test_client()
        with self.app.app_context():
            db=self.app.helpers['db']()
            for name,role in [('parent','parent'),('child1','child'),('child2','child')]: db.execute('INSERT INTO users(username,name,hash,role) VALUES(?,?,?,?)',(name,name,generate_password_hash('testing-password'),role))
            # Silent audio is a TEST FIXTURE only. It is not shipped as parent content.
            audio=self.root/'media/test.wav'
            with wave.open(str(audio),'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b'\0'*16000)
            for r in db.execute('SELECT id,data FROM words WHERE level=1').fetchall():
                w=json.loads(r['data']); w.update(arabic='كلمة'+self.arabic_number(w['id']),variants=[],arabic_approved=True,image='images/arasaac-2447.png',image_approved=True,audio='uploads/test.wav',published=True)
                # Use an existing first-level image independent of sourcing choices.
                original=json.loads(r['data'])
                w['image']=original['image'] or json.loads(db.execute('SELECT data FROM words WHERE id=1').fetchone()[0])['image']
                db.execute('UPDATE words SET data=? WHERE id=?',(json.dumps(w),w['id']))
            db.commit()
        self.login('child1')
    @staticmethod
    def arabic_number(n): return ''.join(chr(0x0660+int(c)) for c in str(n))
    def tearDown(self):
        intended=(Path(__file__).resolve().parents[1]/'test-output').resolve()
        assert self.root.resolve().is_relative_to(intended) and self.root.name.startswith('test-')
        shutil.rmtree(self.root)
    def login(self,username):
        self.c.get('/login')
        with self.c.session_transaction() as s: csrf=s['csrf']
        r=self.c.post('/login',data={'username':username,'password':'testing-password','csrf':csrf})
        self.assertEqual(r.status_code,302)
    def post(self,path,data=None,form=False):
        with self.c.session_transaction() as s: csrf=s['csrf']
        return self.c.post(path,data=(dict(data or {},csrf=csrf) if form else None),json=(None if form else data),headers={} if form else {'X-CSRF-Token':csrf})
    def sql(self,sql,args=()):
        with self.app.app_context():
            db=self.app.helpers['db'](); result=db.execute(sql,args).fetchall(); db.commit(); return result
    def complete(self):
        self.c.get('/daily'); a=self.sql('SELECT * FROM assignments ORDER BY id DESC LIMIT 1')[0]; ids=self.sql('SELECT id FROM words WHERE level=? AND position BETWEEN ? AND ? ORDER BY position',(a['level'],(a['day']-1)*20+1,a['day']*20))
        for i,r in enumerate(ids): self.assertEqual(self.post('/api/practice',dict(assignment=a['id'],word=r['id'],position=i,complete=True)).status_code,200)
        return a['id']
    def start_quiz(self,aid):
        r=self.post('/quiz/start',dict(assignment=aid),form=True); self.assertEqual(r.status_code,302); return int(r.location.split('/')[-1])
    def test_auth_and_account_isolation(self):
        self.assertEqual(self.c.get('/admin').status_code,403)
        aid=self.complete(); qid=self.start_quiz(aid); self.login('child2')
        self.assertEqual(self.post('/api/practice',dict(assignment=aid,word=1,complete=True)).status_code,404)
        self.assertEqual(self.c.get(f'/api/quiz/{qid}').status_code,404)
        self.assertEqual(self.c.get('/admin/export').status_code,403)
        self.assertEqual(self.post('/api/events',dict(id=str(uuid.uuid4()),word=1,source='homework',assignment=aid,kind='visit')).status_code,404)
    def test_csrf_enforced(self): self.assertEqual(self.c.post('/api/practice',json={}).status_code,400)
    def test_curriculum_and_scheduling(self):
        rows=self.sql('SELECT level,COUNT(*) n FROM words GROUP BY level'); self.assertEqual([r['n'] for r in rows],[200]*10)
        self.c.get('/daily'); a=self.sql('SELECT * FROM assignments')[0]
        self.post('/api/practice',dict(assignment=a['id'],word=6,position=5,complete=True)); self.c.get('/daily'); self.assertEqual(self.sql('SELECT position FROM assignments')[0]['position'],5)
        aid=self.complete(); self.post('/api/practice',dict(assignment=aid,word=1,position=0,complete=True)); self.assertEqual(len(self.sql('SELECT * FROM practice')),20)
        self.c.get('/daily'); self.assertEqual(len(self.sql('SELECT * FROM assignments')),1)
        self.sql('UPDATE assignments SET completed=? WHERE id=?',('2020-01-01T10:00:00-05:00',aid)); self.c.get('/daily')
        self.assertEqual(self.sql('SELECT day FROM assignments ORDER BY id DESC LIMIT 1')[0]['day'],2)
    def test_unpublished_homework_is_not_exposed(self):
        r=self.sql('SELECT data FROM words WHERE id=1')[0]; w=json.loads(r['data']);w['published']=False;self.sql('UPDATE words SET data=? WHERE id=1',(json.dumps(w),))
        response=self.c.get('/daily');self.assertNotIn(b'parent recording',response.data);self.assertEqual(len(self.sql('SELECT * FROM assignments')),0)
        self.assertEqual(self.c.get('/word/1').status_code,403)
    def test_exploration_separate_and_random_batch(self):
        self.c.get('/explore?category=Conversation+and+describing');first=json.loads(self.sql('SELECT words FROM exploration_batches ORDER BY created DESC LIMIT 1')[0][0]);self.assertEqual(len(set(first)),10);self.assertEqual(len(self.sql('SELECT * FROM exploration')),0);self.assertEqual(len(self.sql('SELECT * FROM assignments')),0)
        self.c.get('/explore?category=Conversation+and+describing');second=json.loads(self.sql('SELECT words FROM exploration_batches ORDER BY created DESC LIMIT 1')[0][0]);self.assertNotEqual(first,second)
        self.c.get('/daily'); self.assertEqual(self.sql('SELECT day FROM assignments')[0]['day'],1)
    def test_preview_next_matching_level(self):
        with self.app.app_context():
            w=self.app.helpers['word'](201);w.update(category='Family and friends',topic='Unique preview',arabic='أهل',arabic_approved=True,image=self.app.helpers['word'](1)['image'],image_approved=True,audio='uploads/test.wav',published=True)
            self.app.helpers['db']().execute('UPDATE words SET data=? WHERE id=201',(json.dumps(w),));self.app.helpers['db']().commit()
        r=self.c.get('/explore?category=Family+and+friends&topic=Unique+preview'); self.assertIn(b'across all ten levels',r.data)
        self.assertEqual(self.c.get('/word/201').status_code,200)
        self.assertEqual(len(self.sql('SELECT * FROM assignments')),0)
    def test_quiz_hidden_answers_and_unique_words(self):
        aid=self.complete();qid=self.start_quiz(aid);q=self.c.get(f'/api/quiz/{qid}').json
        self.assertEqual(q['type'],'audio_english');self.assertEqual(len(q['options']),4)
        for key in ['word','english','arabic','correct','expected','variants']:self.assertNotIn(key,q)
        self.assertEqual(q['image'],'');self.assertEqual(self.c.get(f'/quiz-media/{qid}/0/image').status_code,403)
        qs=json.loads(self.sql('SELECT questions FROM quizzes WHERE id=?',(qid,))[0]['questions']);self.assertEqual(len(set(q['word'] for q in qs)),5)
        self.assertEqual(len(set(o['label'] for o in qs[0]['options'])),4)
    def test_first_answer_retries_and_review_priority(self):
        aid=self.complete();qid=self.start_quiz(aid);qs=json.loads(self.sql('SELECT questions FROM quizzes WHERE id=?',(qid,))[0]['questions']);x=qs[0];wrong=next(o['token'] for o in x['options'] if o['token']!=x['correct'])
        r=self.post(f'/api/quiz/{qid}/answer',dict(index=0,answer=wrong));self.assertFalse(r.json['correct']);self.assertTrue(r.json['first'])
        self.assertEqual(self.post(f'/api/quiz/{qid}/answer',dict(index=0,answer=x['correct'])).status_code,409)
        r=self.post(f'/api/quiz/{qid}/answer',dict(index=0,answer=x['correct'],retry=True));self.assertFalse(r.json['first']);self.assertTrue(r.json['correct'])
        self.assertEqual(len(self.sql('SELECT * FROM review_queue')),1)
        self.sql('UPDATE assignments SET completed=? WHERE id=?',('2020-01-01',aid));self.c.get('/daily');self.c.get('/review')
        self.assertIn(x['word'],json.loads(self.sql('SELECT words FROM reviews')[0]['words']))
        with self.app.app_context():
            result=self.app.helpers['analytics'](2,'all');self.assertEqual(result['first'],1);self.assertEqual(result['correct'],0);self.assertEqual(result['retries'],1)
    def test_quiz_resume_and_writing_variants(self):
        qid=self.start_quiz(self.complete());qs=json.loads(self.sql('SELECT questions FROM quizzes WHERE id=?',(qid,))[0]['questions'])
        for i,x in enumerate(qs[:4]):self.post(f'/api/quiz/{qid}/answer',dict(index=i,answer=x['correct']))
        self.assertEqual(self.c.get(f'/api/quiz/{qid}').json['type'],'writing')
        self.assertEqual(self.c.get(f'/api/quiz/{qid}').json['index'],4)
        qs[4]['variants']=['كتاب'];qs[4]['expected']='كتّاب';self.sql('UPDATE quizzes SET questions=? WHERE id=?',(json.dumps(qs),qid))
        r=self.post(f'/api/quiz/{qid}/answer',dict(index=4,answer='كِتاب'));self.assertTrue(r.json['correct']);self.assertTrue(r.json['finished'])
        self.assertEqual(self.c.get(f'/api/quiz/{qid}').json['score'],5)
        self.login('parent');r=self.c.get(f'/admin/analytics/2/word/{qs[4]["word"]}');self.assertEqual(r.status_code,200);self.assertIn(b'spelling-inline',r.data)
    def test_latin_writing_not_accepted(self):
        qid=self.start_quiz(self.complete());qs=json.loads(self.sql('SELECT questions FROM quizzes WHERE id=?',(qid,))[0]['questions'])
        for i,x in enumerate(qs[:4]):self.post(f'/api/quiz/{qid}/answer',dict(index=i,answer=x['correct']))
        r=self.post(f'/api/quiz/{qid}/answer',dict(index=4,answer='kitab'));self.assertFalse(r.json['correct'])
    def test_event_dedup_and_listens(self):
        self.c.get('/daily');aid=self.sql('SELECT id FROM assignments')[0]['id'];base=dict(word=1,assignment=aid,source='homework');eid=str(uuid.uuid4());e=dict(base,id=eid,kind='visit')
        self.post('/api/events',e);self.post('/api/events',e);start=str(uuid.uuid4());self.post('/api/events',dict(base,id=start,kind='audio_start'))
        for _ in range(2): self.post('/api/events',dict(base,id=str(uuid.uuid4()),kind='audio_end',play_id=start))
        self.assertEqual(len(self.sql("SELECT * FROM events WHERE kind='visit'")),1);self.assertEqual(len(self.sql("SELECT * FROM events WHERE kind='audio_end'")),1)
        with self.app.app_context():
            a=self.app.helpers['analytics'](2,'all');self.assertEqual(a['distinct'],1);self.assertEqual(a['visits'],1);self.assertEqual(a['rows'][0]['plays'],1);self.assertEqual(a['rows'][0]['listens'],1)
    def test_active_time_caps_idle_and_elapsed(self):
        self.c.get('/daily');aid=self.sql('SELECT id FROM assignments')[0]['id'];base=dict(word=1,assignment=aid,source='homework',kind='active',seconds=3600)
        self.post('/api/events',dict(base,id=str(uuid.uuid4())));import time
        self.sql('UPDATE heartbeats SET last=? WHERE user_id=2',(time.time()-5,));self.post('/api/events',dict(base,id=str(uuid.uuid4())))
        seconds=self.sql("SELECT SUM(seconds) n FROM events")[0]['n'];self.assertGreaterEqual(seconds,5);self.assertLess(seconds,6)
        self.sql('UPDATE heartbeats SET last=? WHERE user_id=2',(time.time()-1000,));self.post('/api/events',dict(base,id=str(uuid.uuid4())));self.assertEqual(self.sql('SELECT seconds FROM events ORDER BY rowid DESC LIMIT 1')[0]['seconds'],0)
    def test_admin_upload_and_publish_gate(self):
        self.login('parent');self.assertEqual(self.c.get('/admin').status_code,200);self.assertEqual(self.c.get('/admin/word/1').status_code,200)
        with self.c.session_transaction() as s: csrf=s['csrf']
        response=self.c.post('/admin/word/1/upload/audio',data={'file':(io.BytesIO(b'not an audio recording'),'fake.wav')},headers={'X-CSRF-Token':csrf});self.assertEqual(response.status_code,400)
        response=self.c.post('/admin/word/1/upload/audio',data={'file':(io.BytesIO((self.root/'media/test.wav').read_bytes()),'recording.wav')},headers={'X-CSRF-Token':csrf});self.assertEqual(response.status_code,200)
        self.assertFalse(json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0])['published'])
        response=self.c.get('/admin/export');self.assertEqual(response.status_code,200);import zipfile
        with zipfile.ZipFile(io.BytesIO(response.data)) as z:self.assertIn('learning.sqlite3',z.namelist());self.assertIn('media/test.wav',z.namelist())
    def test_parent_pages(self):
        self.complete();self.login('parent')
        for path in ['/admin','/admin/word/1','/admin/children','/admin/settings','/admin/analytics','/admin/analytics/2/word/1','/credits','/admin/preview','/admin/preview/daily','/admin/preview/explore?category=Food+and+ingredients','/admin/preview/my_words','/admin/preview/journey']: self.assertEqual(self.c.get(path).status_code,200,path)
    def test_level_completion_requires_ten_assignments_and_four_first_answers(self):
        self.assertEqual(self.post('/quiz/start',dict(kind='level'),form=True).status_code,409)
        for day in range(1,11):self.sql('INSERT INTO assignments(user_id,level,day,created,completed) VALUES(2,1,?,?,?)',(day,'2020-01-01','2020-01-01'))
        self.c.get('/daily');self.assertEqual(len(self.sql('SELECT * FROM assignments')),10)
        # Familiar pool for plausible distractors.
        aid=self.sql('SELECT id FROM assignments LIMIT 1')[0][0]
        for wid in range(1,201):self.sql('INSERT INTO practice VALUES(2,?,?,?)',(aid,wid,'2020-01-01'))
        r=self.post('/quiz/start',dict(kind='level'),form=True);self.assertEqual(r.status_code,302);qid=int(r.location.split('/')[-1]);qs=json.loads(self.sql('SELECT questions FROM quizzes WHERE id=?',(qid,))[0][0])
        for i,x in enumerate(qs):self.post(f'/api/quiz/{qid}/answer',dict(index=i,answer=x['correct'] if i<4 else 'wrong'))
        self.assertEqual(len(self.sql('SELECT * FROM level_reviews')),1)
        self.c.get('/daily');self.assertEqual(len(self.sql('SELECT * FROM assignments')),10) # Next-level content is not ready.
    def test_four_choices_cannot_contain_ambiguous_arabic_labels(self):
        aid=self.complete();w=json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0]);w['arabic']='نفس';self.sql('UPDATE words SET data=? WHERE id=1',(json.dumps(w),));w2=json.loads(self.sql('SELECT data FROM words WHERE id=2')[0][0]);w2['arabic']='نَفْس';self.sql('UPDATE words SET data=? WHERE id=2',(json.dumps(w2),))
        qid=self.start_quiz(aid);qs=json.loads(self.sql('SELECT questions FROM quizzes WHERE id=?',(qid,))[0][0]);labels=[normal(o['label']) for o in qs[3]['options']];self.assertEqual(len(set(labels)),4)
    def test_later_day_confidence_and_retention_exclude_retries(self):
        aid=self.complete();qid=self.start_quiz(aid)
        for day,modality in [('2020-01-01','listening'),('2020-01-02','listening'),('2020-01-03','writing')]:self.sql('INSERT INTO answers(quiz_id,q,word_id,modality,answer,correct,first,created,feedback) VALUES(?,99,1,?,?,1,0,?,?)',(qid,modality,'x',day,'[]'))
        with self.app.app_context():r=next(r for r in self.app.helpers['analytics'](2,'all')['rows'] if r['id']==1);self.assertEqual(r['mastery'],'Practicing');self.assertEqual(r['first'],0)
        for i,(day,modality) in enumerate([('2020-01-01','listening'),('2020-01-02','listening'),('2020-01-03','writing')]):self.sql('INSERT INTO answers(quiz_id,q,word_id,modality,answer,correct,first,created,feedback) VALUES(?,?,1,?,?,1,1,?,?)',(qid,90+i,modality,'x',day,'[]'))
        with self.app.app_context():r=next(r for r in self.app.helpers['analytics'](2,'all')['rows'] if r['id']==1);self.assertEqual(r['mastery'],'Growing confidence');self.assertEqual(r['later_correct'],2)
    def test_review_empty_first_assignment_and_stable_five_word_batch(self):
        self.c.get('/daily');self.c.get('/review');self.assertEqual(json.loads(self.sql('SELECT words FROM reviews')[0][0]),[])
        aid=self.complete();self.sql('UPDATE assignments SET completed=? WHERE id=?',('2020-01-01',aid));self.c.get('/daily');self.c.get('/review');ids=json.loads(self.sql('SELECT words FROM reviews ORDER BY id DESC LIMIT 1')[0][0]);self.assertEqual(len(set(ids)),5);self.assertTrue(all(1<=wid<=20 for wid in ids));self.c.get('/review');self.assertEqual(json.loads(self.sql('SELECT words FROM reviews ORDER BY id DESC LIMIT 1')[0][0]),ids)
    def test_audio_picture_requires_distinct_pictures(self):
        aid=self.complete();self.sql("INSERT INTO settings VALUES('audio_picture','1')")
        # Deliberately identical picture fixtures must never produce an ambiguous quiz.
        with self.app.app_context():
            db=self.app.helpers['db']();image=self.app.helpers['word'](1)['image']
            for r in db.execute('SELECT id,data FROM words WHERE id<=20').fetchall():
                w=json.loads(r['data']);w['image']=image;db.execute('UPDATE words SET data=? WHERE id=?',(json.dumps(w),r['id']))
            db.commit()
        self.assertEqual(self.post('/quiz/start',dict(assignment=aid),form=True).status_code,409)
    def test_unpublished_upload_is_private_to_parent(self):
        self.login('parent')
        with self.c.session_transaction() as s:csrf=s['csrf']
        r=self.c.post('/admin/word/1/upload/audio',data={'file':(io.BytesIO((self.root/'media/test.wav').read_bytes()),'recording.wav')},headers={'X-CSRF-Token':csrf});path=r.json['url'];response=self.c.get(path);self.assertEqual(response.status_code,200);response.close()
        self.login('child2');self.assertEqual(self.c.get(path).status_code,403)
    def test_review_only_does_not_change_assignments(self):
        self.sql('UPDATE users SET review_only=1 WHERE id=2');self.c.get('/daily');self.assertEqual(len(self.sql('SELECT * FROM assignments')),0)
    def test_started_level_move_preserves_snapshot(self):
        self.c.get('/daily');self.login('parent');w=json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0]);data={k:w[k] for k in ['english','meaning','arabic','category','topic','pos','level']};data['position']=2
        self.post('/admin/word/1',data,form=True);self.assertEqual(self.sql('SELECT position FROM words WHERE id=1')[0][0],2);self.assertEqual(self.sql('SELECT word_id FROM assignment_cards ORDER BY position LIMIT 1')[0][0],1)
    def test_unstarted_swap_keeps_counts(self):
        self.login('parent');w=json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0]);data={k:w[k] for k in ['english','meaning','arabic','category','topic','pos','level']};data['position']=2
        self.post('/admin/word/1',data,form=True);self.assertEqual(self.sql('SELECT position FROM words WHERE id=1')[0][0],2);self.assertEqual(self.sql('SELECT position FROM words WHERE id=2')[0][0],1)
    def test_alignment(self):
        self.assertEqual(normal('كِتَاب'),'كتاب')
        wrong=arabic_feedback('كتلب','كتاب');self.assertEqual([s['kind'] for s in wrong],['ok','ok','wrong','ok'])
        missing=arabic_feedback('كتب','كتاب');self.assertEqual(sum(s['kind']=='missing' for s in missing),1)
        extra=arabic_feedback('كتتاب','كتاب');self.assertEqual(sum(s['kind']=='extra' for s in extra),1)
        self.assertEqual(sum(s['kind']!='ok' for s in arabic_feedback('مَدْرَسَة','مدرسة')),0)

if __name__=='__main__': unittest.main()
