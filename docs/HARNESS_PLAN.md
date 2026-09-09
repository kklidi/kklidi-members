# Harness Plan · 구현 이전 행동 계약

이 문서는 검증 기대값·성능 budget·release gate의 기준이다. Phase 0에서는 실제 회원가입·로그인·메일·탈퇴·HTTP 요청을 실행하지 않았다. 후속 실행 상태는 아래 §5에서 명시하며 원래 제품 contract의 범위는 축소하지 않는다.

## 1. 테스트 환경과 판정

reference와 독립된 WP DB/filesystem에 synthetic 사용자 A/B, subscriber/admin, 활성/탈퇴/pending/legacy_unknown, username=email 및 다른 사용자명, 한국어 이름, 전화 누락·충돌, 동의 agree/blank/missing, guest/member 주문, enrollment·progress·certificate·question·activity를 만든다. 실제 회원 이메일·전화·비밀번호 해시·OAuth secret을 복사하지 않는다.

메일은 sink, SMS와 provider는 mock, 결제는 테스트 모드다. test route나 token 생성 도구를 운영 runtime에 넣지 않는다. 기본 prefix와 임의 non-default prefix를 검사한다. 현재 단일 사이트만 대상이며 지원 버전은 D07에서 고정한다. code가 선언한 최소 버전과 테스트 지원 matrix를 일치시킨다.

관찰은 사용자 화면/HTTP status/Location/cookie, 다음 요청의 Core current user/capability, 목적 domain 결과, 최소 DB 상태 전후 차이다. “Cosmosfarm 함수 X가 호출됨” 같은 구현 종속 assertion을 쓰지 않는다. 일회성 토큰과 race는 시계 제어·병렬 request·fault injection이 필요하다. form 유효성은 단순 HTML required뿐 아니라 서버 경로를 검사한다.

| 실행 matrix | 이유 |
| --- | --- |
| Core only + Members off/on | optional dependency와 ID contract |
| 관찰된 legacy off + 잔존 page | B0의 기대하지 않은 정상 가정을 방지 |
| 격리 legacy 활성 + Members route owner별 전환 | B1·중복 hook·redirect·메일 회귀 |
| Members + Woo/WCI + LMS + device-limit | 실제 공통 로그인·수강권 경계 |
| Members off + LMS/Woo | fatal 없음, Core fallback; lifecycle 이전 gate 별도 |
| cache adapter 있음/없음/장애, proxy 있음/없음 | limiter·token 일관성 |

## 2. Behavior contracts

아래 표는 기대 계약이며 실행 결과의 연혁은 §5, 현재 판정은 최신 릴리스 문서와 `docs/evidence/<version>.json`이 소유한다. MVP=1.0 필수, OPTIONAL=해당 기능을 포함하면 필수, FUTURE=1.0에는 실행 대상 아님. 각 사건은 별도 fixture에서 반복해 데이터 오염을 피한다.

