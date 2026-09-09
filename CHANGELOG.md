# Changelog

## 0.7.10 — 2026-09-09

- Added a Users-area notification section backed by the WordPress Settings API and
  one versioned, non-autoload option.
- Limited edits to the subject and plain-text body of the four existing account
  notices, with event-specific placeholders and gettext fallback.
- Kept sender identity, SMTP/provider configuration, Core reset mail, WooCommerce
  mail, LMS mail, delivery queues, and test sending outside Members.

## 0.7.9 — 2026-09-09

- Added the route-scoped `AUTH-UX-004` typography tokens and bounded title, body,
  control, metadata, and consent-document scales.
- Verified desktop and 360px layouts, visible keyboard focus, server-rendered forms,
  and homepage asset isolation in the fixed MAMP sandbox.

## 0.7.8 — 2026-09-09

- Added capability- and nonce-protected withdrawal restoration with a required
  reason, and retained explicit pending-to-disabled finalization.
- Kept all Core sessions revoked after either review decision, preserved WordPress
  user IDs and external domain rows, and made repeated review actions idempotent.
- Added translated audit event/result/reason labels, event/result/date/user filters,
  bounded 25-row pagination, retention status, and read-only notification outcomes.

## 0.7.7 — 2026-09-09

- Moved the administrator surface to the WordPress Users area and split it into
  overview, documents, withdrawals, and audit sections with a safe legacy redirect.
- Added read-only registration, document, route, URL ownership, table, and cleanup
  diagnostics without loading WooCommerce or LMS domains.
- Added immutable document preview/history and administrator-only Core Users columns
  and filters for Members account state and current required consent.

## 0.7.6 — 2026-09-09

- Implemented the approved account, profile, consent, and password UX slice with
  linked validation errors, clear success/error states, versioned document details,
  and route-scoped password visibility controls.
- Added a branded password reset request and completion wrapper using only WordPress
  Core reset-key APIs, generic identifier responses, and no-store/no-referrer headers.
- Added a validated local link-only account navigation filter for optional plugins;
  Members does not call WooCommerce or LMS APIs or read their domain data.

## 0.7.5 — 2026-09-09

- Implemented the approved login and registration UX contract with a standalone
  server-rendered shell, safe same-request value recovery, field-level errors,
  accessible error summaries, action links, and versioned consent details.
- Added a small route-scoped password visibility enhancement that leaves the core
  submit and validation flow usable without JavaScript.
- Added a clean-route collision preflight while keeping existing query routes as the
  fallback, and expanded the Korean catalog for the new user-facing states.

## 0.7.4 — 2026-09-09

- Added the executable `AUTH-UX-003` strategy contract for the approved frontend and
  administrator information architecture without implementing future runtime stages.
- Corrected the UI source of truth to match the existing private opaque Core
  `user_login` strategy while preserving email and legacy-username login.
- Decided the standalone branded shell, collision-gated `/members/` route family,
  safe form recovery, duplicate display names, Core reset wrapper boundary, and
  plugin-owned account navigation slots.
- Decided the Users-area administrator structure, diagnostics, immutable consent
  history, bounded audit views, and reasoned withdrawal recovery/finalization.

## 0.7.3 — 2026-09-09

- Added route-scoped account notices for completed registration, self-service password
  changes, withdrawal requests, and administrator-finalized withdrawals.
- Used the current WordPress user email, explicit plain-text presets, user locale, and
  the existing audit unique key for one logical dispatch claim per event.
- Verified the four presets, rejected/replayed requests, data minimization, arbitrary
  database prefixes, and Members-off behavior in disposable WordPress installations.
- Completed the P0-4 injected `wp_mail()` failure gate across all four account events
  and two database prefixes: committed state and session revocation survive, failed
  attempts are audited as `failure/wp_mail_failed`, and no delivery or retry is recorded.

## 0.7.2 — 2026-09-09

