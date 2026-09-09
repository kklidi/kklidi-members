# 0.7.7 release evidence and deployment gates

0.7.7 implements the administrator information architecture slice of
`AUTH-UX-003`. The Members page lives under WordPress Users and has overview,
documents, withdrawals and audit sections. The old Tools URL performs a local,
capability-checked redirect.

The overview reads Core registration, required-document readiness, clean-route
collisions, Members URL ownership, the two owned tables and the daily cleanup
schedule. It does not query WooCommerce orders, LMS learning data or KBoard content.

Document preview sanitizes and renders an unpublished draft without writing it.
Published history reads a bounded set of immutable snapshots and never rewrites
past consent rows. The Core Users list adds administrator-only account-state and
current required-consent columns and filters; WordPress Core remains the user registry.

## Local release gate

- Unit guards cover the Users menu, four sections, legacy redirect, diagnostics,
  preview/history, Core Users columns/filters and optional-domain boundaries.
- Production and harness PHP files must pass syntax checks.
- The Korean gettext catalog and installable ZIP must include all 0.7.7 strings.
- The synthetic WordPress behavior suite must preserve the existing 24 MVP contracts.

## Remaining gates

0.7.8 owns reasoned withdrawal recovery/finalization and bounded audit
filter/pagination. 0.7.9 owns MAMP desktop/mobile browser, keyboard, no-JavaScript,
route isolation and Members-off regression.

Production acceptance remains `PARTIAL` until the trusted HTTPS staging manifest,
backup/restore, applicable multi-node checks and observation window are complete.