| ID / 대상 | 조건과 사용자 행동 | 기대 결과·실패/경계 검증 |
| --- | --- | --- |
| AUTH-LOGIN-001 / MVP | 기존 이메일 및 별도 username 회원이 유효 credential로 로그인, remember on/off | Core cookie로 다음 요청에서 같은 ID; 역할 불변; 올바른 목적지; 성공 event 1회; device-limit 정상 경로 |
| AUTH-LOGIN-002 / MVP | 틀린 password/없는 회원/disabled/pending/과도한 입력 | 공통 credential 오류·인증 cookie 없음·다음 요청 비회원; 기존 third-party auth 거부 보존 |
| AUTH-LOGOUT-001 / MVP | nonce 있는 logout 실행, 이전 cookie 재사용 | 로그아웃/세션 폐기 후 보호 자원 접근 불가; 외부 redirect 거부; 재실행 안전 |
| AUTH-REGISTER-001 / MVP | Core `users_can_register=1` + 필수 문서 준비 + 필수 필드·동의 제출, 한국어 표시명·빈 전화 포함 | WP user 정확히 1개·서버 역할·필수 동의 영속화. 기존 Members 가입 option 값은 결과에 영향 없음; 전화 선택; 이메일 인증·자동 로그인 없음; 재전송 중복 없음; 저장 실패 시 pending·재시도로 완료 |
| AUTH-REGISTER-002 / MVP | Core `users_can_register=0`, 필수 문서 미준비, duplicate email/동시 동일 email/필수 누락/동의 누락/role·ID 주입 | 가입 폼·처리 닫힘 또는 성공 계정 0개, 경합 중 1개만; role 상승 없음; 기존 email/login 불변; 안전한 오류 안내 |
| AUTH-REGISTER-FIELDS-001 / 0.7.18 extension (SPECIFIED) | 기본 설정, 이름·성·전화의 필수/선택/숨김 조합, 비관리자 설정 시도, hidden field·role·ID·meta 주입, invalid schema/state | 0.7.17 기본 동작 보존; 내장 세 필드만 변경; 숨김 입력 무시; invalid update 전체 거부; Core ID/auth·동의·profile·Woo/LMS 데이터 불변 |
| AUTH-RESET-001 / MVP | 분실→sink link→유효 key로 reset, 만료·재사용·다른 login·동시 소비 | 실제 Core password만 변경; 이전 key 재사용 거부; old session 무효 확인; 자동 로그인 없음; public 존재 여부 비노출 |
| AUTH-REDIRECT-001 / MVP | LMS lesson·강의실 tab·checkout 목적지; 외부/동일 host 다른 port/CRLF/이중 인코딩/중첩 URL | 허용된 원래 목적지 유지, 위험 주소는 local fallback; 무한 루프 없음; 목적지 resource 권한 별도 검사 |
| AUTH-PROFILE-001 / MVP | A가 이름·표시명·전화 수정; B user_id/role/state/meta/script 주입 | A allowlist만 변경, B/role/verified/과거 주문 불변; 한글 보존·출력 escape·invalid email/phone 거부; 1.0 email read-only |
| AUTH-CONSENT-001 / MVP | 신규 version 동의/선택 marketing 미선택/legacy agree import/철회/중복 POST | 문서 snapshot/hash/version과 서버 시각 일치; legacy version/time NULL; 빈값 동의 생성 없음; idempotency; consent 저장 실패 성공 금지 |
| AUTH-WITHDRAW-001 / MVP | A 최근 재인증 후 탈퇴, 반복 요청·타인 ID·잘못된 nonce·domain 작업 실패 | 즉시 차단·Core session/application password 철회; ID·주문·학습 참조 유지; queue 상태 정확; 실패 시 완료 표시 금지; 승인 전 PII 자동 삭제 없음 |
| AUTH-NOTIFY-001 / MVP extension (SPECIFIED) | 가입 완료·비밀번호 변경·탈퇴 접수·관리자 처리 완료, 중복 요청·상태 저장 실패·메일 실패 | 성공 상태 확정 뒤 현재 Core 이메일에 고정 안내 1건; 비밀·주문·LMS 정보 없음; P0-2~P0-4 성공·거부·중복·한국어 catalog·mail 실패 합성 검증 완료 |
| AUTH-EMAIL-VERIFY-001 / OPTIONAL | valid/expired/revoked/replayed token, GET scanner, resend, concurrent POST, email change | GET 미소비; POST 한 번만 성공; 목적/email binding; resend 이전 token 거부; mail 실패 미검증; legacy 계정 일괄 차단 없음 |
| AUTH-2FA-001 / FUTURE | password만 성공·정상/오류 TOTP·코드 replay·challenge theft·recovery·모든 login 입구 | 최종 검증 전 auth cookie/current user 없음; browser binding·원자 소비; recovery 1회; Woo/Core/social/XML-RPC/application password 우회 없음 |
| AUTH-SOCIAL-001 / FUTURE | provider mock 정상·잘못된 issuer/aud/signature/state/nonce/PKCE/redirect, 동일 callback race | provider subject로 동일 WP ID, 실패 cookie 없음, 중복 생성 없음, Core lifecycle/2FA/DL 정책 거부 보존 |
| AUTH-SOCIAL-LINK-001 / FUTURE | 같은 이메일의 기존 WP 계정, 다른 browser link intent, unlink/revoke 실패 | email만으로 auto-link 불가; 기존 계정 재인증 필요; subject unique; 마지막 로그인 수단 제거 불가; 로컬 revoke 우선 |
| AUTH-RATE-LIMIT-001 / MVP | 동일/분산 identifier·IP, 위조 proxy, IPv6, 병렬 100회, TTL 만료/adapter 장애 | 원자 count, 임계 이후 429/Retry-After, spoof로 우회 불가; 무제한 option 누적 없음; 의도적 영구 lockout 없음 |
| AUTH-WOO-001 / MVP | checkout 비회원→login→원래 cart/checkout, My Account 주문, 기존 user 주문, guest 과거 주문 | guest/signup 현행 정책 유지, cart 보존, customer_id 동일; billing/주문 domain 미복제; 이메일 같아도 guest 주문 자동 claim 없음 |
| AUTH-LMS-001 / MVP | 구매 user의 강의·progress·certificate·question, A/B 권한; Members off | WP ID·enrollment relation 동일; 타인 강의 접근 거부는 LMS 유지; Members off fatal 없음/로그인 fallback; profile delegation |
| AUTH-KBOARD-001 / MVP compatibility | KBoard 제거 전 board·댓글·회원 login link smoke, restriction 3페이지/메뉴 3개 연결 | KBoard가 권한 owner로 남고 Members on/off에서 fatal 없음; Members의 KBoard 권한 엔진 이전·복제, full permission parity·content migration은 범위 밖 |
| AUTH-DEVICE-001 / MVP | device-limit 허용/차단/제거된 장치에서 Members·Core·Woo 로그인 | 기존 거부가 성공으로 뒤집히지 않음; logout detection/relogin 목적지 정상; 보안 event 중복 없음 |
| AUTH-CSRF-001 / MVP | guest/로그인 회원의 cross-origin POST, guest token 다른 browser, nonce missing/expired | mutation/인증 cookie 발생 없음; 허용 same-origin 정상 요청은 성공; guest WP nonce 하나만으로 통과 불가 |
| AUTH-COOKIE-001 / MVP | pre-auth browser token·로그인 전후 cookie·shared cache·로그아웃 cookie·2FA 1단계 | Core만 최종 auth cookie 발급, pre-auth 값으로 인증 불가; transport flags/no-store; 계정 A 화면이 B에게 cache 노출 안 됨 |
| AUTH-ENUM-001 / MVP | 존재/미존재 identifier로 login/reset/register/error API 비교 | 공개 응답 형태 동일, 사용자 정보 비노출; timing 분포 차이 검토; Core/site 별도 노출 한계 기록 |
| AUTH-PRIVILEGE-001 / MVP | 일반 회원이 admin setting/audit/다른 user의 profile·consent·withdrawal 접근 | 403 또는 동일한 비노출 응답; 아무 변경 없음; nonce 있어도 capability 없으면 거부 |
| AUTH-AUDIT-001 / MVP | 성공/실패/탈퇴·민감 변경, 로그 저장 장애, retention cleanup | 원문 credential/token/email/IP 없이 최소 event 1회; 접근 제한; 보존 cutoff·pseudonym 삭제; audit 장애로 개인정보 fallback dump 안 함 |
| AUTH-MIGRATION-001 / MVP | import dry-run→실행→재실행, route rollback, 임의 prefix | ID 재매핑 0, 신규 업무 소실 0, legacy reader/owner 검증, 동의 중복 0, rollback 후 필수 정책 유지 |
| AUTH-PERF-001 / MVP | 같은 브라우저로 일반 글/LMS 동시 요청; Members on/off | Members 때문에 session_start/session cookie/lock 직렬화가 생기지 않음; 타 plugin session과 귀속 분리 |
| AUTH-PERF-002 / MVP | account UI 없는 page·lesson·LMS 탭, UI 있는 page/widget/block | 전자는 Members frontend CSS/JS/외부 request 0; 후자는 필요한 assets만, 중복 enqueue 없음 |
| AUTH-PERF-003 / MVP | cache warm/cold 일반 GET on/off, auth state가 다른 사용자 | 아래 비용 budget, 계정 query/provider load 없음; lifecycle guard는 보호 상태를 정확히 반영 |