- Clarified that `AUTH-UI-002` is implemented and verified in MAMP and Chrome.
- Separated historical synthetic/MAMP snapshots from the current release verdict in
  the Phase 0 harness source of truth.
- Added an executable documentation consistency guard and advanced the lifecycle gate
  to the 0.7.1-to-0.7.2 update path.
- Made lifecycle directory swaps same-volume atomic and added a write-access probe so
  a denied MAMP mutation cannot fall back to a partial copy.
- Confined OpenSSL random-state files to each disposable TLS certificate directory.
- Kept the 0.7.1 Core-auth runtime behavior unchanged.

## 0.7.1 — 2026-09-09

- Added a repeatable fixed-MAMP LMS runner that verifies WordPress user-ID continuity,
  Woo order reconciliation, learning access, profile delegation, Members-off fallback,
  and exact synthetic cleanup.
- Added a bounded plugin lifecycle runner for fresh installation, 0.7.0-to-0.7.1
  update, same-version reinstall, deactivation fallback, reactivation, protected-domain
  fingerprints and exact source restoration.
- Added harness guards and operating instructions for both release gates.
- Fixed the release allowlist so the Korean PO/MO catalog and source POT are present
  in the installable ZIP, with a unit guard preventing another untranslated package.
- Kept aggregate evidence outside the installable archive so lifecycle evidence can
  bind the final ZIP hash without a self-referential rebuild.
- Bound deployment manifests to Members 0.7.1 and the executed WordPress 7.1/PHP 8.3
  support matrix, with WooCommerce 11.1.0 or an explicit disabled state.
- Scoped lifecycle domain fingerprints to WordPress content and Woo/LMS/KBoard-owned
  tables so unrelated background scheduler/session writes cannot create a false failure.

## 0.7.0 — 2026-09-08

- Added an isolated MAMP TLS reverse-proxy harness with a per-run CA, normal hostname
  verification, HSTS, `__Host-` guest-cookie and Core Secure-cookie checks.
- Moved limiter counters onto direct shared-MySQL reads/writes under `GET_LOCK`, so an
  unavailable WordPress object-cache adapter cannot bypass limits; storage failure
  rejects the authentication mutation.
- Added bounded legacy-consent rollback verification and a credential-free deployment
  manifest validator for owners, backup/restore evidence and the observation window.
- Re-ran MAMP signup/reset races, Woo checkout/cart/order/device-limit, and enumeration
  timing after the storage change.

## 0.6.0 — 2026-09-08

- Made WordPress `users_can_register` the only public-registration switch; required
  service/privacy documents still fail closed.
- Fixed the 1.0 signup policy at optional phone, no email-verification module, and no
  automatic login. Fixed withdrawal at immediate access revocation plus manual owner
  review, with no automatic user/domain deletion.
- Assigned legacy page/menu ownership without adding a Members restriction engine.
- Added fixed-sandbox concurrent registration/Core reset, enumeration timing,
  browser JavaScript, proxy/cache capability, and read-only D06 audit evidence.
- Declared the actually executed support baseline: WordPress 7.1, PHP 8.3,
  single-site; WooCommerce 11.1.0 is the tested optional integration.

## 0.5.0 — 2026-09-08

First repository release of the Core-based Members MVP and its behavior harness.

- Login/logout, registration, profile, Core password reset/change, versioned consent,
  withdrawal blocking/administration, audit, rate limiting, and legacy-consent import.
- Scoped frontend/admin styling and WordPress gettext Korean translations.
- LMS classroom profile delegation without accessing enrollment/progress/certificate data.
- Disposable WordPress verification on two database prefixes, including 100 limiter
  calls through eight independent PHP workers per prefix.
- Fixed MAMP fixtures for Woo checkout/cart/order/device-limit and KBoard compatibility.
- Allowlisted installable ZIP builder; test fixtures, caches and credentials are excluded.

This is a development validation release. Production acceptance remains open for
the policy and environment gates listed in `docs/RELEASE-0.5.0.md`.
