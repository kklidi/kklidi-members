=== KKLIDI Members ===
Contributors: kklidi
Requires at least: 7.1
Tested up to: 7.1
Requires PHP: 8.3
Stable tag: 0.7.2

Core-based member accounts with scoped UI, consent records and safe withdrawal handling.

== Description ==

WordPress Core owns users, passwords, sessions and authentication cookies.
KKLIDI Members adds login, registration, profile, consent and account management UI.
WooCommerce orders and LMS enrollment/progress stay with their respective plugins.
Korean UI uses WordPress gettext translation catalogs.

0.7.2 keeps the verified Core-auth runtime and clarifies current Phase 0 evidence
without treating historical partial results as the current release verdict. See
docs/RELEASE-0.7.2.md.

== Installation ==

1. Upload the kklidi-members ZIP to a test WordPress single-site installation.
2. Activate the plugin and open Tools > KKLIDI Members.
3. Review registration and consent policy before changing the closed defaults.

== Changelog ==

= 0.7.2 =
* Clarified completed AUTH-UI-002 status and separated historical harness snapshots from the current release verdict.
* Revalidated the unchanged runtime and the 0.7.1-to-0.7.2 package lifecycle.
* Hardened lifecycle file swaps and confined OpenSSL temporary state to owned directories.

= 0.7.1 =
* Repeatable actual-LMS identity, access, fallback and cleanup verification.
* Fresh install, 0.7.0-to-0.7.1 update, reinstall and deactivate/reactivate gate.
* Release evidence now includes both executable gates.
* Korean translation catalogs are included in the installable ZIP.

= 0.7.0 =
* Local TLS, HSTS, host-only guest-cookie and Core Secure-cookie verification.
* Shared-DB limiter behavior during object-cache outage and storage failure.
* Bounded migration rollback and production deployment manifest validation.

= 0.6.0 =
* Core registration authority and bounded 1.0 signup/withdrawal policy decisions.
* Actual Chrome, Apache race, timing, and read-only legacy ownership evidence.

= 0.5.0 =
* Core account MVP, localized frontend/admin UI, bounded LMS profile delegation.
* Actual Woo/KBoard compatibility fixtures and parallel limiter verification.