### 2.1 Phase 1 UI 계약

`AUTH-UI-001`은 [UI_UX.md](UI_UX.md)와 `tests/harness/ui_contract.json`에서 로그인·가입·계정·프로필·비밀번호·동의·탈퇴·로그아웃·관리자 화면의 상태, 접근성, 번역, route 전용 자산 기준을 고정한다. executable guard는 현재 route와 template surface가 계약에서 빠지거나 이름이 어긋나면 실패한다.

이 항목은 기존 Phase 0의 24개 runtime behavior contract 집계에 추가하지 않는다. 상태는 **SPECIFIED**이며 `AUTH-UI-002` 구현은 완료했다. 2026-09-07 MAMP smoke에서 가입·로그인 오류·로그인 회원의 6개 계정 화면·관리자 화면, 360px reflow, keyboard focus, Members route CSS와 일반 페이지의 Members CSS 0을 확인했다. 모든 보안 상태 전이의 UI 회귀는 기존 MVP behavior harness와 후속 통합 gate가 소유한다.

0.7.5는 `AUTH-UX-003`의 첫 번째 runtime slice인 로그인·회원가입 shell, 안전한 입력 복원, field 오류 연결, 약관 상세 표시, route 전용 password visibility enhancement와 clean-route preflight를 구현했다. 단위 계약 25개, 0.7.5 ZIP 번역/package gate, 합성 WordPress 전체 실행 `618b1354f1484a4b96d4bd319feef581`, MAMP lifecycle `mamp-lifecycle-1d042c936753`가 PASS했다. 실제 브라우저 JavaScript·키보드·no-JS 화면 검증은 0.7.9 gate에 남아 있고, production acceptance는 staging backup/restore와 관찰 기간 전까지 `PARTIAL`이다.

