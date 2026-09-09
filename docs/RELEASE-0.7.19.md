# 0.7.19 message UX

0.7.19 implements `AUTH-MESSAGE-UX-001` without adding a global message editor or changing mail transport.

## Included behavior

- `Users → KKLIDI Members → Messages` displays 16 approved gettext messages in seven read-only groups.
- Security-sensitive login, reset, registration, CSRF, and rate-limit wording cannot be stored or edited from Members.
- Notifications displays the translated default subject and body for each of the four existing account notices while preserving the existing plain-text override schema.
- A successful self-service password change redirects to the Members login screen with only `password_changed=1`, displays a completion notice, and still requires manual sign-in.
- The message catalog class is loaded only for its administrator section and adds no frontend hooks or assets.

## Verification

The bounded unit guard and PHP syntax checks passed. The Korean gettext catalog compiled with 349 messages. Synthetic run `76b5fbbeec1940548eea447f3af980dd` passed 24 MVP contracts and four extension contracts across the default and an arbitrary database prefix, including 12 Core and 12 Members login cases and exact cleanup. The installable artifact SHA-256 is `011f731d83f4ba513c63fc75c54af02fec9e78b2e4c59dac3bc021d080875e4c`.

## Excluded

Administrator registration email, HTML/WYSIWYG email, sender or SMTP configuration, test sending, delivery logs, retries, and WooCommerce/LMS/KBoard messages remain outside this release.
