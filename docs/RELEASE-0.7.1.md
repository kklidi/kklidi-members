# 0.7.1 release evidence and deployment gates

0.7.1 preserves the Core-auth Members MVP and adds repeatable evidence for the actual
LMS boundary and plugin lifecycle. It does not add email verification, 2FA, social
login, automatic PII deletion, custom authentication cookies, PHP-session auth, or a
Members-owned Woo/LMS/KBoard permission domain.

Credential-free aggregate evidence is in the repository sidecar
[evidence/0.7.1.json](evidence/0.7.1.json). The evidence and package manifest are kept
outside the installable ZIP so the lifecycle report can bind the final ZIP hash without
creating a self-referential archive.

## Local release gate

- All 24 MVP behavior contracts pass in disposable WordPress sites with two prefixes.
- The fixed MAMP LMS gate preserves one WordPress user ID across order, enrollment,
  progress, certificate and question records, then verifies Members-off fallback.
- The lifecycle gate covers fresh install, 0.7.0-to-0.7.1 update, reinstall,
  deactivation fallback and reactivation while preserving protected data fingerprints.
- Every fixture uses synthetic run markers and reports exact cleanup.
- The allowlisted ZIP excludes tests, caches, credentials, private keys and fixture data.
- The installable ZIP includes the Korean PO/MO catalog and source POT; browser
  acceptance verifies rendered Korean rather than only checking the source catalog.

## Production acceptance

Production acceptance remains `PARTIAL`. A local CA and one-host process campaign do
not prove the real certificate, CDN/load-balancer trust configuration, or shared-DB
behavior across actual application nodes. Complete the credential-free deployment
manifest, backup restore evidence, bounded rollback rehearsal and the minimum 14-day
observation window before declaring production acceptance.

Run the fixed-sandbox gates and deployment checks from `tests/harness/README.md` and
`docs/OPERATIONS.md`. The installable package is `dist/kklidi-members-0.7.1.zip`.
