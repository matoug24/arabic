"""Create a one-time bootstrap token without default parent credentials."""
import argparse,os,secrets,sqlite3
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--state',default=os.environ.get('ARABIC_STATE_DIR','instance'));p.add_argument('--show-token',action='store_true');a=p.parse_args();state=Path(a.state);state.mkdir(parents=True,exist_ok=True)
if (state/'learning.sqlite3').exists():
    db=sqlite3.connect(state/'learning.sqlite3');count=db.execute('SELECT COUNT(*) FROM users').fetchone()[0];db.close()
    if count:raise SystemExit('A parent account already exists; setup stays disabled.')
path=state/'setup-token'
if not path.exists():
    with path.open('x') as f:f.write(secrets.token_urlsafe(32))
    path.chmod(0o600)
print(path.read_text().strip() if a.show_token else 'One-time setup token prepared in private state storage.')
