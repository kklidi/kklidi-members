=== KKLIDI Members ===
Contributors: kklidi
Requires at least: 7.1
Tested up to: 7.1
Requires PHP: 8.3
Stable tag: 0.6.0

Core-based member accounts with scoped UI, consent records and safe withdrawal handling.

== Description ==

WordPress Core owns users, passwords, sessions and authentication cookies.
KKLIDI Members adds login, registration, profile, consent and account management UI.
WooCommerce orders and LMS enrollment/progress stay with their respective plugins.
Korean UI uses WordPress gettext translation catalogs.

0.6.0 closes the bounded D01/D02/D06 policy gates and adds real Chrome,
registration/reset race, and enumeration-timing evidence. See docs/RELEASE-0.6.0.md.
Production TLS, persistent-cache/proxy failure, and production migration remain
environment-specific gates.

== Installation ==

1. Upload the kklidi-members ZIP to a test WordPress single-site installation.
2. Activate the plugin and open Tools > KKLIDI Members.
3. Review registration and consent policy before changing the closed defaults.

== Changelog ==

= 0.6.0 =
* Core registration authority and bounded 1.0 signup/withdrawal policy decisions.
* Actual Chrome, Apache race, timing, and read-only legacy ownership evidence.

= 0.5.0 =
* Core account MVP, localized frontend/admin UI, bounded LMS profile delegation.
* Actual Woo/KBoard compatibility fixtures and parallel limiter verification.
