# 0.6.0 release evidence and deployment gates

## Scope

0.6.0 keeps WordPress Core as the identity, password, reset-key, session and auth-cookie
owner. It does not remap user IDs, claim Woo/LMS/KBoard data, create PHP-session auth,
or add optional/FUTURE authentication modules.

## Product decisions closed

- D01: Core `users_can_register` is the only public-registration switch. Required
  documents still fail closed. Phone is optional; email verification and automatic
  login are not part of 1.0.
- D02: withdrawal immediately blocks login and revokes Core sessions/application
  passwords, then enters a manual queue. Members keeps the Core ID and does not
  automatically erase or claim completion for external-domain data. Site privacy and
  domain owners decide lawful retention and actual erasure.
- D06: payout owns the instructor/partner settlement pages and menus; LMS/LearnDash
  owns classroom access; site content operations owns the two static application pages.
  Members gains no generic page-restriction engine.
- D07: the supported 0.6.0 runtime baseline is WordPress 7.1, PHP 8.3, single-site.
  WooCommerce 11.1.0 is the tested optional integration. PHP 7.4–8.3 syntax lint is
  recorded separately and is not a multi-version runtime support claim.

## Verified

Credential-free aggregate evidence is in [evidence/0.6.0.json](evidence/0.6.0.json).

- Disposable WordPress behavior harness: all 24 MVP contracts, two prefixes, Core and
  Members identity continuity, bounded writes and exact cleanup.
- Fixed MAMP Woo, LMS and KBoard ownership/optional-dependency flows.
- Eight simultaneous same-email registrations created one subscriber and two required
  consent rows. Eight pre-opened Core reset forms produced one matching final password
  and no reusable reset form.
- Existing/missing login identifiers returned the same public message; nine samples per
  group measured a 1.018 median-time ratio in the local MAMP stack.
- Chrome 152 executed the real page and device fingerprint script, created the device
  fingerprint/signature cookies, reported no console/JavaScript errors, and had no
  horizontal overflow at 360px.
- The fixed reference D06 audit used a read-only transaction, did not bootstrap
  WordPress, and rolled back before disconnecting.

## Environment gates still open

The MAMP site is HTTP and has no external persistent object cache. It cannot prove
trusted production TLS, HSTS, Core Secure auth-cookie flags, reverse-proxy trust, or
persistent-cache outage behavior. `deployment_preflight.py` refuses HTTP and
credentials; run it against the actual trusted HTTPS staging URL.

Distributed multi-node abuse and production migration require an explicitly identified
deployment environment and accountable owners. No production/reference data was
mutated. Before production migration, record backups, route owners, domain retention
decisions, rollback responsibility and an observation window. KBoard permission parity
and content migration remain outside Members because KBoard is scheduled for removal.

## Reproduce and install

See `tests/harness/README.md`. The installable package is
`dist/kklidi-members-0.6.0.zip`; its SHA-256 manifest is generated beside it. Test code,
caches, credentials and fixture data are excluded from the ZIP.
