#!/usr/bin/env bash
# One file bootstraps or updates the full application on Ubuntu 24.04 LTS.
set -Eeuo pipefail
if ! command -v python3 >/dev/null 2>&1; then
    [[ "${EUID}" -eq 0 ]] || { echo 'Run with sudo to install Python 3.' >&2; exit 1; }
    apt-get update
    apt-get install -y python3
fi
export ARABIC_INSTALLER_SOURCE="$(realpath "$0")"
exec python3 - "$@" <<'PYTHON'
import argparse, fcntl, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

REPOSITORY='https://github.com/matoug24/arabic.git'
DOMAIN='arabic.matoug.com'
def validate_repository(url):
    if url==REPOSITORY:return url
    if re.fullmatch(r'git@github(?:-[A-Za-z0-9_-]+)?(?:\.com)?:matoug24/arabic\.git',url):return url
    raise ValueError('Use the named HTTPS repository or an SSH host alias for matoug24/arabic.git. Credentials in URLs are not accepted.')
def validate_domain(domain):
    if not re.fullmatch(r'(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',domain) or '..' in domain or '.' not in domain:raise ValueError('Invalid domain')
    return domain
def validate_branch(branch):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./-]*',branch) or '..' in branch:raise ValueError('Invalid branch')
    return branch

