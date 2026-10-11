# Arabic learning: numbered Lightsail installation and update guide

Target: **Ubuntu 24.04 LTS, OS-only**, repository **https://github.com/matoug24/arabic.git**, domain **arabic.matoug.com**. This guide prepares installation; no AWS instance, public IP, DNS record or live HTTPS site has been created by this work.

The installer is one file: `deploy/install_arabic.sh`. The same file installs a new server or updates an existing installation. After installation, the convenient command is `sudo install-arabic`. It fetches the repository, makes a production release, installs dependencies, backs up state, migrates safely, restarts and checks health. AWS account operations, DNS ownership, GitHub authorization and speaking personal recordings remain human steps.

## 1. Understand the architecture

```text
Browser -> HTTPS 443 -> Nginx -> Gunicorn 127.0.0.1:8050 -> Flask
                                                       -> /var/lib/arabic
```

One Gunicorn worker with four threads serves this single-instance SQLite app. Only Nginx is public. Never open port 8050 in Lightsail or Ubuntu's firewall. Application state lives outside Git checkouts and release directories. No image-generation service, audio-generation service, messaging service or paid third-party API is needed.

| Item | Location | GitHub contents? |
| --- | --- | --- |
| Clean Git checkout/cache | `/opt/arabic/repository` | App source only |
| Immutable release and Python environment | `/opt/arabic/releases/<COMMIT>` | Source comes from Git; environment is local |
| Active release symlink | `/opt/arabic/current` | No |
| Database and parent uploads | `/var/lib/arabic/learning.sqlite3`, `/var/lib/arabic/media` | **No** |
| Session secret and initial setup token | `/var/lib/arabic/session-secret`, `/var/lib/arabic/setup-token` | **No** |
| App settings and saved installer options | `/etc/arabic/app.env`, `/etc/arabic/install.json` | **No** |
| Private backups | `/var/backups/arabic` | **No** |
| Service and scheduled backup | `/etc/systemd/system/arabic*` | Templates only |
| Nginx config | `/etc/nginx/sites-available/arabic` | Installer-generated |
| HTTPS keys and certificates | `/etc/letsencrypt` | **No** |

## 2. Confirm the source repository is populated

