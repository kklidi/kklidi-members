=== KKLIDI Members ===
Contributors: kklidi
Requires at least: 7.1
Tested up to: 7.1
Requires PHP: 8.3
Stable tag: 0.7.6

Core-based member accounts with scoped UI, consent records and safe withdrawal handling.

== Description ==

WordPress Core owns users, passwords, sessions and authentication cookies.
KKLIDI Members adds login, registration, profile, consent and account management UI.
WooCommerce orders and LMS enrollment/progress stay with their respective plugins.
Korean UI uses WordPress gettext translation catalogs.

0.7.6 implements the account, profile, consent and password UX, a WordPress Core
password-reset wrapper, and plugin-owned link-only account navigation slots. See
docs/RELEASE-0.7.6.md.

== Installation ==

1. Upload the kklidi-members ZIP to a test WordPress single-site installation.
2. Activate the plugin and open Tools > KKLIDI Members.
3. Review registration and consent policy before changing the closed defaults.

== Changelog ==

= 0.7.6 =
* Added the account, profile, consent and password UX states with linked validation errors and route-scoped password controls.
* Added a branded reset wrapper that uses only WordPress Core reset-key APIs and returns a generic request response.
* Added local link-only account navigation slots registered by optional plugins without reading WooCommerce or LMS data.

= 0.7.5 =
* Implemented the server-rendered login and registration shell with safe input recovery, field-level errors, consent details, and Core password visibility enhancement.
* Added route-scoped authentication JavaScript and a clean-route collision preflight while preserving query-route fallback.
* Added Korean translations for the new login and registration states.

= 0.7.4 =
* Added an executable strategy contract for the approved frontend and administrator information architecture.
* Corrected the documented new-account login strategy to match the private opaque Core user_login implementation.
* Fixed the implementation sequence and boundaries for versions 0.7.5 through 0.7.9 without implementing those features early.

= 0.7.3 =
* Added four fixed plain-text account notices using the current WordPress user email and locale.
* Added Korean translations for all account-notice subjects and bodies.
* Verified that mail failure preserves committed account state and session revocation while recording failure without delivery or retry claims.

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
