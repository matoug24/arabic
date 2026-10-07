import io,json,re,sqlite3,unittest,uuid
from pathlib import Path
import tests.test_app as fixtures
from app import create_app
from curriculum import CATEGORIES
from migrations import rebuild_plan

class NewLearningTests(fixtures.FamilyAppTests):
    # Reuse fixtures but do not duplicate inherited regression tests in discovery.
    def move(self,wid,level,position):
        w=json.loads(self.sql('SELECT data FROM words WHERE id=?',(wid,))[0][0]);data={k:w[k] for k in ['english','meaning','arabic','category','topic','pos']};data.update(level=level,position=position,published='on',image_approved='on',arabic_approved='on',variants='\n'.join(w['variants']));return self.post('/admin/word/'+str(wid),data,form=True)
    def test_twenty_categories_and_full_image_coverage(self):
        self.assertEqual(len(CATEGORIES),20);d=json.loads((Path(__file__).resolve().parents[1]/'data/curriculum.json').read_text(encoding='utf-8'));self.assertEqual(set(w['category'] for w in d),set(CATEGORIES));self.assertEqual(len(d),2000)
        for w in d:self.assertTrue(w['image']);self.assertTrue(w['image_creator']);self.assertTrue(w['image_license'])
    def test_random_cross_level_batches_and_no_duplicate_practice_counts(self):
        ids=list(range(1,6))+list(range(201,206))+list(range(1601,1606))
        for wid in ids:
            w=json.loads(self.sql('SELECT data FROM words WHERE id=?',(wid,))[0][0]);w.update(category='Animals and living things',topic='Across levels test',arabic='كلمة'+self.arabic_number(wid),arabic_approved=True,image_approved=True,audio='uploads/test.wav',published=True);self.sql('UPDATE words SET data=? WHERE id=?',(json.dumps(w),wid))
        self.c.get('/explore?category=Animals+and+living+things&topic=Across+levels+test');b=self.sql('SELECT * FROM exploration_batches ORDER BY created DESC LIMIT 1')[0];selected=json.loads(b['words']);self.assertEqual(len(set(selected)),10);self.assertTrue(any(w>200 for w in selected));self.assertEqual(len(self.sql('SELECT * FROM assignments')),0)
        wid=selected[0];self.assertEqual(self.post('/api/exploration-practice',dict(batch=b['id'],word=wid)).status_code,200);self.post('/api/exploration-practice',dict(batch=b['id'],word=wid));self.assertEqual(len(self.sql('SELECT * FROM topic_practice')),1)
        self.post('/api/events',dict(id=str(uuid.uuid4()),source='explore',kind='visit',word=wid));self.assertEqual(len(self.sql('SELECT * FROM exploration')),1)
        self.c.get('/explore?category=Animals+and+living+things&topic=Across+levels+test');new=json.loads(self.sql('SELECT words FROM exploration_batches ORDER BY created DESC LIMIT 1')[0][0]);self.assertEqual(len(set(new)-set(selected)),5)
        self.login('child2');self.assertEqual(self.post('/api/exploration-practice',dict(batch=b['id'],word=wid)).status_code,403)
    def test_small_groups_only_ready_children_and_drafts_parent(self):
        for wid in (2,201):
            w=json.loads(self.sql('SELECT data FROM words WHERE id=?',(wid,))[0][0]);w.update(category='Body and senses',topic='Small test');self.sql('UPDATE words SET data=? WHERE id=?',(json.dumps(w),wid))
        self.c.get('/explore?category=Body+and+senses&topic=Small+test');b=json.loads(self.sql('SELECT words FROM exploration_batches ORDER BY created DESC LIMIT 1')[0][0]);self.assertEqual(b,[2])
        self.login('parent');self.c.get('/admin/preview/explore?category=Body+and+senses&topic=Small+test');b=json.loads(self.sql('SELECT words FROM exploration_batches ORDER BY created DESC LIMIT 1')[0][0]);self.assertEqual(set(b),{2,201});self.assertEqual(len(self.sql('SELECT * FROM topic_practice')),0)
    def test_unissued_move_changes_future_homework_and_counts_stay_exact(self):
        aid=self.complete();self.sql('UPDATE assignments SET completed=? WHERE id=?',('2020-01-01',aid));old=[r[0] for r in self.sql('SELECT word_id FROM assignment_cards WHERE assignment_id=? ORDER BY position',(aid,))]
        self.login('parent');self.move(25,2,1);self.assertEqual([r[0] for r in self.sql('SELECT word_id FROM assignment_cards WHERE assignment_id=? ORDER BY position',(aid,))],old)
        plan=self.sql('SELECT * FROM child_plan WHERE user_id=2');self.assertEqual(len(plan),2000);self.assertEqual(len(set(r['word_id'] for r in plan)),2000);self.assertEqual([r['word_id'] for r in plan if r['slot']==25],[201])
        self.assertEqual([r['n'] for r in self.sql('SELECT COUNT(*) n FROM words GROUP BY level')],[200]*10)
        # Incoming draft needs approval before the next homework opens.
        self.login('child1');self.c.get('/daily');self.assertEqual(len(self.sql('SELECT * FROM assignments')),1)
    def test_issued_word_move_keeps_practice_quiz_and_other_child_plan(self):
        aid=self.complete();qid=self.start_quiz(aid);questions=self.sql('SELECT questions FROM quizzes WHERE id=?',(qid,))[0][0]
        self.login('parent');self.move(1,2,1);self.assertEqual(self.sql('SELECT questions FROM quizzes WHERE id=?',(qid,))[0][0],questions);self.assertEqual(len(self.sql('SELECT * FROM practice')),20)
        self.assertEqual(self.sql('SELECT word_id FROM child_plan WHERE user_id=2 AND slot=1')[0][0],1);self.assertEqual(self.sql('SELECT word_id FROM child_plan WHERE user_id=3 AND slot=1')[0][0],201)
        self.assertEqual(len(self.sql('SELECT * FROM placement_history')),1);self.login('child1');self.assertEqual(self.c.get('/word/1').status_code,200)
    def test_migration_idempotent_preserves_recordings_and_parent_changes(self):
        aid=self.complete();self.sql("UPDATE words SET english='My custom English' WHERE id=1");w=json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0]);w.update(english='My custom English',content_note='Personal review',audio='uploads/test.wav');self.sql('UPDATE words SET data=? WHERE id=1',(json.dumps(w),))
        for _ in range(2):
            app=create_app(dict(self.app.config));self.assertIsNotNone(app)
        self.assertEqual(json.loads(self.sql('SELECT data FROM words WHERE id=1')[0][0])['content_note'],'Personal review');self.assertEqual(len(self.sql('SELECT * FROM practice')),20);self.assertEqual(len(self.sql('SELECT * FROM assignment_cards WHERE assignment_id=?',(aid,))),20)
    def test_production_setup_https_token_and_no_default_credentials(self):
        db=self.root/'production.sqlite3';token=self.root/'bootstrap';token.write_text('test-bootstrap-token')
        a=create_app({'TESTING':True,'DATABASE':str(db),'UPLOAD_DIR':str(self.root/'prodmedia'),'SECRET_KEY':'test-secret','PRODUCTION':True,'SETUP_TOKEN_FILE':str(token),'SESSION_COOKIE_SECURE':True});c=a.test_client();self.assertEqual(c.get('/setup').status_code,403)
        response=c.get('/setup',base_url='https://arabic.matoug.com');self.assertEqual(response.status_code,200)
        csrf=re.search(rb'name="csrf-token" content="([^"]+)"',response.data).group(1).decode()
        r=c.post('/setup',base_url='https://arabic.matoug.com',data=dict(csrf=csrf,username='owner',password='owner-test-password',setup_token='wrong'));self.assertEqual(r.status_code,403)
        r=c.post('/setup',base_url='https://arabic.matoug.com',data=dict(csrf=csrf,username='owner',password='owner-test-password',setup_token='test-bootstrap-token'));self.assertEqual(r.status_code,302);self.assertFalse(token.exists());self.assertIn('Secure',r.headers['Set-Cookie'])
    def test_health_has_no_private_data(self):
        r=self.c.get('/healthz');self.assertEqual(r.json,dict(status='ok'))

# Only additional tests run in this class; base regression suite is discovered separately.
for name in list(fixtures.FamilyAppTests.__dict__):
    if name.startswith('test_') and name not in NewLearningTests.__dict__:setattr(NewLearningTests,name,None)
