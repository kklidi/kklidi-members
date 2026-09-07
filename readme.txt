=== KKLIDI Members ===
Contributors: kklidi
Requires at least: 6.1
Tested up to: 7.1
Requires PHP: 7.4
Stable tag: 0.5.0

Core-based member accounts with scoped UI, consent records and safe withdrawal handling.

== Description ==

WordPress Core owns users, passwords, sessions and authentication cookies.
KKLIDI Members adds login, registration, profile, consent and account management UI.
WooCommerce orders and LMS enrollment/progress stay with their respective plugins.
Korean UI uses WordPress gettext translation catalogs.

0.5.0 is a development validation release. See docs/RELEASE-0.5.0.md for unresolved
production policy, HTTPS/browser and concurrency verification gates.
The minimum-version declarations above are not a tested multi-version matrix.

== Installation ==

1. Upload the kklidi-members ZIP to a test WordPress single-site installation.
2. Activate the plugin and open Tools > KKLIDI Members.
3. Review registration and consent policy before changing the closed defaults.

== Changelog ==

= 0.5.0 =
* Core account MVP, localized frontend/admin UI, bounded LMS profile delegation.
* Actual Woo/KBoard compatibility fixtures and parallel limiter verification.
