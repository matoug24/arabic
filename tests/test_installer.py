"""Installer orchestration on isolated paths. No package/service/cloud mutations."""
import argparse,importlib.util,json,os,shutil,sqlite3,sys,types,unittest,uuid
from pathlib import Path
from tools.backup_state import backup
ROOT=Path(__file__).resolve().parents[1]
if os.name=='nt':sys.modules.setdefault('fcntl',types.SimpleNamespace(LOCK_EX=1,LOCK_NB=2,flock=lambda *args:None))
installer=types.ModuleType('installer_under_test');source=(ROOT/'deploy/install_arabic.sh').read_text(encoding='utf-8');code=source.split("<<'PYTHON'",1)[1].rsplit('PYTHON',1)[0];exec(compile(code,'install_arabic.sh','exec'),installer.__dict__)
class PortableInstaller(installer.Installer):
    """Model atomic symlink promotion with a marker on Windows; real Linux uses os.replace."""
    def previous_release(self):return Path(self.current.read_text()) if self.current.exists() else None
    def promote(self,release):self.current.write_text(str(release))
    def nginx(self):
        available=self.root/'etc/nginx/sites-available/arabic';old=available.read_text() if available.exists() else None;cert=self.root/f'etc/letsencrypt/live/{self.domain}/fullchain.pem';key=self.root/f'etc/letsencrypt/live/{self.domain}/privkey.pem';tls=cert.exists() and key.exists();available.write_text(self.nginx_text(tls))
        try:self.run(['nginx','-t'])
        except Exception:
            if old is not None:available.write_text(old)
            raise
        self.run(['systemctl','reload','nginx']);return tls
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.root=ROOT/'test-output'/('installer-'+uuid.uuid4().hex);self.root.mkdir(parents=True);self.commands=[];self.rev='a'*40;self.dirty=False;self.origin=installer.REPOSITORY;self.health_fail=False
        for p in ['etc/systemd/system','etc/nginx/sites-available','etc/nginx/sites-enabled','var/lib/arabic/media']:(self.root/p).mkdir(parents=True,exist_ok=True)
        self.state=self.root/'var/lib/arabic';db=sqlite3.connect(self.state/'learning.sqlite3');db.execute('CREATE TABLE progress(value TEXT)');db.execute("INSERT INTO progress VALUES('keep child progress')");db.commit();db.close();(self.state/'media/parent.wav').write_bytes(b'private voice');(self.state/'session-secret').write_text('test private secret')
        self.args=installer.arguments([]);self.i=PortableInstaller(self.args,self.root,self.fake);installer.time=types.SimpleNamespace(sleep=lambda _:None)
    def tearDown(self):
        assert self.root.resolve().is_relative_to((ROOT/'test-output').resolve()) and self.root.name.startswith('installer-');shutil.rmtree(self.root)
    def fake(self,cmd,**kw):
        self.commands.append(cmd)
        if cmd[:2]==['git','clone']:(Path(cmd[-1])/'.git').mkdir(parents=True);return ''
        if cmd[0]=='git':
            if 'get-url' in cmd:return self.origin
            if 'status' in cmd:return 'dirty' if self.dirty else ''
            if 'branch' in cmd:return 'main'
            if 'rev-parse' in cmd:return self.rev
            if 'archive' in cmd:Path(cmd[cmd.index('--output')+1]).write_text('fixture archive')
            return ''
        if cmd[0]=='tar':
            dest=Path(cmd[-1]);(dest/'deploy').mkdir(exist_ok=True);(dest/'tools').mkdir(exist_ok=True)
            for name in ['arabic.service','arabic-backup.service','arabic-backup.timer','install_arabic.sh']:shutil.copyfile(ROOT/'deploy'/name,dest/'deploy'/name)
        if 'backup_state.py' in ' '.join(cmd):return str(backup(cmd[cmd.index('--state')+1],cmd[cmd.index('--destination')+1]))
        if cmd[0]=='curl' and self.health_fail:raise RuntimeError('fixture failed health')
        return ''
    def assert_private_state(self):
        db=sqlite3.connect(self.state/'learning.sqlite3');self.assertEqual(db.execute('SELECT value FROM progress').fetchone()[0],'keep child progress');db.close();self.assertEqual((self.state/'media/parent.wav').read_bytes(),b'private voice');self.assertEqual((self.state/'session-secret').read_text(),'test private secret')
    def test_first_install_repeat_and_safe_new_release(self):
        self.i.install();self.assert_private_state();release=self.i.current.read_text();first_pip=sum('pip' in c for c in self.commands)
        self.i.install();self.assert_private_state();self.assertEqual(self.i.current.read_text(),release);self.assertEqual(sum('pip' in c for c in self.commands),first_pip);self.assertTrue(any('--ff-only' in c for c in self.commands))
        self.rev='b'*40;self.i.install();self.assert_private_state();self.assertNotEqual(self.i.current.read_text(),release);self.assertTrue(list(self.i.backups.glob('*.zip')))
    def test_dirty_checkout_and_wrong_origin_are_not_overwritten(self):
        self.i.install();self.dirty=True
        with self.assertRaisesRegex(RuntimeError,'local changes'):self.i.fetch()
        self.dirty=False;self.origin='https://github.com/someone/other.git'
        with self.assertRaisesRegex(RuntimeError,'origin differs'):self.i.fetch()
        self.assert_private_state();self.assertFalse(any('reset' in c or '--force' in c for c in self.commands))
    def test_failed_health_restores_previous_code_without_destroying_state(self):
        self.i.install();old=self.i.current.read_text();self.rev='c'*40;self.health_fail=True
        try:self.i.install()
        except RuntimeError:self.i.restore_service()
        self.assertEqual(self.i.current.read_text(),old);self.assert_private_state()
    def test_http_never_exposes_login_and_tls_survives_updates(self):
        self.assertIn('return 503',self.i.nginx_text(False));self.assertNotIn('proxy_pass',self.i.nginx_text(False));self.assertIn('127.0.0.1:8050',self.i.nginx_text(True));self.assertIn('return 301 https',self.i.nginx_text(True))
        cert=self.root/f'etc/letsencrypt/live/{self.i.domain}';cert.mkdir(parents=True);(cert/'fullchain.pem').write_text('test certificate');(cert/'privkey.pem').write_text('test key');self.i.install();self.i.install();self.assertIn('listen 443 ssl',(self.root/'etc/nginx/sites-available/arabic').read_text())
    def test_validation_rejects_token_urls_and_shell_injection(self):
        for url in ['https://token:secret@github.com/matoug24/arabic.git','https://example.org/app.git','x; rm -rf /']:
            with self.assertRaises(ValueError):installer.validate_repository(url)
        with self.assertRaises(ValueError):installer.validate_domain('x; echo bad')
        with self.assertRaises(ValueError):installer.validate_branch('--force')
    def test_backup_contains_consistent_database_voice_and_secret(self):
        import zipfile
        p=backup(self.state,self.root/'backups')
        with zipfile.ZipFile(p) as z:self.assertIn('learning.sqlite3',z.namelist());self.assertEqual(z.read('media/parent.wav'),b'private voice');self.assertEqual(z.read('session-secret'),b'test private secret')
    def test_environment_preserved_and_setup_token_not_logged(self):
        self.i.install();env=self.i.config/'app.env';env.write_text(env.read_text()+'CUSTOM_PARENT_SETTING=keep\n');self.i.install();self.assertIn('CUSTOM_PARENT_SETTING=keep',env.read_text());self.assertFalse(any('test private secret' in ' '.join(c) for c in self.commands))
