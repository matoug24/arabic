"""Disposable local UI test environment. Never touches family instance data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.test_app import FamilyAppTests
fixture=FamilyAppTests(); fixture.setUp()
print('UI TEST FIXTURES ONLY: mock Arabic and silent audio, not validated content or parent recordings.',flush=True)
try: fixture.app.run(host='127.0.0.1',port=5001,debug=False,use_reloader=False)
finally: fixture.tearDown()
