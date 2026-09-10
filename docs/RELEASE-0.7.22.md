# 0.7.22 frontend input refinement

0.7.22 refines the existing Members screens without changing authentication, storage, route ownership, or registration policy.

## UI behavior

- Password visibility controls render as eye icons inside the right side of every password input, including withdrawal confirmation.
- JavaScript remains progressive enhancement: password entry and server validation work when JavaScript is unavailable.
- Required fields keep their HTML `required` attribute and display a consistent red asterisk. Optional configurable registration fields keep their existing `Optional` hint.
- Frontend helper text describes the user action rather than internal WordPress authentication implementation details.

## Verification

The existing 37 executable unit/design guards remain required. The 0.7.22 release candidate must pass the two-prefix synthetic behavior harness, final PHP lint, package manifest audit, fixed MAMP lifecycle, and the serial candidate MAMP gates. Dynamic run IDs and the final archive SHA-256 are recorded in `docs/evidence/0.7.22.json` outside the installable ZIP.

Production certificate/CDN/proxy, real mailbox delivery, backup restore, and the post-deployment observation window remain operational acceptance gates.
