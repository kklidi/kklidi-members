# 0.7.3 release evidence and deployment gates

0.7.3 completes `AUTH-NOTIFY-001` P0-1 through P0-4. It adds fixed plain-text
notices for completed registration, self-service password changes, withdrawal requests,
and administrator-finalized withdrawals. Messages use the current WordPress user email,
the WordPress user locale with site fallback, and the bundled Korean PO/MO catalog.

Notification dispatch remains downstream of the committed account transition. A failed
`wp_mail()` call does not roll back registration, password changes, session revocation,
withdrawal blocking, or final disablement. Failure is recorded as
`failure/wp_mail_failed`; the plugin does not claim delivery and does not add a retry
queue, SMTP provider, or notification-management UI.

Credential-free aggregate evidence is stored outside the installable archive in
`docs/evidence/0.7.3.json`. The package manifest remains an external sidecar so the
lifecycle report can bind the final ZIP hash without a self-referential rebuild.

## Local release gate

- All 24 MVP behavior contracts plus `AUTH-NOTIFY-001` execute in disposable WordPress
  sites using both the default and a non-default table prefix.
- `AUTH-NOTIFY-001` verifies four accepted notices, Korean site/user locale rendering,
  and four injected mail failures per prefix with committed state and revoked sessions
  preserved, four failure audit rows, zero delivery records, and zero retry attempts.
- The fixed-MAMP gates cover WooCommerce, LMS, KBoard removal compatibility,
  concurrency, timing, local TLS, and the package lifecycle.
- The 0.7.2 Chrome responsive UI evidence is reused because 0.7.3 does not change
  frontend HTML, CSS, or JavaScript; current runtime, integration, and package gates
  are refreshed for this release.
- The lifecycle gate covers fresh installation, 0.7.2-to-0.7.3 update, reinstall,
  deactivation fallback, and reactivation while preserving WordPress user IDs and
  integration-domain fingerprints.
- The installable ZIP includes the Korean PO/MO catalog and excludes tests, caches,
  credentials, private keys, fixture data, and release evidence sidecars.

## Production acceptance

Production acceptance remains `PARTIAL` until a real trusted HTTPS staging environment
has an approved credential-free deployment manifest, accountable owners, a backup hash,
separate restore-test evidence, actual proxy/multi-node checks where applicable, and the
minimum 14-day observation window with an actual order and account recovery.

Run the fixed-sandbox gates and deployment checks from `tests/harness/README.md` and
`docs/OPERATIONS.md`. The installable package is `dist/kklidi-members-0.7.3.zip`.
