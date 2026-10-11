# Arabic, together

A private Flask/SQLite family learning app: 2,000 entries, ten levels of 200, twenty categories, parent-approved Libyan Arabic and personal recordings.

## Start locally

Python 3.11+: create a virtual environment, install requirements.txt, then run python app.py. Open http://127.0.0.1:5000. Create your own parent account (minimum twelve-character password), then separate child accounts. There are no default real credentials. Local first-run setup accepts loopback only and closes after the first account. Private state lives in instance/ and is excluded from Git.

## Prepare lessons

Every entry has an attributed local image: 1,705 ARASAAC pictograms, 66 Commons photographs and 229 original concept diagrams. All entries were visually inspected, including 122 subsequent corrections. English senses and images remain candidates for parent approval. No dialect spelling or parent's voice is fabricated.

In Content, review the grammar and picture; enter approved Arabic spellings one per line, with the default first; record pronunciation; approve and publish. One spelling is enough, and additional lines are accepted alternatives. All twenty cards must be ready for a homework batch. New recordings and picture uploads reset publication. Microphone recording requires localhost or HTTPS. Parent preview includes drafts without affecting child progress.

Moving a word swaps the destination position, keeping 200 entries per level even after learning begins. The editor previews the destination. Issued homework, quiz answers and activity retain their original snapshots. Future assignments follow a rebalanced per-child plan without duplicate entries.

## Optional spoken examples

Use Record example inside Your pronunciation to add optional spoken examples. Listen before saving, play saved examples or remove them. No upload, label or written sentence is required. Examples appear in a collapsed optional section on child word cards, homework, reviews, exploration and parent previews. They never enter quizzes, scoring, homework-completion or publication requirements. Required word pronunciation remains the quiz audio. Example playback is not counted as a pronunciation start/completion; visible engagement may still contribute to estimated active time.

Examples are stored in the private database/media directory and included in private exports and server backups. They follow the current word even for issued homework, without changing assignment or quiz snapshots. Removing an example removes its child playback route; old media files remain private in storage/backups, following the existing replaced-recording policy. Earlier single sentence recordings remain available and are also excluded from pronunciation counters.

## Learning and analytics

- Homework contains twenty entries, saves position/practice incrementally, and never skips content after missed days. The next assignment opens on the next local day after completion. Ten assignments make a level.
- Reviews contain up to five distinct previously completed entries, including older work and mistakes. Parents can pause new homework.
- Explore chooses random batches of up to ten ready category/topic entries across all levels. Visits and practice save separately and never advance homework. Parent preview includes drafts.
- Five-question quizzes include listening-to-English, picture-to-Arabic and Arabic writing. Listening prompts conceal answer vocabulary until submission. Choices exclude ambiguous approved spellings and duplicate images. Writing accepts approved variants and shows letter alignment while preserving RTL joining. First answers and correction attempts are tracked separately.
- End-level review requires four of five correct first answers to advance. Completion, practice and growing-confidence evidence remain distinct.

Parent analytics separate visits/revisits, homework/review/exploration, audio starts/completions, first-answer accuracy/corrections and later-day rechecks. Active minutes use visibility/interaction, idle limits and server caps; these are engagement estimates, not proof of learning.

## Ubuntu Lightsail

Follow [the numbered deployment guide](docs/LIGHTSAIL_DEPLOYMENT.md) for arabic.matoug.com and [the GitHub repository](https://github.com/matoug24/arabic). The single installer is [deploy/install_arabic.sh](deploy/install_arabic.sh), supporting initial installation, repeat updates, HTTPS and rollback.

Ubuntu 24.04 uses Gunicorn/Nginx, a dedicated systemd account, immutable releases and persistent private state under /var/lib/arabic. Production setup requires HTTPS and a one-time server token. Updates check Git fast-forward state and back up before migration. HTTP serves an installation notice until TLS is configured. Code rollback preserves state.

AWS resources, static IP, DNS and actual installation remain operator steps. No cloud resources or DNS records were changed. Installer tests simulated commands; no live Ubuntu host was provisioned.

## Backups

The parent export contains a consistent database and uploaded media; protect it because it includes accounts and family recordings. Static catalog pictures remain in the project. Private server backups also include the signing secret and initial setup token, with a daily systemd timer. Keep off-server copies. Follow the guide's stop/back-up/restore sequence; never overwrite running SQLite.

## Sources and licenses

- Adapted curriculum: NGSL 1.2 by Charles Browne, Brent Culligan and Joseph Phillips, [official source](https://www.newgeneralservicelist.com/new-general-service-list), CC BY-SA 4.0, with editorial additions/order/categories. This is not a universal Arabic frequency ranking.
- ARASAAC: Sergio Palao, Government of Aragon, [terms](https://arasaac.org/terms-of-use), CC BY-NC-SA 4.0. Attribution, noncommercial use and share-alike apply.
- Commons photographs: individual creator/source/license per card, CC BY, CC BY-SA or public-domain terms.
- Original concept diagrams: Arabic, together, CC BY-SA 4.0; abstract concepts may need spoken context.
- [Birzeit Lisan](https://sina.birzeit.edu/currasat/about-en.html) is a possible reference; no corpus text/audio was imported. Parent uploads need permission for their reuse.

Cards link to image sources and the app has a Credits page. Preserve per-asset licenses.

## Developer verification

Run python -m unittest discover -s tests -v; python -m compileall -q app.py curriculum.py migrations.py tools tests; python tools/validate_catalog.py; node --check static/app.js. See [VERIFICATION.md](VERIFICATION.md) and [CONTENT_REVIEW.md](CONTENT_REVIEW.md).

The reviewed data/curriculum.json is the deliverable. Rebuilding is a developer action, not a parent workflow, and does not directly update a live database. Source/matching tools retain provenance. prepare_catalog applies twenty categories; apply_image_review applies explicit corrections. review_all_images generates contact sheets/manifests using optional QA-only resvg-py. Do not overwrite the reviewed catalog with an unreviewed rebuild.

tools/serve_ui_test.py runs disposable fixtures on port 5001: mock Arabic, silent recordings and testing-password. These never enter real family state. Stop that server after testing.
