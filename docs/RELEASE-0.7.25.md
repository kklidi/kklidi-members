# 0.7.25 withdrawal request feedback

0.7.25 improves the withdrawal request screen without changing WordPress Core identity, authentication, user IDs, account-state transitions, or domain ownership.

## UI behavior

- Withdrawal reauthentication continues to use `wp_check_password` and now connects a failed check to the password field with a visible error and `aria-invalid`.
- The withdrawal password field has the same inline eye control as other Members password fields.
- The request copy states that sign-in is blocked immediately and that deletion-eligible data is processed according to the applicable retention period.
- The copy allows for records that must remain under law or service policy; Members does not promise deletion of every external-domain record.

## Verification

The `AUTH-WITHDRAW-UX-008` contract is covered by the executable harness. The release candidate must pass the full unit harness, PHP lint, package manifest audit, fixed MAMP lifecycle, and serial candidate MAMP gates. Dynamic run IDs and the final archive SHA-256 are recorded in `docs/evidence/0.7.25.json` outside the installable ZIP.

Production certificate/CDN/proxy, real mailbox delivery, backup restore, retention-owner decisions, and the post-deployment observation window remain operational acceptance gates.
