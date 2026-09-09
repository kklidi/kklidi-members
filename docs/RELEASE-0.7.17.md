# 0.7.17 administrator UX and harness evidence

0.7.17 improves the administrator-facing account workflow without changing
WordPress Core authentication, user IDs, route ownership, notification
transport, or account-state transitions.

## Implemented contract

- `AUTH-ADMIN-UX-001` adds actionable overview diagnostics, quick links, and
  canonical Members route links.
- The administrator screen explains that WordPress Core owns public
  registration and mail transport.
- Notification settings keep the approved four plain-text events, gettext
  fallback, read-only sender policy, and no test-send/HTML/queue behavior.
- Withdrawal queue rows link to the existing WordPress user editor and show a
  bounded pending count.
- Audit filters expose a clear-filters action.
- No WordPress pages or site menus are created or mutated automatically.

## Verification

- Python harness guards: `AUTH-ADMIN-UX-001` plus all prior contracts pass.
- PHP lint, translation catalog, release allowlist and archive checks are
  required before packaging.
- MAMP sink verification remains the executable mail-delivery check. External
  mailbox delivery is an environment gate and is not claimed by this release.

## Scope boundary

This release does not add administrator recipient notices, registration
approval, CAPTCHA, HTML mail, sender overrides, SMTP/provider settings,
shortcodes, or automatic page creation. Each requires a separate behavior
contract and security review.
