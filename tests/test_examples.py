"""Optional examples stay outside assessment and required pronunciation."""
import io,json,re,sqlite3,uuid,zipfile
from contextlib import closing
import tests.test_app as fixtures
from app import create_app
from tools.backup_state import backup

class ExampleTests(fixtures.FamilyAppTests):
    def media_status(self,path):
        with self.c.get(path) as response:
            response.get_data()
            return response.status_code
    def add(self,wid=1,label='',eid=None,data=None):
        with self.c.session_transaction() as s:csrf=s['csrf']
        route=f'/admin/word/{wid}/examples'+('/'+eid if eid else '')
        return self.c.post(route,data={'label':label,'file':(io.BytesIO(data if data is not None else (self.root/'media/test.wav').read_bytes()),'example.wav')},headers={'X-CSRF-Token':csrf})
    def payload(self,path):
        r=self.c.get(path)
        self.assertEqual(r.status_code,200)
        return json.loads(re.search(rb'<script id="practice-data" type="application/json">(.*?)</script>',r.data).group(1))
    def test_multiple_optional_examples_edit_replace_remove_and_private_playback(self):
        self.login('parent')
        first=self.add(label='At breakfast');second=self.add(label='')
        self.assertEqual(first.status_code,200);self.assertEqual(second.status_code,200)
        eid=first.json['id'];old=first.json['url']
        rows=self.sql('SELECT * FROM word_examples WHERE word_id=1');self.assertEqual(len(rows),2)
        before=json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0])
        self.assertTrue(before['published']);self.assertEqual(before['audio'],'uploads/test.wav')
        self.post(f'/admin/word/1/examples/{eid}',{'label':'With friends'},form=True)
        previous=self.sql('SELECT audio FROM word_examples WHERE id=?',(eid,))[0][0]
        self.assertEqual(self.add(eid=eid,label='A new example').status_code,200)
        self.assertNotEqual(self.sql('SELECT audio FROM word_examples WHERE id=?',(eid,))[0][0],previous)
        self.login('child1');p=self.payload('/word/1');self.assertEqual(len(p['cards'][0]['examples']),2)
        self.assertEqual(self.media_status(old),200)
        self.assertEqual(self.c.get('/media/'+previous.removeprefix('uploads/')).status_code,403)
        self.login('parent');self.assertEqual(self.post(f'/admin/word/1/examples/{eid}',{'action':'delete'},form=True).status_code,302)
        self.login('child1');self.assertEqual(self.c.get(old).status_code,404);self.assertEqual(len(self.payload('/word/1')['cards'][0]['examples']),1)
        self.assertEqual(json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0]),before)
    def test_parent_only_csrf_invalid_audio_and_cross_word_ids(self):
        self.assertEqual(self.add().status_code,403);self.login('parent')
        self.assertEqual(self.c.post('/admin/word/1/examples',data={'file':(io.BytesIO(b'x'*200),'test.wav')}).status_code,400)
        self.assertEqual(self.add(data=b'not audio'*30).status_code,400)
        self.assertEqual(self.add(label='x'*161).status_code,400)
        eid=self.add().json['id']
        self.assertEqual(self.add(wid=2,eid=eid).status_code,404)
        self.assertEqual(self.post(f'/admin/word/2/examples/{eid}',{'action':'delete'},form=True).status_code,404)
        self.login('child1');self.assertEqual(self.post(f'/admin/word/1/examples/{eid}',{'action':'delete'},form=True).status_code,403)
        guest=self.app.test_client();self.assertEqual(guest.get('/example-media/'+eid).status_code,302)
        self.sql('UPDATE users SET enabled=0 WHERE username=?',('child1',));self.assertEqual(self.c.get('/example-media/'+eid).status_code,302)
    def test_drafts_future_levels_and_selected_exploration_access(self):
        self.login('parent');eid=self.add(wid=201).json['id']
        self.assertEqual(len(self.payload('/admin/word/201')['cards'][0]['examples']),1)
        self.login('child1');self.assertEqual(self.c.get('/example-media/'+eid).status_code,403)
        w=json.loads(self.sql('SELECT data FROM words WHERE id=201')[0][0]);w.update(published=True,arabic='اختبار',arabic_approved=True,image_approved=True,audio='uploads/test.wav',topic='Example access test')
        self.sql('UPDATE words SET data=? WHERE id=201',(json.dumps(w),))
        self.assertEqual(self.c.get('/example-media/'+eid).status_code,403)
        category=w['category'];p=self.payload('/explore?category='+category+'&topic=Example+access+test')
        self.assertEqual(p['cards'][0]['id'],201);self.assertEqual(p['cards'][0]['examples'][0]['id'],eid)
        self.assertEqual(self.media_status('/example-media/'+eid),200)
        self.login('child2');self.assertEqual(self.c.get('/example-media/'+eid).status_code,403)
        w['published']=False;self.sql('UPDATE words SET data=? WHERE id=201',(json.dumps(w),))
        self.login('child1');self.assertEqual(self.c.get('/example-media/'+eid).status_code,403)
    def test_examples_never_enter_quizzes_or_change_completion_or_listen_metrics(self):
        self.login('parent')
        for wid in range(1,21):self.add(wid=wid,label='NEVER_EXAM_EXAMPLE')
        self.login('child1');aid=self.complete();qid=self.start_quiz(aid)
        questions=json.loads(self.sql('SELECT questions FROM quizzes WHERE id=?',(qid,))[0][0])
        self.assertTrue(all(q['audio']=='uploads/test.wav' for q in questions))
        self.assertNotIn('NEVER_EXAM_EXAMPLE',json.dumps(questions))
        r=self.c.get(f'/api/quiz/{qid}');self.assertNotIn(b'example',r.data)
        self.assertNotIn(b'word-examples',self.c.get(f'/quiz/{qid}').data)
        p=self.payload('/word/1');self.assertEqual(self.media_status(p['cards'][0]['examples'][0]['audio']),200)
        self.assertEqual(len(self.sql('SELECT * FROM practice')),20)
        self.assertEqual(len(self.sql('SELECT * FROM answers')),0)
        self.assertEqual(len(self.sql("SELECT * FROM events WHERE kind IN ('audio_start','audio_end')")),0)
        self.assertEqual(self.post('/api/events',dict(id=str(uuid.uuid4()),word=1,source='my_words',kind='example_start')).status_code,400)
    def test_current_examples_update_issued_cards_without_rewriting_snapshots(self):
        self.c.get('/daily');snapshot=self.sql('SELECT data FROM assignment_cards ORDER BY position LIMIT 1')[0][0]
        self.login('parent');eid=self.add().json['id']
        self.login('child1');p=self.payload('/daily');self.assertEqual(p['cards'][0]['examples'][0]['id'],eid)
        self.assertEqual(self.sql('SELECT data FROM assignment_cards ORDER BY position LIMIT 1')[0][0],snapshot)
        self.login('parent');self.post(f'/admin/word/1/examples/{eid}',{'action':'delete'},form=True)
        self.login('child1');self.assertEqual(self.payload('/daily')['cards'][0]['examples'],[])
    def test_examples_backup_and_restart_preserve_existing_state(self):
        self.login('parent');eid=self.add(label='Persistent example').json['id']
        recording=self.sql('SELECT audio FROM word_examples WHERE id=?',(eid,))[0][0][8:]
        export=self.c.get('/admin/export')
        with zipfile.ZipFile(io.BytesIO(export.data)) as z:
            self.assertIn('media/'+recording,z.namelist())
            restored=self.root/'restored.sqlite3';restored.write_bytes(z.read('learning.sqlite3'))
            with closing(sqlite3.connect(restored)) as conn:self.assertEqual(conn.execute('SELECT label FROM word_examples WHERE id=?',(eid,)).fetchone()[0],'Persistent example')
        # Server backup uses the normal production filename.
        with closing(sqlite3.connect(self.root/'learning.sqlite3')) as dest:
            with self.app.app_context():self.app.helpers['db']().backup(dest)
        archive=backup(self.root,self.root/'backups')
        with zipfile.ZipFile(archive) as z:self.assertIn('media/'+recording,z.namelist())
        restarted=create_app(dict(self.app.config))
        with restarted.app_context():
            db=restarted.helpers['db']();self.assertEqual(db.execute('SELECT COUNT(*) FROM word_examples').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM words').fetchone()[0],2000)
        self.assertEqual(self.media_status('/example-media/'+eid),200)
    def test_simplified_editor_spelling_order_and_preserved_hidden_data(self):
        self.login('parent')
        before=json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0])
        before.update(forms=['existing form'],sentence='Existing sentence',sentence_audio='uploads/test.wav',content_note='Existing note')
        self.sql('UPDATE words SET data=? WHERE id=1',(json.dumps(before),))
        response=self.post('/admin/word/1',dict(spellings=' كتاب \n\n كِتاب \nكتاب\n',arabic_approved='on',image_approved='on',published='on'),form=True)
        self.assertEqual(response.status_code,302)
        saved=json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0])
        self.assertEqual(saved['arabic'],'كتاب')
        self.assertEqual(saved['variants'],['كِتاب'])
        self.assertTrue(saved['published'])
        for key in ('meaning','forms','sentence','sentence_audio','image_source','image_creator','image_license','content_note'):
            self.assertEqual(saved[key],before[key])
        page=self.c.get('/admin/word/1').data.decode()
        self.assertIn('كتاب\nكِتاب</textarea>',page)
        self.assertIn('Record example</button>',page)
        self.assertIn('Publish for children when all requirements are met',page)
        for field in ('meaning','arabic','variants','forms','sentence','image_source','image_creator','image_license','content_note'):
            self.assertNotIn('name="'+field+'"',page)
        self.assertNotIn('accept="audio/*"',page)
        self.assertNotIn('Earlier optional sentence recording',page)
        self.post('/admin/word/1',dict(spellings='كتاب',arabic_approved='on',image_approved='on',published='on'),form=True)
        saved=json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0])
        self.assertEqual(saved['variants'],[])
        self.assertTrue(saved['published'])
        self.post('/admin/word/1',dict(spellings='كتاب\ninvalid',arabic_approved='on'),form=True)
        self.assertEqual(json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0]),saved)

    def test_no_examples_required_to_publish_practice_or_quiz(self):
        self.assertEqual(self.sql('SELECT COUNT(*) FROM word_examples')[0][0],0)
        self.assertEqual(self.payload('/word/1')['cards'][0]['examples'],[])
        aid=self.complete();qid=self.start_quiz(aid)
        self.assertEqual(self.c.get(f'/api/quiz/{qid}').status_code,200)

for name in list(fixtures.FamilyAppTests.__dict__):
    if name.startswith('test_') and name not in ExampleTests.__dict__:setattr(ExampleTests,name,None)
