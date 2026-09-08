# Changelog

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
