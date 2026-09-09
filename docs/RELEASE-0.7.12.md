# 0.7.12 development evidence

0.7.12 is a bounded registration and login UX clarification. The registration
screen states that WordPress Core owns authentication, that the user can sign
in with the accepted email or username, and that registration does not issue an
automatic login. The post-registration login notice repeats the same supported
identifier policy.

No cookie, password, user-ID, account-state, consent, notification, or rate
limit behavior changed. Email verification, automatic login, social login,
2FA, SMS, and provider-owned identity remain outside this contract.

## Verification

- Python contract guards: 30 passed.
- PHP 8.3 syntax: 32 production PHP files passed.
- Release package: built successfully with the Korean catalog check.

The MAMP lifecycle and full Sol High review are scheduled after the next bounded
reset-flow UX stage.
