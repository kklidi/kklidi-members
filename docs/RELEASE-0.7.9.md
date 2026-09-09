# 0.7.9 development evidence

0.7.9 adds the `AUTH-UX-004` Members typography behavior contract. The frontend stylesheet now uses route-scoped typography tokens for body text, headings, controls, metadata, and consent documents. The title scale is bounded at 28–32px, body and controls remain 16px, metadata is 14px, and consent text is 15px with a 1.7 line height.

## Verified

- `AUTH-UX-004` contract is recorded in `docs/TYPOGRAPHY.md`.
- CSS token and scope guard passed in the synthetic harness.
- Existing 0.7.8 behavior guards remain green.
- Korean translation catalog metadata and the installable package were rebuilt for 0.7.9.

## Remaining gate

Desktop/mobile browser rendering, keyboard navigation, zoom behavior, no-JavaScript behavior, route isolation, and Members-off compatibility remain the 0.7.9 browser release gate. This document does not claim production acceptance or site-wide theme typography changes.