Open [the repository](https://github.com/matoug24/arabic) and confirm `app.py`, `requirements.txt`, `deploy/install_arabic.sh`, `data/curriculum.json` and `static/images/` exist on `main`. An empty repository cannot install an application. The delivery message states whether publication succeeded; use that actual status instead of assuming a push occurred.

The source contains the curated English curriculum and licensed pictures. It excludes accounts, recordings, database files, local secrets, test output and private keys. ARASAAC pictures require attribution, noncommercial use and share-alike; see the app's Credits page and README. Do not turn this deployment into a commercial service without replacing/relicensing restricted assets.

## 3. Create the Lightsail instance yourself

In the [Lightsail console](https://lightsail.aws.amazon.com/), choose **Create instance → Linux/Unix → OS Only → Ubuntu 24.04 LTS**. Use an OS-only image rather than a Bitnami application image with another web stack. Choose the region and instance size according to your own budget; leave room for Python, Nginx, Git updates and future recordings. Keep the SSH key pair you choose. Creating the instance incurs AWS charges and is not performed by the installer.

## 4. Attach a static public IPv4 address

Create a Lightsail static IP in the instance's region and attach it. Record its real value as **`YOUR_STATIC_IP`** for the commands below. Do not use a sample IP as a real destination. An ordinary public IPv4 address can change after stopping/restarting an instance; the static IP keeps DNS stable. [AWS static-IP instructions](https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-create-static-ip.html).

## 5. Configure the Lightsail firewall

In the instance's **Networking** tab allow:

| Port | Purpose | Source |
| --- | --- | --- |
| TCP 22 | SSH administration | Your public IP where practical |
| TCP 80 | ACME certificate validation and HTTPS redirect | All IPv4 addresses |
| TCP 443 | HTTPS website | All IPv4 addresses |

Do not allow 5000, 5001, 8050 or database ports publicly. IPv4 and IPv6 firewall settings are separate. If you publish an AAAA record, ensure IPv6 reaches this same instance and equivalent HTTP/HTTPS rules exist; otherwise omit the AAAA record. [AWS firewall instructions](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html).

## 6. Set the DNS A record

At the DNS provider currently authoritative for `matoug.com`, create or update:

```text
Type: A
Name: arabic
Value: YOUR_STATIC_IP
```

Do not move the whole `matoug.com` DNS zone or replace its nameservers just to add this subdomain; preserve existing websites and mail records. If you deliberately choose a Lightsail DNS zone, follow [AWS DNS-zone guidance](https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-create-dns-entry.html) and migrate all existing records before changing delegation. The installer cannot edit your DNS without account credentials, and it never attempts to do so.

## 7. Connect over SSH

Use Lightsail's browser SSH terminal, or from Windows PowerShell:

```powershell
ssh -i "C:\path\to\YOUR_LIGHTSAIL_KEY.pem" ubuntu@YOUR_STATIC_IP
```

Replace the key path and IP with your own. Verify the server identity through your Lightsail instance details before accepting its SSH host key. Once connected, verify the OS:

```bash
cat /etc/os-release
```

The installer requires `ID=ubuntu` and `VERSION_ID="24.04"`. It intentionally refuses an untested OS. Run Linux commands below **on the server**, not in Windows PowerShell.

## 8. Check repository access and install bootstrap tools

```bash
sudo apt-get update
sudo apt-get install -y curl ca-certificates git python3
git ls-remote https://github.com/matoug24/arabic.git refs/heads/main
```

If a commit hash appears, the public HTTPS path is accessible. If access fails or Git asks for credentials, do not put a password/token into a URL. For a private repository, complete step 9; otherwise go to step 10.

## 9. Private repository: authorize a read-only deploy key

This step is needed only if the repository is private. Generate a key **on this server**, not by copying another project's credentials:

```bash
sudo install -d -m 700 /root/.ssh
sudo ssh-keygen -t ed25519 -f /root/.ssh/arabic_deploy -N '' -C 'arabic-lightsail-read-only'
sudo cat /root/.ssh/arabic_deploy.pub
```

Copy only the **public** key to GitHub → `matoug24/arabic` → Settings → Deploy keys → Add deploy key. Leave write access disabled. Never share the private `/root/.ssh/arabic_deploy` file.

Create `/root/.ssh/config` using `sudoedit /root/.ssh/config` and add:

```sshconfig
Host github-arabic
    HostName github.com
    User git
    IdentityFile /root/.ssh/arabic_deploy
    IdentitiesOnly yes
```

```bash
sudo chmod 600 /root/.ssh/config
sudo ssh -T git@github-arabic
```

Compare GitHub's presented host key with [GitHub's official SSH fingerprints](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints) before accepting it. GitHub's successful authentication greeting may return exit code 1 because interactive shells are not offered; that is normal. Verify repository access explicitly:

```bash
sudo git ls-remote git@github-arabic:matoug24/arabic.git refs/heads/main
```

The installer saves this SSH repository choice for future updates. It does not copy keys into app releases or expose them to the `arabic` service account.

## 10. Obtain the single installer file

For a public repository:

```bash
curl --fail --location --output install_arabic.sh \
  https://raw.githubusercontent.com/matoug24/arabic/main/deploy/install_arabic.sh
chmod 700 install_arabic.sh
less install_arabic.sh
bash install_arabic.sh --dry-run
```

Download first, inspect it, then execute; do not pipe an unchecked download directly into a root shell. The dry run describes the installation paths and makes no changes.

For a private repository, the public raw URL may return 404. Obtain the file through your read-only SSH key:

GitHub does not support remote `git archive`; use a temporary authenticated clone instead:

```bash
sudo git clone --depth 1 --branch main \
  git@github-arabic:matoug24/arabic.git /root/arabic-bootstrap
sudo cp /root/arabic-bootstrap/deploy/install_arabic.sh /root/install_arabic.sh
sudo chmod 700 /root/install_arabic.sh
sudo less /root/install_arabic.sh
sudo bash /root/install_arabic.sh --dry-run \
  --repository git@github-arabic:matoug24/arabic.git
```

If `/root/arabic-bootstrap` already exists, inspect it instead of blindly overwriting it. The temporary clone is only for obtaining the file; the installer creates the permanent managed checkout. Do not embed a personal-access token in shell history, installer options, logs or clone URLs.

## 11. Run the installer for the first time

Public repository:

```bash
sudo bash ./install_arabic.sh
```

Private repository:

```bash
sudo bash /root/install_arabic.sh \
  --repository git@github-arabic:matoug24/arabic.git
```

The script performs the following sequence:

1. Takes an exclusive installer lock and validates Ubuntu/repository/domain options.
2. Installs Python/venv, Git, Nginx, curl, certificates and Certbot packages.
3. Creates an unprivileged `arabic` service account and separate persistent state/settings/backup directories.
4. Clones, or fetches and fast-forwards, the exact repository. It refuses dirty checkouts, changed origins and divergent history.
5. Prepares a commit-named release and virtual environment, installs declared dependencies and validates Python/catalog files.
6. Stops the service briefly; backs up any existing database, recordings and session secret.
7. Applies additive migrations without replacing accounts, past homework, answers, media or parent edits.
8. Atomically changes the active release, starts systemd and checks `/healthz` internally.
9. Installs the Nginx configuration and daily private backup timer.
10. Installs `/usr/local/sbin/install-arabic` for subsequent updates.

Until HTTPS is configured, public HTTP serves a 503 preparation notice only. **It does not expose login, bootstrap or family data over HTTP.** Internal Gunicorn health can still be checked on the server.

## 12. Verify DNS before requesting HTTPS

From Windows:

```powershell
Resolve-DnsName arabic.matoug.com -Type A
```

On the server:

```bash
getent ahostsv4 arabic.matoug.com
curl --head http://arabic.matoug.com
curl --fail http://127.0.0.1:8050/healthz
```

DNS must show your static IP. HTTP 503 is expected before certificate setup. If a stale AAAA record sends browsers elsewhere, correct or remove it. Certificate HTTP validation requires public port 80 and a reachable DNS destination. A restrictive CAA record must permit Let's Encrypt if you use it.

## 13. Enable HTTPS

Use an email address you actually monitor for certificate notices. Replace `YOUR_EMAIL`:

```bash
sudo install-arabic --https --email YOUR_EMAIL
```

This requests/renews a Let's Encrypt certificate using a webroot challenge, writes the HTTPS server/HTTP redirect, validates and reloads Nginx, enables the Certbot timer and installs a renewal reload hook. The `--https` option accepts Let's Encrypt's subscriber terms; read them and choose to run that command yourself. [Ubuntu Certbot options](https://manpages.ubuntu.com/manpages/noble/man1/certbot.1.html).

Verify:

```bash
curl --head https://arabic.matoug.com
sudo certbot certificates
sudo systemctl status certbot.timer --no-pager
sudo certbot renew --dry-run
```

An unauthenticated app page redirects to login/setup. That is expected. Do not claim HTTPS is active until these checks and the browser succeed without certificate warnings. If Certbot fails, the app's private state remains; the HTTP preparation notice stays in place. Fix DNS/ports, then repeat the HTTPS command rather than repeatedly creating new certificates.

## 14. Create the first parent account securely

Only if no parent account exists, the installer prepares a random one-time token in private server storage. Read it over your authenticated SSH session:

```bash
sudo cat /var/lib/arabic/setup-token
```

Open **https://arabic.matoug.com/setup** in your browser. Enter the token, your chosen parent username and a password of at least 12 characters. The token is submitted in the form, never in the URL, and is deleted after setup. There is no default production password. Secure cookies are enabled and setup requires HTTPS. If an account already exists, setup redirects to login and no replacement account is created.

If an initial token was lost before setup, use the server utility; it refuses to re-enable bootstrap after a parent exists:

```bash
sudo -u arabic env ARABIC_STATE_DIR=/var/lib/arabic \
  /opt/arabic/current/.venv/bin/python \
  /opt/arabic/current/tools/server_setup.py --show-token
```

Keep this token private. The installer itself never prints it to logs.

## 15. Review content and add real recordings

All 2,000 entries have local pictures and attribution. Parent Content shows twenty categories and all ten levels. Choose **Preview child experience** to inspect draft cards, including random category study across levels, before adding recordings.

For each card: select the English sense; approve its picture; enter the family's Libyan Arabic and approved spelling variants; record your own pronunciation; preview and publish. No machine translation or supplied voice is called your validated dialect/recording. Original diagrams explain some abstract concepts using English labels. Some relational pictures need spoken context, so review them before publication and picture quizzes.

Recording works on **HTTPS** and localhost. In the browser, grant the microphone permission when you choose Record, speak, Stop, preview, then Save. Re-record or upload a real recording if needed. If you deny permission, use the site's microphone settings to change it or upload a file. Save text edits before uploading, because uploads refresh the editor and reset publication for review. Unpublished cards never enter real child homework/category batches.

## 16. Create separate child accounts and check learning

In Parent → Children, create each child's account. Verify each can sign in and only sees their own progress. Prepare the first assignment's twenty cards before a child starts homework. Check practice position after reload, replay, review, the five-question quiz and Arabic keyboard. Retrying a quiz question does not change first-answer accuracy.

Category study is separate: it samples up to ten published cards from the chosen category across **all levels**. A new batch/refresh reshuffles and avoids the previous words where the category is large enough. Homework still uses twenty new words and ten assignments per level. Review-only days pause new assignments.

## 17. Move a word without losing history

In Parent → Content → word editor, choose **Move to level** and **Swap with slot**. Read the destination-word preview and affected-child count, then Save. Both levels remain at 200 entries because the two words exchange slots. Moving is allowed even after a child has started.

Already issued homework retains its original twenty-card snapshot, including its original approved recording/spelling. Old quizzes retain their prompt/answer snapshots; activity and accuracy remain attached to the same word IDs. For unissued slots, each child's plan follows the changed placement where possible while keeping all 2,000 words unique. If one swapped word already belongs to issued homework, a future word may remain in a later available slot for that child instead of being inserted into completed homework. New children follow the new global placement. The app records the swap in placement history.

## 18. Update by rerunning the same installer

After new source has been committed and pushed to GitHub:

```bash
sudo install-arabic
```

Or rerun the original downloaded file with `sudo bash ./install_arabic.sh`. Saved repository/domain/branch choices are retained. The updater handles updates to its own installer once per run. Existing valid HTTPS certificates are detected and retained; normal code updates do not issue new certificates.

Updates refuse to discard server checkout modifications or force-reset Git history. Do not edit deployed code by hand; edit/push the repository. State, private keys, recordings and backups are outside code releases. A repeated run at the same commit reuses the completed release/venv rather than rebuilding it, then validates/restarts. An incomplete staging release is rebuilt before activation. Previous releases are retained for rollback.

## 19. Check service, health and logs

```bash
sudo systemctl status arabic --no-pager
curl --fail http://127.0.0.1:8050/healthz
sudo journalctl -u arabic -n 100 --no-pager
sudo nginx -t
sudo systemctl status nginx --no-pager
sudo systemctl list-timers arabic-backup.timer certbot.timer
readlink -f /opt/arabic/current
sudo git -C /opt/arabic/repository log -1 --oneline
```

`/healthz` returns only status, not private information. The service starts at boot and restarts on failure. Nginx access/error logs are under `/var/log/nginx`. Use `sudo journalctl -u arabic -f` to watch app errors during a check; Ctrl+C stops watching, not the app. Do not post logs containing personal data, setup tokens or credentials publicly.

## 20. Create backups and copy them off the server

Every update makes a pre-update private archive. The daily timer runs at 03:30 **server-local time** and catches up after downtime. It is independent of the app's family timezone used for assignments. Backup contents: a consistent SQLite snapshot, all saved/replaced uploads, session secret, and initial token if setup is still pending. Public picture files ship with Git releases and can be fetched again.

Make a manual backup:

```bash
sudo systemctl start arabic-backup.service
sudo journalctl -u arabic-backup.service -n 20 --no-pager
sudo ls -lh /var/backups/arabic
df -h /var/lib/arabic /var/backups/arabic
```

Do not leave your only backup on the same Lightsail disk. Copy a chosen archive offsite using your SSH client or another private backup process. Archives are root-readable (0600); to retrieve one as the `ubuntu` SSH user, make a private temporary copy:

```bash
sudo install -o ubuntu -g ubuntu -m 600 \
  /var/backups/arabic/YOUR_BACKUP_FILENAME.zip /home/ubuntu/arabic-private-backup.zip
```

From Windows:

```powershell
scp -i "C:\path\to\YOUR_LIGHTSAIL_KEY.pem" \
  ubuntu@YOUR_STATIC_IP:/home/ubuntu/arabic-private-backup.zip \
  "C:\path\to\private-backups\arabic-private-backup.zip"
```

Then remove only that temporary server copy: `rm /home/ubuntu/arabic-private-backup.zip`. Store downloaded backups privately. They contain family audio, progress and password hashes. The installer does not automatically delete old backups; monitor disk use and remove older archives only after verifying offsite copies and retaining a recent known-good restore point. Parent **Download private backup** is another option; it intentionally excludes the server session secret, so restoring it signs users out.

## 21. Restore a backup safely

Restoring replaces current state, so choose a backup deliberately. Stop writes first and make a last-chance backup before replacing anything. Never extract an archive over a running SQLite database.

```bash
sudo systemctl stop arabic
sudo systemctl start arabic-backup.service
sudo install -d -m 700 /root/arabic-restore
sudo /opt/arabic/current/.venv/bin/python -m zipfile -e \
  /var/backups/arabic/YOUR_BACKUP_FILENAME.zip /root/arabic-restore
sudo ls -la /root/arabic-restore
```

Confirm the archive is your own backup and contains `learning.sqlite3` and `media/`. Preserve the current state directory by renaming it (the app is stopped):

```bash
RESTORE_STAMP=$(date -u +%Y%m%dT%H%M%SZ)
sudo mv /var/lib/arabic "/var/lib/arabic-before-restore-$RESTORE_STAMP"
sudo install -d -o arabic -g arabic -m 750 /var/lib/arabic
sudo cp /root/arabic-restore/learning.sqlite3 /var/lib/arabic/learning.sqlite3
sudo cp -a /root/arabic-restore/media /var/lib/arabic/media
```

If present, copy `session-secret` too; otherwise the app generates a fresh one and users sign in again. A production backup includes it:

```bash
if sudo test -f /root/arabic-restore/session-secret; then
  sudo cp /root/arabic-restore/session-secret /var/lib/arabic/session-secret
fi
sudo chown -R arabic:arabic /var/lib/arabic
sudo chmod 750 /var/lib/arabic
sudo systemctl start arabic
curl --fail http://127.0.0.1:8050/healthz
```

No old WAL/SHM files are copied into the new state directory. Check a parent login, child progress and several recordings before discarding the preserved old folder. For a replacement instance, install the application/certificate first, then restore state before allowing the family to use it. Reset `/root/arabic-restore` between restore attempts only after confirming its exact contents/path and preserving needed files.

## 22. Roll back code without discarding new learning

List retained release commits:

```bash
ls /opt/arabic/releases
readlink -f /opt/arabic/current
sudo git -C /opt/arabic/repository log --oneline -10
```

Activate a known prior commit:

```bash
sudo install-arabic --rollback YOUR_KNOWN_COMMIT_HASH
```

This creates a backup, activates that code, and preserves current state. The commit must exist in the local Git repository. Do not restore an old database merely to roll back a UI change: that would lose later practice. Migrations in this version are additive and restart-safe. If a future release makes an incompatible schema change, consult its migration notes and deliberately restore the matching pre-update backup while the service is stopped. Automatic failed-health recovery restores prior code where available and never silently overwrites the database.

## 23. Troubleshoot common failures

| Symptom | Checks and action |
| --- | --- |
| Clone/download 404 or authentication failure | Confirm repository publication/visibility and `main`. For private access, use the read-only deploy key and SSH clone path; no tokens in URLs. |
| Dirty checkout / origin differs / fast-forward refused | Inspect `sudo git -C /opt/arabic/repository status` and remote/history. Preserve local changes; resolve deliberately. The installer never force-pushes or discards them. |
| Public HTTP 503 | Expected before HTTPS. Check DNS and public 80, then run the HTTPS installer option. |
| Certbot validation fails | A/AAAA must point to this server; 80 must be publicly reachable; check CAA and Nginx logs. Avoid repeated certificate requests while DNS is wrong. |
| HTTPS 502 | Check `systemctl status arabic`, journal and internal 8050 health; validate Nginx. Do not open 8050 publicly. |
| Setup 403 | Production requires HTTPS and the one-time server token. Existing accounts disable setup. Check `ARABIC_PRODUCTION`, proxy headers and `/etc/arabic/app.env`. |
| Login loop or lost session after restore | Confirm HTTPS, secure cookies, domain and secret file ownership. Clearing old cookies or signing in again may be needed after a new secret. |
| Microphone unavailable | Use HTTPS/localhost, grant site microphone permission, and check browser/device input or try another recording-capable device. |
| Upload 413 | App/Nginx limit is 12 MB including multipart overhead. Use a shorter/smaller recording. |
| Homework unavailable | Every one of its twenty snapshot/plan cards must be published with approved Arabic/image and saved audio. Prepare the next batch in Content. |
| Disk full / backups fail | Check recordings/backups sizes and free space, copy backups offsite, retain known-good archives before deleting older copies. |
| Installer health failure | Read journal, inspect retained releases and private backup. Previous code is restored where available; state is preserved. |

## 24. What has and has not been tested

Application integration tests cover separate accounts, random all-level categories, twenty-category completeness, movement/snapshot/replanning history, quiz scoring/hiding, Arabic alignment, uploads, analytics and backups. Installer tests exercise first/repeated/new-release orchestration, refusing dirty/wrong-origin checkouts, preserving state/settings, HTTPS configuration preservation and failed-health rollback in an isolated filesystem with mocked Ubuntu commands. Bash syntax is checked with a real Bash interpreter.

**No live Lightsail/Ubuntu provisioning or Certbot certificate issuance has been performed.** The first real server run must validate actual apt packages, systemd, Nginx, repository authentication, DNS and certificates. This limitation is deliberate: paid resources and public deployment/DNS changes were not authorized. The reference `TeraCota_Tracking_site` was inspected read-only for its Ubuntu/systemd/Nginx/fast-forward/backups/health approach; its secrets and operational data were not copied.

## 25. Optional example recordings

The parent word editor supports multiple spoken examples alongside the required word pronunciation. Use Record example inside Your pronunciation, preview before saving, play saved examples and remove examples. Audio uploads and example label fields are absent from this editor. HTTPS is required for microphone access online. Empty examples are valid; they never enter quizzes or publication/homework requirements. The former single sentence recorder is also absent; previously saved sentence recordings remain available to children.

Update an existing server with `sudo install-arabic`. The additive version-3 migration creates a separate example table without replacing accounts, progress, issued snapshots or existing media. Example metadata resides in `/var/lib/arabic/learning.sqlite3`; audio resides in `/var/lib/arabic/media`. Both private web exports and server backups include examples, so the existing restore procedure applies. Keep family recordings out of GitHub. Removed/replaced recordings remain archived privately like replaced pronunciation recordings; children cannot access removed example routes.
