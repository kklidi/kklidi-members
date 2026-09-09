# 0.7.5 release evidence and deployment gates

0.7.5 implements the first runtime slice of the approved `AUTH-UX-003` strategy:
the login and registration experience. It keeps WordPress Core as the identity,
password, authentication-cookie, and session-token owner while adding a server-rendered
Members shell, safe same-request form recovery, field-level validation links, versioned
consent presentation, action links, and a route-scoped password visibility enhancement.

The release also adds a read-only preflight for the future `/members/` clean-route family.
Existing query routes remain the active fallback; this release does not claim clean-route
ownership or automatically rewrite existing site pages.

Account home, Core reset wrapper, plugin-owned navigation slots, administrator information
architecture, withdrawal operations, browser acceptance, and staging deployment remain
separate subsequent gates. WooCommerce, LMS, KBoard, custom identity, email verification,
social login, 2FA, editable mail templates, SMTP settings, retry queues, and PHP-session
authentication remain outside this release.

## Local release gate

- The 25 unit guards must pass, including route-scoped asset, translation, safe recovery,
  and clean-route preflight assertions.
- The installable ZIP must be rebuilt from the explicit production allowlist and its Korean
  catalog must contain every runtime gettext string.
- The synthetic WordPress suite must pass all MVP contracts, the UI strategy guard, the
  notification regression, optional-dependency behavior, and performance checks.
- The MAMP lifecycle gate must cover a 0.7.4-to-0.7.5 update, same-version reinstall,
  deactivation fallback, reactivation, and protected WordPress/Woo/LMS domain fingerprints.

## Production acceptance

Production acceptance remains `PARTIAL` until a trusted HTTPS staging manifest includes
named owners, the 0.7.5 artifact hash, a separate backup restore test, applicable
proxy/multi-node checks, and the minimum observation window. The installable package is
`dist/kklidi-members-0.7.5.zip`.
