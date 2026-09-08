# 0.7.2 release evidence and deployment gates

0.7.2 preserves the verified 0.7.1 Core-auth runtime. It corrects Phase 0 status
wording so completed UI work and historical partial results cannot be mistaken for the
current release verdict. It adds no OPTIONAL/FUTURE authentication feature and changes
no identity, WooCommerce, LMS or KBoard ownership boundary.

Credential-free aggregate evidence is stored outside the installable archive in
`docs/evidence/0.7.2.json`. The package manifest is also an external sidecar so the
lifecycle report can bind the final ZIP hash without a self-referential rebuild.

## Local release gate

- All 24 MVP behavior contracts execute successfully in disposable WordPress sites
  using both the default and a non-default table prefix.
- Actual fixed-MAMP WooCommerce, LMS, KBoard, concurrency, timing, HTTPS and Chrome
  evidence remains required and is refreshed for this release.
- The lifecycle gate covers fresh installation, 0.7.1-to-0.7.2 update, reinstall,
  deactivation fallback and reactivation while preserving protected WordPress and
  integration-domain fingerprints.
- The lifecycle runner probes MAMP write access before mutation and uses atomic
  same-volume directory moves. The TLS runner confines OpenSSL random state to its
  disposable certificate directory.
- The installable ZIP includes the Korean PO/MO catalog and excludes tests, caches,
  credentials, private keys and fixture data.

## Production acceptance

Production acceptance remains `PARTIAL` until a real trusted HTTPS staging environment
has an approved credential-free deployment manifest, accountable owners, a backup hash,
separate restore-test evidence, actual proxy/multi-node checks where applicable, and the
minimum 14-day observation window with an actual order and account recovery.

Run the fixed-sandbox gates and deployment checks from `tests/harness/README.md` and
`docs/OPERATIONS.md`. The installable package is `dist/kklidi-members-0.7.2.zip`.