0.7.6은 두 번째 runtime slice인 account/profile/consent/password UX, Core reset wrapper와 plugin-owned link-only navigation slot을 구현했다. executable unit guard는 Core reset API 세 개 사용, 일반화된 reset request 응답, reset limiter 연결, token 화면의 no-store/no-referrer, 자체 token/cookie/session 부재, optional local link validation과 Woo/LMS domain read 부재를 검사한다. 이번 Sol 구현 turn에서는 반복 MAMP/browser 실행을 하지 않으며 실제 reset mail link·키보드·no-JS·mobile browser 검증은 0.7.9 gate에 남긴다.

0.7.7은 Users 영역 관리자 정보 구조, 읽기 전용 overview 진단, 저장 전 문서 preview와 immutable history, Core Users의 account state·현재 필수 consent 컬럼/필터를 구현했다. executable guard는 네 section, legacy Tools redirect, capability, bounded history, route-scoped admin asset과 Woo/LMS domain read 부재를 검사한다. 탈퇴 복구와 audit 조회 workflow는 0.7.8, MAMP/browser 반복은 0.7.9가 소유한다.

0.7.8은 `withdrawal_pending→active` 사유 있는 복구와 `withdrawal_pending→disabled` 확정, 기존 Core session 재철회, 재실행 멱등성을 구현했다. audit은 event/result/UTC date/user ID filter, 25건 page limit, 번역된 event/result/reason과 읽기 전용 mail 결과를 제공한다. 단위 계약 28개와 PHP 파일 57개 검증이 PASS했고, 합성 WordPress 실행 `d9256bc16d5843e98164623feffb3b03`은 두 prefix에서 24개 MVP 계약, 알림 확장 계약, Core/Members 로그인 각 12건을 통과했다. 이 검증은 복구와 확정 모두에서 WordPress ID 보존, 외부 domain 삭제 부재, session 0과 최소 audit을 검사하며 브라우저 반복은 0.7.9가 소유한다.

### 2.2 계정 알림 계약

`AUTH-NOTIFY-001`은 [NOTIFICATIONS.md](NOTIFICATIONS.md)와 `tests/harness/notification_contract.json`에서 가입 완료·비밀번호 변경·탈퇴 접수·탈퇴 처리 완료의 사용자 알림을 고정한다. 기존 24개 MVP runtime 계약 집계에는 추가하지 않는다. 상태는 **SPECIFIED**, runtime은 **IMPLEMENTED_AND_SYNTHETIC_VERIFIED**다.

`AUTH-NOTIFY-002`는 0.7.10의 **IMPLEMENTED_AND_SYNTHETIC_VERIFIED** 계약이다. `tests/harness/notification_settings_contract.json`은 기존 네 사건의 plain-text 제목·본문만 WordPress Settings API와 non-autoload option으로 관리하도록 고정한다. 실행 `d28853b554c5497eb50df18d7f24dffe`는 두 prefix에서 저장·권한·fallback·placeholder·감사와 기존 메일 회귀를 PASS했다. 실제 운영 mailbox 전달은 배포 환경 gate다.

WooCommerce 주문·결제 메일과 LMS 수강·진도·수료증 알림은 각 domain owner에 남는다. 이메일 가입 인증, 관리자 알림, 마케팅, SMTP/provider와 재시도 queue는 두 계약 모두의 범위가 아니다. 편집 가능한 제목·본문은 `AUTH-NOTIFY-002`에만 속한다. P0-3은 gettext/한국어 catalog 검증을 완료했고, P0-4는 네 사건의 메일 실패 주입과 보안 상태 보존·실패 감사·전달 기록 0·재시도 0을 완료했다.

2026-09-09 P0-2 실행 `0d31685ae4584e49af3aa5f54c0896a0`는 WordPress 7.1/PHP 8.3의 새 임시 설치에서 `wp_`와 임의 prefix를 각각 검사했다. P0-3 실행 `bacdd413b3444dd694baa26d725e7e9a`도 두 prefix에서 네 알림 preset, 현재 Core 수신자, 명시적 plain-text header, 성공 후 발송, `wp_mail` 수락 감사 결과, 거부·재실행 중복 0, credential/token·주문/LMS 상세 미포함, Members-off hard dependency 없음과 `ko_KR` 사이트 fallback/사용자 locale catalog 렌더링을 PASS했다. P0-4 릴리스 실행 `aed831b84fe140708b6346e244a2190c`는 두 prefix의 네 실제 HTTP 계정 경로에 실패를 정확히 4회 주입해 확정 상태·세션 철회·성공 응답 유지, `failure/wp_mail_failed` 4건, 전달 sink 0건, 자동 재시도 0건을 각각 PASS했고 성능 블록도 PASS했다. 0.7.4 회귀 실행 `5886351d4d39439993fae700b0cb610a`는 같은 계약과 `AUTH-PERF-003`을 다시 PASS했다. 0.7.5 합성 실행은 `618b1354f1484a4b96d4bd319feef581`이며, 모든 실행의 임시 DB/filesystem과 process가 정리됐고 reference에는 쓰지 않았다. 최신 로컬 증거는 `.harness/reports/latest.json`에 있다.

