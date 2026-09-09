# 0.7.10 development evidence

0.7.10 implements `AUTH-NOTIFY-002`. Administrators with
`manage_kklidi_members` can edit the plain-text subject and body of the four
existing account notices under Users > KKLIDI Members > Notifications. The form
uses the WordPress Settings API, its nonce, and one versioned non-autoload option.

Each event has a fixed placeholder allowlist. Unknown placeholders, HTML,
shortcodes, PHP, and over-limit values are rejected without replacing the previous
settings. Empty or structurally invalid stored fields use the existing translated
gettext preset. Audit rows record only the settings event metadata and never the
saved subject or body.

The delivery boundary is unchanged: `AccountMailer` still uses one `wp_mail()`
call after the approved account transition. Members does not add global sender
filters or own SMTP/provider credentials, test sending, queues, webhooks, Core
password-reset mail, WooCommerce mail, or LMS mail.

## Verification

- Python contract guards: 30 passed.
- PHP 8.3 syntax: 32 production PHP files passed.
- Synthetic WordPress run `d28853b554c5497eb50df18d7f24dffe` passed all
  24 MVP contracts and both notification extension contracts under `wp_` and a
  non-default prefix. It also passed Core and Members login cases 12/12 each,
  limiter, performance, device-limit, mail failure, and exact temporary cleanup.

Production certificate/CDN/proxy behavior, distributed application hosts, and
production migration remain deployment-environment gates.
