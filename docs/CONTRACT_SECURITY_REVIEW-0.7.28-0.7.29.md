# 0.7.28–0.7.29 계약·보안 경계 검토

- 검토일: 2026-09-10
- 대상: `AUTH-IDENTITY-002`, `AUTH-MAIL-SENDER-001`
- 범위: Phase 0 source of truth, 0.7.29 runtime, 실행 가능한 계약 manifest와 단위 guard
- 판정: **AUTH-IDENTITY-002 구현·합성 검증 완료; AUTH-MAIL-SENDER-001 구현·합성 검증 완료**

## AUTH-IDENTITY-002

### 확인된 안전 경계

- 신규 가입 form은 username을 받지 않고 Core `user_email`과 내부 생성 `user_login`을 사용한다.
- 로그인은 `wp_signon()`, reset은 `retrieve_password()`와 Core reset key API를 사용한다.
- 기존 WordPress user ID와 `user_login`을 변경·병합·재발급하지 않는다.
- 기존 username/email 양쪽 호환, generic 실패 응답, account-state/device-limit/authenticate hook과 limiter를 유지한다.
- 표시명은 공개 닉네임이며 인증·권한 식별자로 사용하지 않는다.

### 구현·검증된 경계

0.7.28에서 신규 계정은 `user_nicename`을 내부 `user_login`과 독립된 unique slug로 생성한다. WordPress의 작성자 URL 또는 REST 설정에 공개될 수 있는 값이 내부 로그인 값을 역으로 드러내지 않는다. 기존 계정의 ID/login/nicename은 migration하지 않는다.

### 의도적으로 남은 범위

이메일 소유 확인은 아직 없다. 따라서 이메일 중심 로그인은 로그인 입력 정책이지 verified-email 주장이나 2FA가 아니다. 이메일 변경도 계속 읽기 전용이다.

## AUTH-MAIL-SENDER-001

### 확인된 안전 경계

- 현재 production에는 `wp_mail_from`/`wp_mail_from_name` 전역 filter가 없고 실제 `wp_mail()` 호출은 Members 사용자 알림과 관리자 가입 알림에 한정된다.
- 후속 설정은 기본 꺼짐, Settings API, `manage_kklidi_members`, nonce, non-autoload 단일 option으로 제한했다.
- From header는 Members가 소유한 개별 mail 호출에만 적용하고 Core reset·WooCommerce·LMS·KBoard는 제외했다.
- CR/LF와 invalid email을 거부하고 SMTP/provider credential·HTML·retry queue를 범위 밖으로 유지했다.
- 시험 발송은 현재 관리자 자신의 Core 이메일만 허용하고 15분 3회로 제한했다.

### 배포 환경 gate

`wp_mail()` true는 메일 시스템이 요청을 받아들였다는 뜻이며 inbox 도착을 증명하지 않는다. 사용자 정의 발신 주소를 켜기 전에 운영 도메인의 SPF·DKIM·DMARC와 실제 SMTP/provider 정렬을 별도 확인해야 한다. provider가 From을 강제로 덮어쓸 수도 있으므로 실제 header와 수신 결과는 staging/운영 mailbox에서 판정한다.

합성 검증 실행 `2fb34a1a46b14894989c36e755b2dbd1`은 기본 및 임의 database prefix에서 Settings API 권한·nonce, non-autoload 저장, CR/LF 거부, Members 범위 적용, 실패 주입과 관리자별 rate limit을 PASS했다. 격리 MAMP 실행 `mamp-mail-sender-56dbd5af1df2`는 WordPress runtime의 `wp_mail()` 수락, plain-text header/footer와 account-mail 감사 경계를 PASS했으며 외부 수신함은 의도적으로 호출하지 않았다.

## 결론과 구현 순서

1. 0.7.28에서 신규 `user_nicename` 분리, 이메일 주 label·기존 아이디 보조 안내를 구현했다.
2. 합성 WordPress에서 신규 이메일, 기존 아이디/이메일, 존재·부재 오류, limiter, Members off 경계를 반복 검증한다.
3. 0.7.29에서 Members 전용 sender/footer와 제한된 시험 발송을 구현했다.
4. 기본/비기본 prefix에서 설정 권한·nonce·CRLF·적용 범위·mail 실패·rate limit을 검증하고 실제 mailbox는 배포 gate로 남긴다.