class Installer:
    def __init__(self,args,root=Path('/'),runner=None):
        self.args=args;self.root=Path(root);self.runner=runner or self.execute
        self.base=self.root/'opt/arabic';self.repo=self.base/'repository';self.releases=self.base/'releases';self.current=self.base/'current';self.state=self.root/'var/lib/arabic';self.backups=self.root/'var/backups/arabic';self.config=self.root/'etc/arabic';self.previous=None;self.backup=None;self.stopped=False
        saved=json.loads((self.config/'install.json').read_text()) if (self.config/'install.json').exists() else {}
        self.repository=validate_repository(args.repository or saved.get('repository',REPOSITORY));self.domain=validate_domain(args.domain or saved.get('domain',DOMAIN));self.branch=validate_branch(args.branch or saved.get('branch','main'));self.email=args.email or saved.get('email','')
    def execute(self,cmd,**kw):
        checked=kw.pop('check',True)
        result=subprocess.run([str(x) for x in cmd],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw)
        if result.returncode and checked:
            # No environment dump, shell trace or authentication URL output.
            if cmd[0]=='git':raise RuntimeError('Git operation failed. Check repository access, branch, clean checkout and fast-forward history. No remote history was overwritten.')
            raise RuntimeError(f'{Path(str(cmd[0])).name} failed: '+result.stderr[-2500:])
        return result.stdout.strip()
    def run(self,cmd,**kw):return self.runner([str(x) for x in cmd],**kw)
    def directories(self):
        for p in (self.base,self.releases,self.config,self.state,self.backups):p.mkdir(parents=True,exist_ok=True)
    def fetch(self):
        if not (self.repo/'.git').exists():
            if self.repo.exists() and any(self.repo.iterdir()):raise RuntimeError('Repository directory is not empty; refusing to overwrite it.')
            self.run(['git','clone','--branch',self.branch,self.repository,self.repo])
        else:
            remote=self.run(['git','-C',self.repo,'remote','get-url','origin'])
            if remote!=self.repository:raise RuntimeError('Existing origin differs. Inspect it; the installer will not replace it.')
            if self.run(['git','-C',self.repo,'status','--porcelain']):raise RuntimeError('Server checkout has local changes; resolve them before updating.')
            if self.run(['git','-C',self.repo,'branch','--show-current'])!=self.branch:raise RuntimeError('Existing checkout is on a different branch; inspect it before updating.')
            self.run(['git','-C',self.repo,'fetch','origin',self.branch])
            self.run(['git','-C',self.repo,'merge','--ff-only','origin/'+self.branch])
        revision=self.run(['git','-C',self.repo,'rev-parse',self.args.rollback or 'HEAD'])
        if not re.fullmatch('[0-9a-f]{40}',revision):raise RuntimeError('Invalid Git revision')
        return revision
    def release(self,revision):
        release=self.releases/revision
        if not (release/'.complete').exists():
            release.mkdir(parents=True,exist_ok=True)
            # git archive avoids .git, server state and machine-specific untracked files.
            archive=self.base/'release.tar'
            self.run(['git','-C',self.repo,'archive','--format=tar','--output',archive,revision])
            self.run(['tar','-xf',archive,'-C',release]);archive.unlink(missing_ok=True)
            self.run(['python3','-m','venv',release/'.venv'])
            self.run([release/'.venv/bin/python','-m','pip','install','--disable-pip-version-check','-r',release/'requirements.txt'])
            self.run([release/'.venv/bin/python','-m','compileall','-q',release/'app.py',release/'migrations.py',release/'wsgi.py'])
            self.run([release/'.venv/bin/python',release/'tools/validate_catalog.py'])
            (release/'.complete').write_text(revision+'\n')
        return release
    def configure(self,release):
        env=self.config/'app.env'
        if not env.exists():env.write_text(f'ARABIC_STATE_DIR=/var/lib/arabic\nARABIC_PRODUCTION=1\nARABIC_DOMAIN={self.domain}\n')
        else:
            lines=env.read_text().splitlines();lines=[line for line in lines if not line.startswith(('ARABIC_DOMAIN=','ARABIC_STATE_DIR=','ARABIC_PRODUCTION='))];env.write_text('\n'.join(lines)+f'\nARABIC_DOMAIN={self.domain}\nARABIC_STATE_DIR=/var/lib/arabic\nARABIC_PRODUCTION=1\n')
        env.chmod(0o640)
        (self.config/'install.json').write_text(json.dumps(dict(repository=self.repository,domain=self.domain,branch=self.branch,email=self.email),indent=2)+'\n')
        (self.config/'install.json').chmod(0o600)
        for name in ('arabic.service','arabic-backup.service','arabic-backup.timer'):shutil.copyfile(release/'deploy'/name,self.root/'etc/systemd/system'/name)
        self.run(['chown','root:arabic',self.config,env]);self.run(['chmod','750',self.config])
        self.run(['chown','-R','arabic:arabic',self.state]);self.run(['chmod','750',self.state]);self.run(['chmod','700',self.backups])
        self.run(['systemctl','daemon-reload'])
    def nginx_text(self,tls):
        acme='location /.well-known/acme-challenge/ { root /var/www/arabic-acme; }'
        proxy='''client_max_body_size 12m;
    server_tokens off;
    location / { proxy_pass http://127.0.0.1:8050; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-For $remote_addr; proxy_set_header X-Forwarded-Proto $scheme; proxy_read_timeout 120s; }
'''
        if tls:
            return f'''server {{ listen 80; listen [::]:80; server_name {self.domain}; {acme} location / {{ return 301 https://$host$request_uri; }} }}
server {{ listen 443 ssl; listen [::]:443 ssl; server_name {self.domain}; ssl_certificate /etc/letsencrypt/live/{self.domain}/fullchain.pem; ssl_certificate_key /etc/letsencrypt/live/{self.domain}/privkey.pem; ssl_protocols TLSv1.2 TLSv1.3; {proxy} }}
'''
        # No logins, setup or family data are ever served on unencrypted public HTTP.
        return f'''server {{ listen 80; listen [::]:80; server_name {self.domain}; {acme} location / {{ default_type text/plain; return 503 "HTTPS setup is required. Complete certificate setup on the server.\\n"; }} }}
'''
    def nginx(self):
        available=self.root/'etc/nginx/sites-available/arabic';enabled=self.root/'etc/nginx/sites-enabled/arabic'
        cert=self.root/f'etc/letsencrypt/live/{self.domain}/fullchain.pem';key=self.root/f'etc/letsencrypt/live/{self.domain}/privkey.pem'
        tls=cert.exists() and key.exists();previous=available.read_text() if available.exists() else None
        available.write_text(self.nginx_text(tls))
        if not enabled.exists():enabled.symlink_to(available)
        try:self.run(['nginx','-t'])
        except Exception:
            if previous is not None:available.write_text(previous)
            else:available.unlink(missing_ok=True);enabled.unlink(missing_ok=True)
            raise
        self.run(['systemctl','reload','nginx']);return tls
    def health(self):
        for _ in range(20):
            try:self.run(['curl','--fail','--silent','--max-time','5','http://127.0.0.1:8050/healthz']);return
            except RuntimeError:time.sleep(1)
        raise RuntimeError('Application health check failed')
    def activate(self,release):
        self.previous=self.previous_release()
        self.run(['systemctl','stop','arabic'],check=False);self.stopped=True
        if (self.state/'learning.sqlite3').exists():
            output=self.run([release/'.venv/bin/python',release/'tools/backup_state.py','--state',self.state,'--destination',self.backups]);self.backup=output
        # Startup applies only additive schema migrations and imports into missing image fields.
        env=dict(os.environ,ARABIC_STATE_DIR=str(self.state),ARABIC_PRODUCTION='1',ARABIC_DOMAIN=self.domain)
        self.run([release/'.venv/bin/python','-c','from app import create_app; create_app()'],cwd=str(release),env=env)
        self.run([release/'.venv/bin/python',release/'tools/server_setup.py','--state',self.state],check=False)
        self.run(['chown','-R','arabic:arabic',self.state])
        self.promote(release)
        self.run(['systemctl','enable','arabic','arabic-backup.timer']);self.run(['systemctl','restart','arabic']);self.health();self.stopped=False
        self.run(['systemctl','restart','arabic-backup.timer'])
    def previous_release(self):
        if self.current.exists() and not self.current.is_symlink():raise RuntimeError('Current path is not a managed symlink; refusing to overwrite it.')
        return self.current.resolve() if self.current.is_symlink() else None
    def promote(self,release):
        temp=self.base/'next-current';temp.unlink(missing_ok=True);temp.symlink_to(release);os.replace(temp,self.current)
    def install(self):
        self.directories();self.run(['apt-get','update']);self.run(['apt-get','install','-y','python3','python3-venv','python3-pip','git','nginx','curl','ca-certificates','certbot','python3-certbot-nginx'])
        if not self.run(['getent','group','arabic'],check=False):self.run(['groupadd','--system','arabic'])
        if not self.run(['id','-u','arabic'],check=False):self.run(['useradd','--system','--gid','arabic','--home','/var/lib/arabic','--shell','/usr/sbin/nologin','arabic'])
        revision=self.fetch()
        # Python has already parsed this file; a pull cannot alter executing instructions.
        # If the installer itself changed, run that version once in the same invocation.
        origin=os.environ.get('ARABIC_INSTALLER_SOURCE');latest=self.repo/'deploy/install_arabic.sh'
        if origin and os.environ.get('ARABIC_INSTALL_REEXECED')!='1' and latest.exists() and Path(origin).read_bytes()!=latest.read_bytes():
            env=dict(os.environ,ARABIC_INSTALL_REEXECED='1');os.execvpe('/bin/bash',['/bin/bash',str(latest),*sys.argv[1:]],env)
        release=self.release(revision);self.configure(release);self.activate(release)
        (self.root/'var/www/arabic-acme').mkdir(parents=True,exist_ok=True)
        self.run(['systemctl','enable','--now','nginx']);tls=self.nginx()
        if self.args.https:
            if not self.email or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',self.email):raise RuntimeError('A valid --email is required for HTTPS certificate notices.')
            self.run(['certbot','certonly','--webroot','--webroot-path','/var/www/arabic-acme','--non-interactive','--agree-tos','--email',self.email,'-d',self.domain,'--keep-until-expiring'])
            tls=self.nginx();self.run(['systemctl','enable','--now','certbot.timer'])
            hook=self.root/'etc/letsencrypt/renewal-hooks/deploy/reload-arabic-nginx';hook.parent.mkdir(parents=True,exist_ok=True);hook.write_text('#!/bin/sh\nnginx -t && systemctl reload nginx\n');hook.chmod(0o755)
        wrapper=self.root/'usr/local/sbin/install-arabic';wrapper.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(release/'deploy/install_arabic.sh',wrapper);wrapper.chmod(0o755)
        print('Application health: OK. Revision:',revision)
        print('HTTPS configured.' if tls else 'HTTPS is pending. Public HTTP serves only a setup notice; run with --https --email after DNS/firewall are ready.')
        print('Update next time: sudo install-arabic')
        print('Parent setup token is stored privately at /var/lib/arabic/setup-token if no parent exists. It is never printed by the installer.')
        if self.backup:print('Pre-update private backup:',self.backup)
    def restore_service(self):
        # Never silently restore the database: post-update learning must not be overwritten.
        # Additive migrations remain compatible with the previous release in this update series.
        if self.previous:
            self.promote(self.previous)
            try:self.run(['systemctl','restart','arabic'])
            except Exception:pass
        elif self.stopped:
            try:self.run(['systemctl','stop','arabic'])
            except Exception:pass
        print('Update failed. Previous code restored where available. Database/uploads were not overwritten. See the private pre-update backup and deployment guide.',file=sys.stderr)

