# 0.7.6 release evidence and deployment gates

0.7.6 implements the second runtime slice of `AUTH-UX-003`: account, profile,
consent and password UX, a branded WordPress Core password-reset wrapper, and
plugin-owned link-only account navigation slots.

WordPress Core continues to own users, password hashes, reset keys, sessions and
authentication cookies. The wrapper calls `retrieve_password()`,
`check_password_reset_key()` and `reset_password()` and creates no token, password
store, authentication cookie or PHP session. Reset requests return the same public
completion text for matching and missing identifiers. Token-bearing responses are
private/no-store and no-referrer.

Optional plugins can register a label, local URL and priority through
`kklidi_members_account_navigation_links`. Members validates and renders those links
without calling WooCommerce or LMS APIs or querying their domain data. Each consumer
keeps its own behavior and fallback when Members is unavailable.

## Local release gate

- Unit guards cover the reset Core APIs, generic public response, existing reset
  limiter path, absence of custom authentication state, link-only slot boundary,
  runtime routes, templates and route-scoped assets.
- PHP production and harness files must pass syntax checks.
- The Korean catalog and installable ZIP must include every 0.7.6 runtime string and
  the new controller/template.
- The synthetic WordPress behavior suite and lifecycle gate must be refreshed before
  treating this candidate as a fully revalidated package.

## Remaining gates

The repeated MAMP/browser checks are reserved for the later Luna verification stage.
They must cover the real reset email link, valid/invalid/expired/replayed keys, generic
identifier response, keyboard/no-JavaScript operation, mobile reflow, route isolation,
and Members-off fallback. The 0.7.7 administrator information architecture and 0.7.8
withdrawal/audit operations remain unimplemented.

Production acceptance remains `PARTIAL` until the trusted HTTPS staging manifest,
backup/restore, applicable multi-node checks and observation window are complete.
