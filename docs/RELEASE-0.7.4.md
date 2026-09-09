# 0.7.4 release evidence and deployment gates

0.7.4 preserves the verified 0.7.3 Core-auth and account-notification runtime. It
adds `AUTH-UX-003`, an executable strategy contract for the next frontend and
administrator stages, and corrects the UI source of truth to match the implemented
private opaque Core `user_login` strategy. Email and existing username login remain
supported through WordPress Core authentication.

The strategy approves a standalone branded shell, collision-gated `/members/` clean
routes with existing query-route fallback, safe form-value recovery, duplicate display
names, WordPress Core reset wrappers, and plugin-owned link-only navigation slots. It
also approves a Users-area administrator information architecture, read-only health
diagnostics, immutable consent history, reasoned pending-withdrawal recovery or final
disablement, bounded audit views, and read-only notification results.

These 0.7.5–0.7.9 runtime stages are explicitly not implemented by 0.7.4. Email
verification, social login, 2FA, editable mail templates, SMTP settings, retry queues,
WooCommerce/LMS domain data, custom identity, and PHP-session authentication remain
outside this release.

## Local release gate

- The `AUTH-UX-003` JSON manifest and unit guard must agree with `UI_UX.md` and the
  product decisions.
- All existing synthetic account, security, notification, optional-dependency, and
  performance contracts must continue to pass without new frontend hooks or assets.
- The package lifecycle must cover fresh installation, 0.7.3-to-0.7.4 update,
  reinstall, deactivation fallback, and reactivation while preserving WordPress user
  IDs and integration-domain fingerprints.
- The 0.7.2 Chrome responsive UI evidence can be reused because 0.7.4 changes no
  frontend HTML, CSS, or JavaScript. Runtime and package gates are refreshed.

## Production acceptance

Production acceptance remains `PARTIAL` until the real trusted HTTPS staging manifest,
owners, backup hash, separate restore test, applicable proxy/multi-node checks, and
the minimum observation window are complete. The installable package is
`dist/kklidi-members-0.7.4.zip`.
