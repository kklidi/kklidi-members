# 0.7.13 development evidence

0.7.13 is a bounded password-reset UX clarification. The request screen states
that users may enter a username or email and that WordPress Core sends a reset
link only when an account matches. This wording preserves the existing generic
response boundary and does not disclose account existence.

Reset keys, Core password APIs, rate limits, private/no-store headers, token
consumption, session behavior, and the Members optional-dependency boundary are
unchanged. Email verification, TOTP/2FA, SMS, social login, and custom reset
tokens remain outside this release.

## Verification

- Python contract guards: 30 passed.
- PHP 8.3 syntax: 32 production PHP files passed.
- Release package: built successfully with the Korean catalog check.
- Fixed MAMP lifecycle evidence for the `0.7.12→0.7.13` update path is exported
  in the credential-free sidecar `docs/evidence/0.7.13.json` after the final ZIP
  is frozen.
