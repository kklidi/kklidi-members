=== KKLIDI Members ===
Contributors: kklidi
Requires at least: 7.1
Tested up to: 7.1
Requires PHP: 8.3
Stable tag: 0.7.31

Core-based member accounts with scoped UI, consent records and safe withdrawal handling.

== Description ==

WordPress Core owns users, passwords, sessions and authentication cookies.
KKLIDI Members adds login, registration, profile, consent and account management UI.
WooCommerce orders and LMS enrollment/progress stay with their respective plugins.
Korean UI uses WordPress gettext translation catalogs.

0.7.25 improves withdrawal reauthentication feedback, adds password visibility,
and qualifies the immediate access block and retention-period processing copy.
0.7.24 unifies required-field metadata and visible asterisks across registration,
and labels always-required fields as fixed in the administrator settings.
0.7.23 centers the short login and password-reset routes, removes the redundant
site-name eyebrow, and presents login links as Sign up | Find password | Home.
0.7.22 refines the password controls, required-field indicators, and concise
frontend wording. 0.7.21 adds optional fixed /members/ clean routes without creating WordPress
pages or shortcodes. Activation requires pretty permalinks and a conflict-free
preflight; query routes and Core force-reauth remain available as fallbacks.
See docs/RELEASE-0.7.25.md.
See docs/RELEASE-0.7.26.md.
See docs/RELEASE-0.7.29.md.
See docs/RELEASE-0.7.30.md.
See docs/RELEASE-0.7.31.md.

0.7.17 adds administrator diagnostics, quick actions, route links, and clearer
notification, withdrawal, and audit management while preserving the approved
account and mail contracts. See docs/RELEASE-0.7.17.md.

0.7.16 adds accessible password visibility icons, clearer account-link hierarchy,
and a denser responsive Members shell while preserving WordPress Core ownership
of users, passwords, sessions, reset keys, and mail delivery. See
docs/RELEASE-0.7.16.md.

== Installation ==

1. Upload the kklidi-members ZIP to a test WordPress single-site installation.
2. Activate the plugin and open Users > KKLIDI Members.
3. Review registration and consent policy before changing the closed defaults.

== Changelog ==

= 0.7.31 =

* Add a platform-neutral non-cache boundary for Members-owned authentication routes.
* Cover LiteSpeed, reverse proxy, CDN, Cloudflare, and Cloudways-style stacks without global cache hooks.

= 0.7.30 =

* Load the scoped password visibility script on the withdrawal route.
* Verify the withdrawal eye control and responsive account screens in a real Chrome engine.

= 0.7.25 =

* Show a field-level error when withdrawal password reauthentication fails.
* Add the inline password visibility control to withdrawal requests.
* Explain immediate sign-in blocking and retention-qualified processing without promising universal deletion.

= 0.7.26 =

* Separate Members manual menu links from WordPress-generated login and registration links in administrator settings.
* Show the current generated URL beside the Core fallback and clarify that direct wp-login.php access is not redirected.

= 0.7.27 =

* Remove the site-name brand line from all Members route screens.
* Center short screens while allowing long forms to start with a safe top margin.
* Use one shared account-link row and clarify that display name is a public nickname, not a login ID.

= 0.7.28 =

* Keep new registration email-first without collecting a separate username.
* Separate the new account's public user_nicename from its private Core user_login.
* Present email as the primary login and password-reset identifier while retaining legacy username compatibility.

= 0.7.29 =

* Add Members-scoped sender name, sender email, plain-text footer, and administrator-only bounded test mail settings.
* Keep Core reset, WooCommerce, LMS, KBoard, SMTP credentials, and global WordPress mail filters outside the feature.

= 0.7.24 =

* Render required markers from one server-side registration policy.
* Show fixed required account and consent fields in administrator settings.
* Keep first name, last name, and phone as the only configurable fields.

= 0.7.23 =

* Center the login and password-reset cards without changing route ownership.
* Remove the redundant site-name eyebrow from short auth screens.
* Present login links in one same-hierarchy row: Sign up | Find password | Home.

= 0.7.22 =

* Place password visibility controls inside password inputs.
* Mark required fields consistently and simplify frontend copy.

= 0.7.21 =
* Added opt-in fixed clean routes for nine Members screens.
* Rejected plain-permalink, page, rewrite-rule, and endpoint conflicts without changing content.
* Preserved query routes, Core force-reauth, manual menu ownership, and route-scoped assets.

= 0.7.20 =
* Added an opt-in administrator notification after active member registration.
* Kept the recipient in WordPress Core administration settings and the transport in wp_mail().
* Added bounded settings, deduplication, invalid-recipient, failure, and cleanup verification.

= 0.7.19 =
* Added a read-only translated catalog for approved account and security messages.
* Displayed translated default subject and body content beside account-email overrides.
* Added a secret-free password-change completion notice before manual sign-in.

= 0.7.18 =
* Added a Users-area Registration Fields section backed by the WordPress Settings API.
* Limited configuration to required, optional, or hidden states for first name, last name, and phone.
* Kept identity, password, display name, required consent, existing users, WooCommerce orders, and LMS data unchanged.

= 0.7.17 =
* Improved the administrator overview with quick actions, route links, and actionable prerequisite diagnostics.
* Clarified WordPress Core ownership of registration, route fallback, and mail transport in the administrator UI.
* Improved notification, withdrawal, and audit management feedback without expanding the approved mail or account-state contracts.

= 0.7.16 =
* Refined Members-only typography, spacing, and narrow-screen density.

= 0.7.15 =
* Clarified branded shell and account-link hierarchy across authentication screens.

= 0.7.14 =
* Replaced password visibility text controls with accessible eye icons while keeping no-JavaScript forms usable.

= 0.7.13 =
* Clarified the generic WordPress Core password-reset request guidance and kept account-existence responses generic.
* Clarified that a newly registered user signs in with the email address used during registration and is not signed in automatically.

= 0.7.12 =
* Clarified the approved manual sign-in flow after registration.

= 0.7.11 =
* Clarified withdrawal review/finalization states and notification default fallback guidance.

= 0.7.10 =
* Added capability- and nonce-protected Settings API fields for the four approved account-notice subjects and bodies.
* Added event-specific placeholder allowlists, plain-text validation, and gettext fallback for empty or invalid stored values.
* Kept wp_mail(), sender identity, SMTP/provider configuration, Core reset mail, WooCommerce mail, and LMS mail with their existing owners.

= 0.7.9 =
* Added route-scoped typography tokens and verified desktop, mobile, keyboard-focus, and homepage isolation behavior.

= 0.7.8 =
* Added reason-required withdrawal restoration and explicit finalization while preserving Core user IDs and external domain rows.
* Kept all previous sessions revoked after restoration and made repeated review actions idempotent.
* Added translated audit event/result labels, event/result/date/user filters, 25-row pages, and read-only notification outcomes.

= 0.7.7 =
* Moved the Members administration screen under Users with overview, documents, withdrawals, and audit sections.
* Added read-only readiness diagnostics and server-rendered document preview/history without rewriting published snapshots.
* Added administrator-only account-state and required-consent columns and filters to the Core Users list.

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
