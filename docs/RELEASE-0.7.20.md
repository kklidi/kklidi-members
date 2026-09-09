# 0.7.20 administrator registration notice

0.7.20 implements `AUTH-ADMIN-NOTIFY-001` as a bounded opt-in notification after active registration.

## Included behavior

- A separate Settings API checkbox in Notifications is off by default and stored in a versioned non-autoload option.
- The recipient is read from WordPress Core `admin_email` at send time and is displayed read-only in Members.
- After required consent and `registration_pending → active` commit, Members requests one plain-text `wp_mail()` message containing the site name, member display name, member email, and UTC registration time.
- The existing audit table provides request-level deduplication and metadata-only result evidence.
- Invalid recipient and mail failure do not roll back registration, change the success response, or start an automatic retry.

## Verification

The PHP syntax and bounded unit checks pass. The Korean catalog contains the administrator notice strings and compiles with 365 messages. Synthetic run `b83fd4753406440a874f0e50e55d0860` passed 24 MVP and five extension contracts across the default and an arbitrary prefix, including 12 Core and 12 Members login cases. Its paired performance block passed with 4.538 ms median and 0.828 ms p95 overhead, no added queries or memory, and no global assets. Fixed-MAMP lifecycle and the remaining pre-release gates are recorded after they complete.

## Excluded

Administrator approval, pending-account moderation, custom or multiple recipients, editable administrator templates, HTML email, sender/SMTP/provider settings, test sends, retries, delivery logs, and WooCommerce/LMS/KBoard messages remain outside this release.
