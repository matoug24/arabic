"""Disposable local UI test environment. Never touches family instance data."""
import sys,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.test_app import FamilyAppTests
fixture=FamilyAppTests(); fixture.setUp()
if '--examples' in sys.argv:
    fixture.login('parent')
    with fixture.c.session_transaction() as session:csrf=session['csrf']
    for label in ('At breakfast (test audio)','With friends (test audio)'):
        response=fixture.c.post('/admin/word/1/examples',data={'label':label,'file':(io.BytesIO((fixture.root/'media/test.wav').read_bytes()),'test.wav')},headers={'X-CSRF-Token':csrf})
        assert response.status_code==200
print('UI TEST FIXTURES ONLY: mock Arabic and silent audio, not validated content or parent recordings.',flush=True)
try: fixture.app.run(host='127.0.0.1',port=5001,debug=False,use_reloader=False)
finally: fixture.tearDown()
