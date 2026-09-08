# Security · 상태 전이와 Threat Model

이 문서는 인증 보안과 탈퇴 상태 전이의 기준이다. 개인정보 field/table 소유권은 ARCHITECTURE, 기능 도입 시점은 PRODUCT, 검증 절차는 HARNESS_PLAN을 따른다. 수치 기본값은 운영 제안이며 법적 보존 기준이 아니다.

## 1. 신뢰 경계와 Core Auth

브라우저 입력·redirect·form hidden field·provider 응답·이메일 주소·기존 meta를 신뢰하지 않는다. 서버의 현재 WP 사용자, 검증한 Core 인증 결과, capability, 목적별 일회성 검증만 사용한다. 로그인 cookie는 WordPress가 발급한다. PHP session, 자체 remember-me cookie, JWT 사용자 세션, 별도 암호 hashing은 도입하지 않는다.

정상 password 로그인은 `wp_signon()`을 통해 Core 인증 chain을 통과한다. device-limit 같은 authenticate hook의 거부를 덮어쓰지 않는다. WP signon은 cookie를 발급하는 단계까지 포함하므로 미래 2FA에서는 이를 먼저 호출해 놓고 challenge를 뒤에 붙이지 않는다. [WordPress wp_signon](https://developer.wordpress.org/reference/functions/wp_signon/).

전역 최소 guard는 로그인 시 계정 상태를 검사하고, 이미 로그인된 disabled/withdrawal_pending/registration_pending 계정의 다음 요청에서도 인증을 거부한다. 탈퇴 처리 시 기존 WP session tokens와 application passwords도 철회한다. 사용자 role에 관리자 capability를 임의 추가/삭제하지 않는다. Core current user 계약을 교체하지 않고 Core 인증·사용자 검증 hook에 정책을 적용한다.

이 설계는 multisite를 아직 지원 대상으로 확정하지 않았다. network super admin, blog별 role, shared users와 custom table scope를 single-site와 같은 것으로 취급하지 않는다.

## 2. 로그인·가입·프로필·비밀번호

- 로그인은 기존 username 또는 email을 받는다. credential 실패는 계정 존재·disabled 여부를 공개하지 않는 공통 메시지를 사용한다. 존재하지 않는 계정도 비교 가능한 password 검증 비용을 가져 timing 차이를 줄인다. 자격증명·비밀번호를 trim/sanitize_text_field로 바꾸지 않는다.
- 가입 입력은 이메일, 비밀번호/확인, 이름, 표시명, 선택 전화, 승인된 필수 동의에 한정한다. role/capability/user_id/account_state/email_verified arbitrary meta는 거부한다. 신규 역할은 검토된 low-privilege subscriber, 요청 parameter로 변경 불가다.
- 비밀번호는 긴 passphrase·password manager·붙여넣기를 허용한다. 제안 기본은 신규/변경 12자 이상, 합리적인 입력 상한(예: UTF-8 1,024 bytes); 길이 제한은 UI와 서버가 같은 규칙으로 검사한다. 기존 짧은 비밀번호의 로그인 자체를 migration 중 막지 않는다. 해시 방식·salt는 Core에 맡긴다.
- 가입 동시성/부분 실패는 ARCHITECTURE의 lock·pending·idempotency로 관리한다. 동의 영속화 없이 가입 성공/자동 로그인이라고 응답하지 않는다. 공개 가입의 단일 운영 스위치는 Core `users_can_register`이며 0이면 가입 폼과 처리를 닫는다. 값이 1이어도 서비스 약관·개인정보 처리방침의 현재 문서가 모두 준비되지 않으면 fail-closed한다. Members 전용 가입 활성화 옵션은 두지 않는다.
- self profile은 `get_current_user_id()`만 수정한다. first_name/last_name/display_name/phone와 선택 description을 allowlist로 다루며 저장은 WP API, 출력은 문맥별 escape다. 닉네임을 sanitize_user로 파괴하지 않는다.
- password 변경·탈퇴·향후 이메일 변경/소셜 link·unlink는 최근 5분 이내 재인증을 제안한다. 2FA가 활성인 계정은 2FA도 요구한다. 재인증 증명은 목적·사용자·브라우저·시간에 묶고 임의 user_id를 받지 않는다.
- 1.0 이메일은 표시 전용이다. 미래 변경은 새 주소 소유 증명 전 user_email을 교체하지 않고, 기존 주소로 변경 안내한다. old user_login은 보존한다.
- reset은 Core 발급·만료·검증·변경 API를 사용한다. 기존 요청 링크와 새 요청 링크의 경합, 사용 후 재사용 거부, 잘못된 key, expiry를 검사한다. 성공 후 기본은 로그인 화면으로 이동하고 재로그인하며 자동 로그인하지 않는다. [check_password_reset_key](https://developer.wordpress.org/reference/functions/check_password_reset_key/), [reset_password](https://developer.wordpress.org/reference/functions/reset_password/).
- 분실 요청에 이메일 존재 여부를 노출하지 않는다. 유효/무효 이메일 모두 같은 공개 응답을 사용하고, 등록 화면에서도 직접 “이 주소의 계정이 존재” API를 제공하지 않는다. 로그인/복구 안내로 연결한다. WP 기본 REST user/author 공개 등 사이트 전체 enumeration은 별도 노출이므로 Members만으로 완전히 제거했다고 주장하지 않는다.

## 3. CSRF·Cookie·Redirect

로그인한 사용자의 mutation은 POST + action별 WP nonce + 인증 + 자기 리소스/capability 검사다. nonce를 권한이나 one-time token으로 간주하지 않는다. anonymous WP nonce는 기본적으로 모든 guest가 user 0을 공유하므로 login/register/reset request에서 그것만으로 CSRF 방어를 끝내지 않는다. [WordPress nonces](https://developer.wordpress.org/apis/security/nonces/).

Guest account route에서만 무작위 browser nonce cookie를 생성하고, action·expiry·해당 cookie에 binding한 HMAC form token을 검증한다. cookie는 로그인 권한을 주지 않는 CSRF용 단기 값이다. TLS 배포에서는 Secure/HttpOnly/SameSite=Lax, path/domain 고정과 가능하면 host-only prefix를 적용한다. Origin/Referer를 가능한 경우 엄격히 비교하고, cross-site 값은 거부한다. 헤더가 없는 요청도 browser-bound token은 반드시 필요하다. PHP session storage는 쓰지 않는다. rate limiting은 CSRF와 별개다.

WordPress auth cookie의 transport/domain/path를 약화시키지 않는다. 계정 화면·callback·reset 페이지에는 no-store와 cache bypass, token-bearing URL에는 no-referrer 및 불필요한 분석/외부 자산 제거를 적용한다. 로그에는 token이 실린 query string을 남기지 않으며 proxy/access log의 redaction도 배포 checklist에 포함한다.

redirect는 명시한 local 목적지 → account/home fallback 순서다. browser/POST/Referer에서 온 URL, double encoding, `//host`, userinfo, CRLF, 역슬래시, 같은 host의 다른 port, 허용되지 않은 scheme, auth loop를 검증한다. 최종 `wp_safe_redirect()` 이후 실행을 끝낸다. 이 함수는 host 검증을 도우므로 제품의 더 좁은 redirect 정책과 함께 사용한다. [wp_safe_redirect](https://developer.wordpress.org/reference/functions/wp_safe_redirect/).

## 4. 이메일 인증 — MVP_OPTIONAL

가입 → WP user 생성/동의 기록 → `pending` → token 발급 → 메일 → 소유 증명 확인 → `verified`. 이 흐름은 비밀번호 reset과 별개의 purpose다.

| 항목 | 설계 |
| --- | --- |
| token | CSPRNG 32-byte 이상 랜덤 bearer. selector+token link; DB에는 token hash만 저장, 비교는 timing-safe |
| binding | purpose, WP user ID, 정규화 target email digest, token version에 binding |
| TTL | 기본 30분 제안. 만료는 매 요청 검사, cleanup 시각에 의존하지 않음 |
| one-time | 조건부 원자 consume; 동시 요청 2개 중 하나만 성공. user email/state 변경도 일관성 있게 finalize |
| 링크 GET | 메일 보안 scanner가 링크를 자동 방문할 수 있으므로 GET은 확인 화면, 명시적 POST에서 consume. 확인 화면에도 CSRF binding 적용 |
| resend | 최소 60초 간격, 대상당 시간당 5회/일 10회 제안. 새 발급 성공 시 이전 challenge revoke, rate count는 초기화하지 않음 |
| mail failure | verified로 바꾸지 않음. 재발급 가능 상태 유지; 재시도와 외부 송신 idempotency 검증 |
| 재사용·대입 | consumed/revoked/expired 모두 공통 실패. 잘못된 token 반복도 limiter 대상 |
| verified state | 검증 email digest + UTC 시각. 이메일이 바뀌면 기존 verified 상태 무효화 |
| email change | 기존 user_email 보존 → 새 주소로 challenge → 재인증·충돌 재검사 → 새 이메일+verified binding finalize → 이전 challenge revoke/기존 주소 알림 |
| 권한 | 이메일 검증이 자동 administrator/student enrollment 부여가 되지 않음 |
| 기존 회원 | legacy_unknown 유지. 구매/학습을 일괄 차단하지 않음. D05에서 단계적 정책 결정 |

이메일 필수 인증으로 결정되면 신규 pending 계정의 full login을 막고 Core/Woo/다른 신규 가입 경로도 동일 정책을 거쳐야 한다. 이 adapter 범위를 완료하지 못하면 이메일 필수 기능을 출시하지 않는다. 성공 token 소비가 인증 cookie 발급이나 다른 계정 로그인으로 이어지지 않게 한다.

## 5. Verification OTP와 TOTP 2FA — 서로 다른 FUTURE 모듈

Verification OTP는 특정 이메일/SMS 연락처의 일회성 소유 확인이다. 로그인 추가 요소로 자동 취급하지 않는다. CSPRNG 코드, 짧은 TTL(5분 제안), challenge당 최대 5회, resend 시 이전 코드 revoke, user/목적/연락처 binding을 사용한다. 6자리 코드 단순 hash는 offline 전수대입에 약하므로 서버 비밀 pepper와 HMAC을 사용한다. SMS 전화는 입력 검증을 거쳐도 실명·본인인증 완료로 해석하지 않는다.

TOTP 로그인은 password 검증(Core authenticate chain) → 제한된 challenge → TOTP 검증 → 최종 Core cookie/current-user/login event 순서다. password 1단계 성공만으로 wp_signon 성공 cookie나 logged-in current user를 만들지 않는다. challenge는 CSPRNG opaque handle, 서버 hash 저장, user/purpose/browser binding, TTL 5분, 최대 5회와 원자 consume로 관리한다. 브라우저 handle은 인증 cookie가 아니며 PHP session에 저장하지 않는다.

TOTP seed는 검증에 필요하므로 hash만 저장할 수 없다. DB 밖 관리 key로 AEAD 암호화하고 key rotation/백업/복원 실패 정책을 설계한다. setup 직후 유효 code 확인 전 enabled로 만들지 않는다. 허용 clock window와 last-used time-step CAS로 같은 code replay를 막는다. primary password와 TOTP 실패 횟수는 별도다.

2FA를 제공하는 버전에는 **해시 저장한 one-time recovery codes 또는 동등하게 안전한 회복 절차가 release 필수**다. 1.0에 2FA가 없으므로 recovery도 FUTURE다. trusted device는 더 나중이며 자체 장기 인증 cookie를 만들지 않는다.

wp-login, Members, Woo login, social login, XML-RPC, REST/application password, password reset 이후, device-limit 경로에서 2FA 우회가 없어야 한다. TOTP와 호환되지 않는 비대화형 인증 경로는 명시적 운영 정책(차단/제한된 별도 credential)과 harness 없이 그대로 허용하지 않는다. 관리자 복구를 이메일 링크 하나로 완료시키지 않는다. 1.0은 2FA 보호를 제공한다고 표시하지 않는다.

## 6. Social — 문서상 provider abstraction만 예약

`SocialProviderInterface`의 논리 계약은 provider ID·고정 issuer, authorization request 생성(state/nonce/PKCE challenge), code 교환, 검증된 identity 반환(issuer/subject/email/email_verified), capability 표시(revoke/PKCE/OIDC 지원), revoke 처리다. provider별 SDK나 PHP interface 파일은 1.0에 만들지 않는다. 첫 후보는 Google이지만 도입 확정이 아니다. Kakao/Naver/Apple은 검증된 provider 정책과 필요가 생긴 후 추가한다.

- Authorization Code flow, 가능하고 지원되는 provider에 PKCE S256; state는 목적/login/link·browser·return target·TTL에 binding하고 원자 일회 소비한다. OIDC는 별도 nonce, signature/JWKS, issuer, audience, expiry를 검증한다. OAuth만 제공하는 provider에 OIDC 필드를 있다고 가정하지 않는다.
- callback URI는 배포 설정의 정확한 allowlist. 클라이언트가 provider endpoint/issuer/redirect URI를 정하지 못한다. provider mix-up 및 SSRF를 막는다. provider discovery가 필요하면 신뢰한 issuer와 endpoint만 허용한다.
- 연결 key는 provider+issuer+subject다. 이메일이 같아도 자동 linking하지 않는다. verified email은 해당 provider 주장일 뿐 기존 WP 계정 소유 증명을 대신하지 않는다.
- 기존 이메일 충돌 시 계정 생성과 cookie 발급을 중단하고 기존 계정 로그인/복구 후 명시적 link로 유도한다. 로그인한 계정도 최근 재인증과 별도 link intent가 필요하다. provider session만으로 기존 회원을 차지할 수 없어야 한다.
- unverified/missing email이면 검증된 이메일과 필수 동의 완료 전 완성 계정 생성/로그인 금지. 제공된 이름/role는 권한이 아니다. social 신규 회원도 Registration/Lifecycle 정책을 거친다.
- unlink는 최근 재인증, 소유권 검사, 마지막 로그인 수단 제거 방지. provider revoke 실패는 로컬 연결을 먼저 사용 불가로 하고 제한된 재시도/관리 상태로 남긴다.
- Social에서 Core password verification을 가장하지 않는다. 검증된 외부 identity→WP user 매핑 이후 Core cookie 발급을 사용하되 disabled/2FA/device-limit 등 동일 최종 정책을 통과시키는 adapter가 있어야 한다. password가 없다고 해당 정책들을 건너뛰지 않는다.
- 토큰/이메일 원문 없는 login/link/unlink/revoke event만 감사한다. 동시 callback·link unique 충돌 시 user 생성과 연결 결과가 하나로 수렴해야 한다.

이는 제품 설계 선택이다. code flow·PKCE·정확한 redirect·mix-up 방어 등은 [OAuth Security BCP RFC 9700](https://www.rfc-editor.org/info/rfc9700/)과 대조했다. provider 실제 구현 시 각 provider 공식 문서를 다시 확인해야 한다.

## 7. 탈퇴 — ID 보존과 개인정보 처리는 별개

1. 본인 로그인 + POST nonce + 최근 재인증 → 영향 안내(구매/강의/증명서/게시물) → 고유 request ID로 요청.
2. `active → withdrawal_pending`을 원자 전환하고 신규 로그인 차단, 기존 Core session token·application password 철회. 새 protected request에서도 차단 상태 확인. 중복 요청은 같은 처리 결과.
3. 관리자 queue는 제한된 capability로 조회한다. Woo/LMS/PMS/KBoard 각 소유자가 개인정보·거래/학습 증거·법적 보존을 평가하고, 재시도 가능한 단계별 완료 상태를 기록한다.
4. `withdrawal_pending → disabled`로 확정한다. 1.0의 D02 정책은 요청·차단·수동 처리 queue까지이며 Members가 계정 연락처·이름·게시물이나 외부 도메인을 자동 익명화·삭제하지 않는다. 사이트의 WordPress privacy 절차와 각 도메인 owner가 실제 처리 범위를 판정한다.

주문/정산/인증서 snapshot/질문 본문에는 users/usermeta 밖 개인정보가 있을 수 있다. user row만 익명화했다고 전체 삭제 완료로 표시하지 않는다. WordPress privacy export/erasure와 domain API로 협업한다. 완료와 보류, 법적 보존 중, 작업 실패를 구별하고 회원에게 실제 처리 범위를 알린다.

`wp_delete_user()` 호출이나 다른 회원에게 작성물 일괄 재할당을 기본 탈퇴로 사용하지 않는다. 1.0은 tombstone user ID를 남겨 order/enrollment/progress/certificate/question/activity 참조를 유지하고 self-service 복구를 제공하지 않는다. 법정·계약 보존기간은 Members가 발명하지 않으며 사이트 privacy owner가 관할 기준을 기록하기 전 자동 삭제를 실행하지 않는다. 관리자 계정·정산 담당자·유일 관리자 탈퇴는 별도 수동 심사로 보낸다.

Members 비활성 시 meta guard도 없어질 수 있다. 차단 계정 존재 후 제품을 비활성화하려면 동등 lifecycle enforcement를 먼저 이관해야 한다. “LMS fatal 없음”은 탈퇴/2FA 정책 유지의 대체 검증이 아니다. 긴 in-flight 요청·비동기 작업은 실행 직전 domain 권한과 계정 상태를 다시 검사하도록 통합 계약에 명시한다.

## 8. Rate limit와 장애 정책

제안 초기 정책: 로그인 identifier당 15분 10회 실패, network당 15분 50회; reset 대상당 시간당 5회, network당 시간당 20회; 가입 network당 시간당 10회. 무작위 사용자명/IP rotation을 고려해 목적+정규화 identifier digest+network+전체 서비스 budget을 조합한다. 공유 NAT에서 부당 차단을 계측하고 조정하며 account 영구 lockout은 하지 않는다. 응답은 429/Retry-After, 긴 서버 sleep으로 worker를 점유하지 않는다.

신뢰된 proxy 목록 외 X-Forwarded-For를 무시한다. IPv4/IPv6·IPv4-mapped 주소 정규화를 통일한다. cache가 없거나 재시작해도 counter가 조용히 무한 리셋되지 않게 ARCHITECTURE의 원자 저장 adapter를 사용한다. limiter 저장 실패 시 해당 인증 mutation은 일시 실패로 처리하고 read-only 일반 화면은 계속 제공한다. audit 장애는 일반 로그인 가용성과 분리해 최소 운영 경보를 내되, 동의·탈퇴 상태 저장 실패는 성공 처리하지 않는다.

## 9. Threat → 방어 → Harness

| Threat | 위험 | 핵심 방어 | 검증 ID |
| --- | --- | --- | --- |
| brute force | 계정 비밀번호 추측 | 복합 limiter, 비용 통일, 강한 새 password | AUTH-LOGIN-002, AUTH-RATE-LIMIT-001 |
| credential stuffing | 유출 credential 반복 사용 | 분산 속도 제한·감사; 2FA 도입 시 별도 gate | AUTH-RATE-LIMIT-001, AUTH-2FA-001 |
| user enumeration | 회원 여부 노출 | 공통 응답, timing/REST 노출 범위 점검 | AUTH-ENUM-001 |
| CSRF / login CSRF | 타계정 로그인·정보/탈퇴 변경 | WP nonce+권한, guest browser binding, POST | AUTH-CSRF-001, AUTH-WITHDRAW-001 |
| open redirect | phishing·credential 전달 | local URL 정책, 안전한 fallback | AUTH-REDIRECT-001 |
| session fixation | 인증 전 handle로 로그인 가로채기 | Core session token, guest/challenge와 인증 분리 | AUTH-COOKIE-001, AUTH-2FA-001 |
| auth cookie misuse | 탈취·캐시 혼입·로그아웃 후 사용 | TLS, Core flags, session revoke, no-store | AUTH-COOKIE-001, AUTH-LOGOUT-001 |
| password reset takeover | key 탈취·재사용·잘못된 계정 변경 | Core key 검증, no-referrer, consume·재로그인 | AUTH-RESET-001 |
| email token replay | 검증 상태 위조 | 목적/email binding·TTL·원자 consume | AUTH-EMAIL-VERIFY-001 |
| OAuth state/nonce·mix-up | 다른 브라우저/provider 응답 주입 | state/nonce/PKCE·issuer/aud·정확한 callback | AUTH-SOCIAL-001 |
| social linking takeover | 동일 이메일로 계정 점유 | 기존 계정 재인증·explicit link·unique subject | AUTH-SOCIAL-LINK-001 |
| email collision | 중복 회원·잘못된 병합 | 기존 login 요구, serialized create, 재검증 | AUTH-REGISTER-002, AUTH-SOCIAL-LINK-001 |
| 2FA bypass | 1차 인증만으로 full session | cookie 발급 전 challenge, 모든 입구 정책 | AUTH-2FA-001, AUTH-COOKIE-001 |
| privilege escalation | 가입 role·capability 주입 | 서버 고정 low privilege role | AUTH-REGISTER-002, AUTH-PRIVILEGE-001 |
| IDOR | 남의 profile·consent·탈퇴 조작 | current user scope, 관리자 capability | AUTH-PROFILE-001, AUTH-PRIVILEGE-001 |
| profile field abuse / stored XSS | 상태/권한 변경·script 저장 | strict allowlist, validation, contextual escape | AUTH-PROFILE-001 |
| withdrawal abuse | 세션 소지자가 즉시 계정/학습 삭제 | 재인증·idempotency·분리 처리·ID 유지 | AUTH-WITHDRAW-001 |
| rate limit bypass / DoS | 동시 증가 손실·proxy spoof·락 공격 | atomic counter, trusted proxy, bounded storage/TTL | AUTH-RATE-LIMIT-001, AUTH-PERF-003 |
| consent forgery / partial signup | 미동의 가입·시각 조작 | 서버 version, immutable 사건, pending 복구 | AUTH-CONSENT-001, AUTH-REGISTER-001 |
| SQL injection / output leakage | DB 손상·PII 노출 | prepared queries/WP API, 최소 payload·escape | AUTH-PROFILE-001, AUTH-AUDIT-001 |

legacy 코드는 reference일 뿐 보안 보증이 아니다. Cosmosfarm delete 조건의 OR/nonce 검증 구조와 일반 session start, SMS OTP 저장·생성 방식은 새 제품으로 이식하지 않는다. 실제 공격 요청은 수행하지 않았다.
