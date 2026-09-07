# Changelog

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