가입 동시성은 단순 재클릭과 다르다. 동일 normalized email의 병렬 요청·다른 case·동일 idempotency key·서로 다른 key를 각각 검사한다. 사용자 생성 후 consent 저장 실패, mail 송신 실패, usermeta finalize 실패를 따로 주입한다. account pending 상태의 fail-closed를 검사하고 고아 계정 재사용·완료 절차를 검증한다.

## 3. Performance budget

현재 TTFB·메모리·query 횟수를 계측하지 않았다. 비활성 Cosmosfarm에 대해 “지금 N ms 절감된다”거나 fork 대비 속도 배수를 제시하지 않는다. 아래는 초기 **수용 예산 제안**이다.

| 지표 | 초기 budget |
| --- | --- |
| 일반 frontend PHP session | Members 유발 session_start 0, PHPSESSID 생성 0, session lock 0 |
| UI 없는 화면 Members asset | CSS/JS/외부 HTTP 0; 전체 사이트 자산 0을 의미하지 않음 |
| 일반 GET Members DB write / 외부 call | 0 / 0. 탈퇴 토큰 철회 같은 명시적 보안 사건 처리 예외는 별도 계측 |
| 일반 GET 추가 DB read | warm cache 직접 query 0 목표. cold cache config read 최대 1 + 필요한 현재 사용자 meta cache miss 최대 1을 초기 상한으로 검증; 게시물/수강 전체조회 없음 |
| 일반 GET 무거운 초기화 | Admin/Social/OTP SDK 객체·전수 provider load 0, install/cron 예약 반복 0 |
| TTFB | 동일 환경 paired on/off에서 median·p95 증가가 각각 `max(기준값의 5%, off/off 반복 noise envelope)` 이내를 잠정 gate로 사용. 절대 ms 기준은 baseline 후 승인 |
| 메모리 | 1차 gate는 loading 대상·객체 수와 peak delta 계측. 근거 없는 고정 MB 목표는 두지 않고 baseline 후 합리적 상한을 기록 |

5%는 달성 사실이 아니라 “의미 있는 일반 요청 회귀를 차단”하려는 초기 상대 예산이다. baseline noise가 커 구분이 안 되면 측정 실패/INCONCLUSIVE로 판정하고 이를 회귀 허용 구실로 삼지 않는다. feature load가 늘어도 baseline 자체를 임의로 올려 통과시키지 않는다.

측정 절차:

1. 고정 WP/PHP/MySQL·plugin set·cache·OPcache 상태로 anonymous article, anonymous course, authenticated lesson, classroom tab, account UI를 분리한다. baseline은 동일 stack Members off, 비교는 Members on이다. legacy active 비교는 별도 실험으로 분리한다.
2. warm-up 20회 후 route별 100회 이상, off/on 순서를 번갈아 3 block 측정한다. cold 시작은 별도 기록하고 DB/cache/server 부하를 고정한다. Query Monitor 영향은 on/off 동일하게 하거나 두 쪽 모두 끈다.
3. 같은 client에서 병렬 요청으로 session 직렬화를 검사한다. 시간만 보지 않고 session handler/Set-Cookie·wait stack 증거를 함께 본다. Woo cookie/session이 있음을 Members PHP session으로 오판하지 않는다.
4. median/p95 TTFB, paired delta, noise envelope, query/read/write, loaded file/module, memory peak, asset 목록을 기록한다. 실제 출력 값과 상태 조건을 같이 저장하고 route aggregate 하나로 숨기지 않는다.
5. 불안정하면 반복 전 원인을 찾는다. gate 통과 후 코드/환경 변경 없이 테스트를 무의미하게 반복하지 않는다.

## 4. Release gate

모든 MVP contract의 성공·거부·복구 경로 통과와 주요 D01/D02/D06/D07 결정이 있어야 실제 전환한다. OPTIONAL/FUTURE를 넣는 순간 관련 contract는 release 필수로 승격한다. legacy 버그나 보안 취약 행동은 기대값으로 고정하지 않고 의도적 차이와 사용자 영향을 기록한다.

최소 보고 항목은 환경 버전, route owner, fixture, case ID, 기대/실제, 증거 파일, 실패 원인, 남은 unknown, cleanup/rollback 결과다. raw credential/token/사용자 개인정보를 증거 artifact에 넣지 않는다. 이미 사용자 데이터가 있는 reference에서 “시험 삼아 로그인”하는 검증은 이 계획에 포함되지 않는다.

## 5. 실행 증거 연혁