def arguments(argv=None):
    p=argparse.ArgumentParser(description='Install/update Arabic learning on Ubuntu 24.04. No AWS or DNS changes.')
    p.add_argument('--repository');p.add_argument('--domain');p.add_argument('--branch');p.add_argument('--email');p.add_argument('--https',action='store_true',help='Request certificate after DNS and public port 80 are ready; accepts Let\'s Encrypt subscriber terms.');p.add_argument('--rollback',help='Known Git commit to activate; state is preserved, not downgraded.');p.add_argument('--dry-run',action='store_true');return p.parse_args(argv)
def main():
    args=arguments();installer=Installer(args)
    if args.dry_run:
        print('Repository:',installer.repository,'Branch:',installer.branch,'Domain:',installer.domain)
        print('Plan: apt dependencies -> clean fast-forward Git checkout -> immutable release/venv -> validation -> stop service -> private backup -> additive migrations -> atomic symlink -> systemd/health -> Nginx -> optional HTTPS.')
        print('Persistent state: /var/lib/arabic. Secrets/settings: /etc/arabic. Backups: /var/backups/arabic. No changes made.');return
    if os.geteuid()!=0:raise SystemExit('Run this installer with sudo.')
    release=Path('/etc/os-release').read_text()
    if 'ID=ubuntu' not in release or 'VERSION_ID="24.04"' not in release:raise SystemExit('This installer is tested for Ubuntu 24.04 LTS only.')
    Path('/run/lock').mkdir(parents=True,exist_ok=True)
    with open('/run/lock/arabic-install.lock','w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Another Arabic installation/update is running.')
        try:installer.install()
        except Exception as exc:installer.restore_service();raise SystemExit(str(exc))
if __name__=='__main__':main()
PYTHON
