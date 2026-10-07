# Implementation verification

- All 39 automated application and installer tests passed. Python compilation and JavaScript/Bash syntax checks passed.
- Catalog validation passed: 2,000 unique IDs and lemma keys, ten levels of 200 positions, twenty populated categories, and attributed local images for all entries.
- Every image decoded successfully, including SVG rasterization. All forty catalog contact sheets were visually inspected; 122 corrections were inspected in three additional sheets. Parent approval remains required.
- Application checks cover authentication/access separation, CSRF, upload/publication, scheduling/resume, immutable assignment snapshots, cross-level swaps and unique future plans, quizzes and ambiguous distractors, Arabic variants/feedback, reviews, random all-level exploration and separate practice, tracking deduplication, time caps, analytics and private backups.
- Production setup checks cover HTTPS, one-time parent setup token and secure cookies. Installer simulations cover first/repeat/update runs, state preservation, refusal of dirty/wrong repositories, failed-health rollback, private backups, retained TLS configuration and pre-TLS HTTP denial.
- Earlier representative browser checks covered child practice/resume, completion, quiz feedback/writing and parent preview/editor. Actual microphone recording requires the parent's permission and voice and was not exercised.

Installer tests mock Ubuntu commands; no live apt, systemd, Nginx, Certbot or Lightsail provisioning was performed. Bash syntax was checked using Git Bash. DNS and certificates for arabic.matoug.com have not been changed or verified as deployed. TeraCota deployment files were inspected read-only as a reference.

Tests use disposable databases under test-output. Real instance data, accounts, recordings, secrets and test artifacts are excluded from source publication. See docs/LIGHTSAIL_DEPLOYMENT.md for numbered installation and restore instructions.