다음 표는 최초 24개 계약 합성 실행의 역사적 snapshot이다. `tests/harness`는 **CORE_BASELINE_ONLY**와 **MEMBERS_ON**을 순서대로 구분하고, 당시에는 실제 device-limit 1.1.3 파일을 읽기 전용 reference에서 임시 site로 복사해 PHP hook을 검증했다. 그 시점의 Woo/LMS는 합성 domain row와 Members-off fallback, KBoard는 제한된 smoke만 검증했으므로 당시 전체 stack 판정은 PARTIAL이었다. 이후 실제 MAMP 보강과 현재 판정은 §5.1 이후 및 최신 릴리스 evidence를 따른다.

| 항목 | 실행 결과 |
| --- | --- |
| 환경 | Windows / WordPress 7.1 en_US / PHP 8.3.1 / MySQL 5.7.24 / Python 3.12.14 |
| Core provenance | pinned archive SHA-256 + pinned manifest SHA-256, 공식 파일 checksum 3,782개 일치 |
| run ID | `dde968a6cb8a4367abb69708568c62bc` |
| Core baseline | 12/12 PASS: email identity, 별도 username의 username/email × remember off/on × prefix 2종 |
| Members-on | 12/12 PASS; 위험 redirect 8종 거부·local 목적지 3종 유지 × prefix 2종 |
| Core 계약 | 두 모드에서 합성 ID 2/3 유지, subscriber/capability/한글 표시명 불변, local 목적지 유지, Core 성공 event 각 1회 |
| cookie | 두 모드 모두 Core HttpOnly auth cookie; remember off=session, on=persistent; PHPSESSID·Members auth cookie 0 |
| 활성화·쓰기 | identity/role/domain 지문 불변; 승인된 audit/consent 표 2개와 비자동로드 option 6개만 생성; 로그인 중 Core session token과 제한/audit 기록만 변경 |
| 구조적 성능 guard | 일반 frontend에서 entry/Core router만 load; Members CSS/JS·PHP session·custom DB write·외부 HTTP event 0 |
| 신뢰성 control | cookie 제거 시 anonymous, wrong-ID assertion 실패, observer 무키 403, 비대상 route 404 |
| 당시 전체 계약 | 24개 모두 실행 경로 존재: 19 PASS, 3 SYNTHETIC_PASS(Woo/LMS/KBoard), 2 PARTIAL(enum timing, device Woo entry) |
| 관리자·탈퇴 | `wp_`/임의 prefix 모두 일반 회원 관리자 GET 거부·관리자 nonce 재사용 거부; 대기 queue 표시 후 `withdrawal_pending→disabled`, ID 보존, 재실행 audit 중복 0 |
| 성능 | 3×100 off/on: median 406.481→405.573ms, p95 477.919→477.217ms; 각 허용 budget 내, query median 5→5 |
| runner safety | 15/15 unit 검사 PASS; production·harness PHP syntax 검사 PASS |
| side effects | mail sink 실동작 및 WP HTTP API 차단 검증; 실제 외부 송신 없음 |
| cleanup | 소유 PHP/MySQL 프로세스 종료, 임시 DB/filesystem 삭제 확인 |
| 증거 | `.harness/reports/dde968a6cb8a4367abb69708568c62bc.json` (git 제외; 최신은 latest.json) |
| 당시 미검증 | Woo browser login 제출 후 cart/checkout 연속성과 렌더링된 My Account 주문, KBoard 제거 전 호환성 smoke/no-fatal, KBoard 권한 parity/content migration(범위 밖), device-limit Woo form, TLS/Secure cookie, browser JS, 분산/병렬 abuse campaign |

### 5.1 AUTH-WOO-001 MAMP 실제 stack 보강

2026-09-07 전용 `kklidi-members-mamp-sandbox`에서 WordPress 7.1, WooCommerce 11.1.0, KKLIDI WCI 1.0.3, device-limit 1.1.3, Members 0.2.0 조합을 확인했다. 고정 sandbox/URL만 허용하는 `tests/harness/mamp_woo_case.php`가 합성 사용자·상품·주문을 만들고 주문을 run token으로 표시하며 원래 option과 plugin 활성 상태를 복원한다.

