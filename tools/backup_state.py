"""Private consistent backup. Called by the installer/timer, not a web endpoint."""
import argparse,json,os,sqlite3,zipfile,tempfile
from datetime import datetime,timezone
from pathlib import Path
def backup(state,destination):
    state=Path(state).resolve();destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    archive=destination/('arabic-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.zip')
    snapshot=destination/('snapshot-'+str(os.getpid())+'.sqlite3')
    if not (state/'learning.sqlite3').exists():return None
    src=sqlite3.connect(state/'learning.sqlite3');target=sqlite3.connect(snapshot);src.backup(target);src.close();target.close()
    try:
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            z.write(snapshot,'learning.sqlite3')
            for name in ('session-secret','setup-token'):
                if (state/name).is_file():z.write(state/name,name)
            for p in (state/'media').glob('*'):
                if p.is_file():z.write(p,'media/'+p.name)
        archive.chmod(0o600)
    finally:snapshot.unlink(missing_ok=True)
    return archive
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',default=os.environ.get('ARABIC_STATE_DIR','instance'));p.add_argument('--destination',required=True);a=p.parse_args();result=backup(a.state,a.destination);print(result or 'No existing database to back up.')
