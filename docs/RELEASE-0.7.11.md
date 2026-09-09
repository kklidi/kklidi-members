# 0.7.11 development evidence

0.7.11 is a bounded UX clarification release. The withdrawal screen now states
that submitting a request blocks sign-in immediately, preserves the WordPress
user and service records, and enters administrator review before finalization.
The Users-area review copy describes finalization as keeping the account
disabled and restoration as a reasoned action that never revives an existing
session.

The notification settings screen now explains that empty subject and body fields
use the translated default at send time for the recipient locale. Field
placeholders repeat that behavior without changing the stored empty value or the
`AUTH-NOTIFY-002` fallback contract.

SMS, two-factor authentication, social login, provider credentials, mail queues,
and per-event disable controls remain out of scope. WordPress Core remains the
identity, authentication, user-ID, and mail transport boundary.

## Verification

- Python contract guards: 30 passed.
- PHP 8.3 syntax: 32 production PHP files passed.
- One-prefix synthetic WordPress run `95d38795eaf04cbab54c90c7cc8f4668`
  passed all 24 MVP contracts and both notification extension contracts,
  including Core/Members login, registration, withdrawal, mail-failure,
  limiter, device-limit, and Members-off checks. The run was intentionally
  `--one-prefix --skip-perf`, so the two-prefix and timing evidence remains the
  existing release gate.
- Fixed MAMP lifecycle `mamp-lifecycle-aec712b5f5c3` passed install,
  `0.7.10->0.7.11` update, reinstall, deactivate/reactivate, protected user-ID
  and domain fingerprints, and exact source restoration. The final package
  manifest records the release archive SHA-256.

Production certificate/CDN/proxy behavior, distributed application hosts, and
production migration remain deployment-environment gates.