| 항목 | 실행 결과 |
| --- | --- |
| run ID | `mamp-woo-c4a9e2d710bf` |
| 익명 checkout | 합성 상품을 cart에 넣은 뒤 checkout 접근 시 Members 로그인으로 이동; `redirect_to`는 원래 checkout URL 유지 |
| 주문 경계 | 기존 회원 주문의 `customer_id`는 같은 WP user ID 11, 같은 billing email의 guest 주문은 `customer_id=0`; 계정 주문 조회에는 회원 주문만 포함 |
| 정책 설정 | 실행 중 guest checkout=no, checkout signup=no, My Account registration=no로 관찰된 Phase 0 정책 고정 |
| optional dependency | Members off에서 checkout은 Core `wp-login.php`로 이동하고 My Account는 HTTP 200/치명 오류 없음; 같은 검증의 `finally`에서 Members 재활성화 |
| cleanup | 합성 user/product/order 4개 부재 확인, guest checkout=yes·signup=no·registration=no 원복, WCI 비활성화 후 임시 복사 삭제, Members 활성 확인 |
| 당시 판정 | **PARTIAL**: 실제 redirect·domain ownership·Members-off는 통과했으나, 이 실행에서는 로그인 POST 뒤 같은 Woo session의 cart/checkout 유지와 렌더링된 My Account 주문을 아직 실행하지 않음 |
| 증거 | `.harness/reports/mamp-woo-c4a9e2d710bf.json` |

### 5.2 AUTH-LMS-001 MAMP 실제 stack 보강

2026-09-08 같은 전용 sandbox에서 WordPress 7.1, WooCommerce 11.1.0, KKLIDI LMS 1.1.1, device-limit 1.1.3, Members 0.2.0 조합을 실행했다. `tests/harness/mamp_lms_case.php`는 고정 sandbox/URL과 12자리 run token만 허용하며, 합성 사용자·강의·차시·상품·주문·진도·수료증·비공개 질문을 만들고 알림 메일을 sink한다. 수강 등록은 LMS의 실제 WooCommerce 주문 reconciliation API로 만들었다.

| 항목 | 실행 결과 |
| --- | --- |
| run ID | `mamp-lms-4f91a2c6d8be` |
| 구매·identity | Woo 주문의 `customer_id`, LMS enrollment/progress/certificate/question의 `user_id`가 같은 WordPress user ID 15를 유지; enrollment source는 `woocommerce` |
| 멱등성 | 같은 주문을 두 번 reconcile해도 해당 주문 enrollment는 1개 |
| LMS domain | 진도 100%, 수료증과 비공개 질문 생성; 데이터는 LMS/Woo 테이블·API가 소유하고 Members는 이를 조회하거나 복제하지 않음 |
| A/B 접근 | 수강자는 강의·차시·질문 접근 허용, 비수강자는 강의 목록에서 제외되고 학습 화면과 질문 접근 거부 |
| profile delegation | Members on + 로그인 + 실제 LMS 강의실 profile tab에서 Members profile URL로 HTTP 302; LMS shortcode가 없는 페이지에는 적용하지 않는 route guard 추가 |
| optional dependency | Members off에서 수강자 학습과 LMS 자체 profile은 HTTP 200/치명 오류 없음; 익명 강의실은 Core `wp-login.php` 사용; Members 재활성화 확인 |
| 자산·side effect | LMS 화면에 Members CSS 0; 질문 알림 메일 1건 sink, 실제 외부 송신 0 |
| cleanup | 합성 user/post/product/order/enrollment/progress/certificate/question/message/activity/device 행 모두 0, 원래 option 복원, Members 활성 확인 |
| 판정 | **PASS** |
| 증거 | `.harness/reports/mamp-lms-4f91a2c6d8be.json` |

### 5.3 0.5.0 추가 검증

- `257a25a207b646f88ba74cd0dd93bfb0`: post-0.5.0 one-prefix synthetic 재검증에서 Core on/필수 문서 없음, Core off/필수 문서 준비, Core on/필수 문서 준비의 세 상태를 실행했다. 앞의 두 상태는 가입 폼을 숨겼고 마지막 상태는 obsolete Members option이 `0`이어도 가입·필수 동의 저장에 성공했다. 전체 24개 MVP 계약 PASS, 임시 DB 제거와 프로세스 종료를 확인했다. 성능 블록은 이 소규모 재검증에서 제외했다.
- `mamp-woo-be0342cba88e`: 실제 로그인 POST 뒤 checkout 복귀, 같은 쿠키 세션의 Woo Store API cart 상품 보존, 회원 주문 상세 링크 표시와 guest 주문 제외, Woo 자체 로그인 폼의 device-limit 허용/거부 PASS. HTTP form 검증이며 JavaScript 엔진을 실행한 브라우저 증거는 아니다.
- `mamp-kboard-394cb2f1d392`: 실제 KBoard 6.5의 목록·게시글·댓글 HTTP 200, 회원/비회원 쓰기 권한, 게시글·댓글 작성자 ID 유지, Members CSS 0을 on/off에서 확인했다. 합성 board/content/comment/user/page 잔존 0. 이 실행 당시에는 D06 restriction 3페이지·메뉴 3개의 운영 owner가 미확정이어서 전체 계약을 PARTIAL로 기록했다.
- `concurrency_case.php`: 별도 PHP 프로세스 8개에서 동일 limiter key에 100회 요청, 각 prefix에서 정확히 10회 허용. 분산 공격·가입/reset 경합 전체 통과로 확대 해석하지 않는다.
- 공개 정책과 환경별 미검증 항목은 [RELEASE-0.5.0.md](RELEASE-0.5.0.md)에 남긴다. 이전 실행의 수치·분류는 역사적 증거로 유지한다.

