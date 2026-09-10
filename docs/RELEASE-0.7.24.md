# 0.7.24 registration required-field contract

0.7.24 makes the registration required-field policy visible and consistent without changing WordPress Core identity, authentication, user IDs, registration gates, or consent storage.

## UI behavior

- Email, password, password confirmation, display name, and required consent are rendered as required with a visible server-rendered asterisk.
- First name, last name, and phone continue to use the administrator-selected required, optional, or hidden state.
- The registration form includes a `* Required field` legend and preserves optional hints.
- The administrator registration-fields screen lists fixed required fields as `Required · fixed`; only the approved profile fields remain editable.

## Verification

The `AUTH-REGISTER-UX-007` contract is covered by the executable harness. The release candidate must pass the full unit harness, PHP lint, package manifest audit, fixed MAMP lifecycle, and serial candidate MAMP gates. Dynamic run IDs and the final archive SHA-256 are recorded in `docs/evidence/0.7.24.json` outside the installable ZIP.

Production certificate/CDN/proxy, real mailbox delivery, backup restore, and the post-deployment observation window remain operational acceptance gates.
