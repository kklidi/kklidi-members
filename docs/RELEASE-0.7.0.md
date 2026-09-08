# 0.7.0 release evidence and deployment gates

## Scope

0.7.0 hardens the existing Core-based Members MVP. WordPress Core remains the user, password, reset-key, session and auth-cookie owner. The release adds no custom authentication cookie, PHP-session authentication, user-ID migration, Woo/LMS ownership, or OPTIONAL/FUTURE authentication feature.

## Verified

Credential-free aggregate evidence is in [evidence/0.7.0.json](evidence/0.7.0.json).

- The disposable WordPress harness executes all 24 MVP contracts on `wp_` and an arbitrary prefix and removes its owned database and filesystem.
- The rate limiter uses the shared MySQL options table under `GET_LOCK`. Eight independent PHP processes make 100 calls and exactly 10 are allowed. An object-cache adapter that throws is not called; an unavailable DB storage table returns the limiter-unavailable error.
- The local MAMP TLS harness uses a per-run CA with hostname verification. TLS 1.3, HSTS, private/no-store, `__Host-` Secure/HttpOnly/SameSite/host-only guest cookies, Core Secure/HttpOnly cookies, authenticated account rendering and no Members PHP session pass.
- Eight concurrent registrations converge on one subscriber and two required consents. Eight pre-opened Core reset forms converge on one final password and the key cannot reopen a reset form.
- Woo checkout login returns to the checkout with its cart, renders only the member order, does not claim the same-email guest order, and preserves device-limit allow/block behavior.
- Existing and missing identifiers use the same public login message. Nine samples per group have a local median ratio of 1.339, below the 2.0 investigation threshold.
- Legacy consent dry-run/import/re-run is idempotent. The rehearsal removes only imported legacy rows, restores the target row count, leaves source meta unchanged, preserves Core IDs, and can be run again.

## Deployment gates still open

The local CA and loopback TLS proxy validate application behavior but are not evidence for the real certificate, CDN/load balancer trust rules or multiple application hosts. Run `deployment_preflight.py` against the trusted HTTPS staging URL and execute the distributed campaign on every real node.

Production/reference data was not mutated. Complete a credential-free deployment manifest from `tests/harness/deployment_manifest.example.json`, including accountable roles, backup hash, separate restore-test evidence, bounded rollback and the minimum observation window. `validate_deployment_manifest.py` must return `READY` before production acceptance.

D03 marketing purpose/channel/withdrawal wording remains a user decision. D04 keeps display-name duplicates allowed and D05 keeps legacy email state `legacy_unknown` as conservative defaults. Email signup verification, TOTP/2FA, social login and automatic PII deletion remain OPTIONAL/FUTURE and are not implemented in this release.

KBoard permission parity and content migration remain outside Members because KBoard is scheduled for removal.

## Reproduce and install

See `tests/harness/README.md` and [OPERATIONS](OPERATIONS.md). The installable package is `dist/kklidi-members-0.7.0.zip`; its SHA-256 manifest is generated beside it. Test code, caches, credentials, private keys and fixture data are excluded from the ZIP.