일반 실행은 cache만 사용하는 offline 방식이며 dependency 준비만 공식 HTTPS 다운로드를 사용한다. 매 실행 fresh DB와 per-run synthetic secret을 만들며 기존 endpoint/datadir 입력 option은 없다. runner safety unit 검사는 별도로 실행한다. 실행 절차와 상세 guard는 `tests/harness/README.md`가 소유한다.

D01은 선택 전화, 이메일 인증 없음, 자동 로그인 없음으로 확정했다. D02는 자동 삭제 없는 차단·수동 queue 계약으로 확정했다. D06의 정산/강의실 owner와 정적 신청 페이지의 사이트 운영 owner를 읽기 전용 감사로 분리했고 Members는 범용 제한 엔진을 소유하지 않는다. D07의 0.7.4 지원 판정은 실제 runtime을 실행한 single-site WordPress 7.1/PHP 8.3/Woo 11.1.0에 한정한다.

2026-09-08 0.7.0 보강 실행: `mamp-https-703376f74438`은 MAMP Apache 뒤 임시 TLS proxy에서 TLS 1.3, HSTS, hostname 검증, `__Host-` Secure/HttpOnly/SameSite/host-only guest cookie, Core Secure/HttpOnly auth cookie, no-store와 PHPSESSID 부재를 통과하고 합성 user·plugin 목록·MU bootstrap·인증서 디렉터리를 복원했다. `mamp-race-a3364a28d0f1`은 가입/reset 경쟁, `mamp-woo-b4b7885b4d3a`는 checkout/cart/order/device-limit, `mamp-timing-f9ad12a0c504`는 동일 공개 문구와 median 비율 1.339를 통과했다. 공유 DB limiter는 독립 PHP process 8개·100회에서 10회만 허용하며 object-cache 호출 장애와 분리되고 DB storage 실패는 fail-closed한다. 로컬 CA/proxy는 실제 운영 인증서·CDN·다중 host를 증명하지 않으므로 운영 manifest와 trusted staging 재검증은 남는다.

2026-09-09 0.7.1 보강: 실제 LMS 검사를 고정 MAMP runner로 만들고 WordPress ID 연속성, Woo 주문 reconciliation 멱등성, 진도·접근·프로필 위임, Members-off fallback과 실행 토큰 기반 cleanup을 JSON으로 기록한다. lifecycle runner는 고정 sandbox와 0.7.0/현재 ZIP만 허용해 신규 설치, 0.7.0→현재 버전 업데이트, 재설치, 비활성·재활성, 보호 ID/domain 지문과 원본 tree 복원을 검사한다. 두 runner는 운영 URL이나 DB를 입력받지 않는다.

2026-09-09 0.7.9 타이포그래피 계약: `AUTH-UX-004`를 추가해 Members route 전용 본문 16px, H1 28~32px, H2 20~22px, 보조 문구·오류 14px, 약관 본문 15px과 줄간격 기준을 CSS custom property로 고정했다. 단위 하네스 29개가 PASS했으며, 사이트 테마 전역·LMS·WooCommerce·KBoard 화면에는 CSS를 확장하지 않는다. 실제 desktop/mobile·키보드·zoom 검증은 0.7.9 browser release gate에 남는다.
2026-09-09 0.7.9 typography browser gate: `mamp-typography-20260909`에서 1920px·360px viewport의 computed typography, 가로 overflow 부재, keyboard focus-visible outline, 서버 렌더링 form/필수 동의, homepage route isolation을 PASS했다. `mamp-lifecycle-66ccd84b74b6`의 Members-off fallback과 함께 고정 MAMP 샌드박스를 원래 0.7.0 활성 상태로 복원했다. 전체 0.7.9 운영 release gate와 Studio01 반영은 별도 승인·관찰 단계다.
2026-09-10 0.7.17 `AUTH-ADMIN-UX-001`: Users 하위 관리자 화면에 actionable prerequisite diagnostics, quick links, canonical Members route link 목록, notification fallback 안내, withdrawal pending count/user link, audit clear-filters를 추가했다. 자동 페이지 생성·메뉴 변경·관리자 수신 메일·HTML 메일은 추가하지 않았다. 단위 계약 31개와 MAMP lifecycle `mamp-lifecycle-6e753ce8d22e`에서 신규 설치·업데이트·재설치·비활성 fallback·ID/domain 보존을 PASS했다. 외부 mailbox 전달은 provider와 수신 주소를 가진 운영 gate로 남긴다.
