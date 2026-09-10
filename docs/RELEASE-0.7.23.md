# 0.7.23 authentication screen layout

0.7.23 refines the short authentication routes without changing WordPress Core authentication, user IDs, route ownership, registration policy, or password-reset behavior.

## UI behavior

- Login and password-reset routes use a vertically centered card with a maximum width of 480px.
- The redundant site-name eyebrow is removed from those short auth screens.
- Login links are presented in one same-hierarchy row: `Sign up | Find password | Home` (translated to `회원가입 | 비밀번호 찾기 | 홈` in Korean).
- Registration remains a naturally flowing long form and is not vertically centered.

## Verification

The `AUTH-UX-006` contract is covered by the executable harness. The release candidate must pass the full unit harness, PHP lint, package manifest audit, fixed MAMP lifecycle, and serial candidate MAMP gates. Dynamic run IDs and the final archive SHA-256 are recorded in `docs/evidence/0.7.23.json` outside the installable ZIP.

Production certificate/CDN/proxy, real mailbox delivery, backup restore, and the post-deployment observation window remain operational acceptance gates.
