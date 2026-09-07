# Product · 기존 시스템 audit

이 문서는 제품 범위·현행 증거·우선순위·fork 판정의 기준이다. 데이터별 처리 방침은 ARCHITECTURE, 보안은 SECURITY, 전환은 MIGRATION에 둔다.

## 1. 제품 정의

Members는 “누구인가”에 관한 공통 UX를 제공한다. 기본 identity는 기존 WordPress user ID다. WordPress의 users/usermeta, password hashing, authentication hooks, auth cookie, session token, role/capability, nonce, current user, password reset을 재사용한다.

Members가 담당하는 것은 계정 진입 URL, 로그인·로그아웃·가입·복구·프로필, 동의 증거, 연락처 상태, 계정 비활성화와 개인정보 처리 조정이다. 자체 users table, 암호 해시, 로그인 cookie, PHP session 인증, 별도 user ID, Core Auth 우회는 금지한다.

LMS의 enrollment·progress·lesson·certificate·course access, Woo의 주문·결제·환불·주문 계정 domain, PMS의 정산, Community/KBoard의 게시물·권한 domain을 복제하지 않는다. Members가 꺼져도 LMS의 Core identity 조회가 fatal을 내면 안 된다.

## 2. Audit 방식과 증거 수준

Reference root `R = C:/MAMP/htdocs/ns_0727`, 플러그인 root `P = R/wp-content/plugins`. 아래 경로는 이 root 기준이며 line은 2026-09-06 로컬 파일 기준이다. 웹 배포 버전과 같은 파일이라고 가정하지 않는다.

| Evidence ID | 직접 확인한 근거 |
| --- | --- |
| E01 | `R/wp-config.php`에서 prefix `wp_`, DB `ns_0727`; DB server 5.7.24; `R/wp-includes/version.php`의 WP 7.1 |
| E02 | options `active_plugins` 24개: WooCommerce, KKLIDI LMS, KKLIDI WCI, device-limit, payout, KBoard/comments, WPCode, disable-emails 등. Cosmosfarm Members/WP-Members 없음. 관련 MU plugin 및 drop-in 파일 없음; WPCode cache의 cosmosfarm/wpmem/active_plugins 문자열 없음 |
| E03 | options `cosmosfarm_members_*`, `wpmembers_settings`, `wpmembers_fields`를 읽어 설정·필드·credential 존재 여부만 확인 |
| E04 | posts 2813 `/login/` `[cosmosfarm_members_login_form]`, 50 `/sign-in/` `[wpmem_form register]`, 56 `/profile/` `[wpmem_profile register=hide]`; 모두 publish |
| E05 | posts 35 `/my-account/` `[woocommerce_my_account]`, 34 `/checkout/` `[woocommerce_checkout]`, 11940 강의실 `[kklidi_lms_my_classroom]`; 모두 publish. 42 reset-password, 43 basic-profile에는 조사한 bracket shortcode 없음 |
| E06 | 사용자·usermeta·history·Woo·LMS 집계: ARCHITECTURE §2. 이름·이메일·전화·IP 원문 미출력 |
| E07 | `P/cosmosfarm-members/cosmosfarm-members.php:41` plugins_loaded, :50 session_start, :67 WPMEM 의존 init, :131 이후 nicename 보정, :494 전역 enqueue |
| E08 | `P/cosmosfarm-members/class/Cosmosfarm_Members.class.php:11` constructor hook, :1253 이메일 UX, :1270 가입 보정, :1429 login URL, :1470 redirect, :1499 Woo fields, :1837 가입 후 처리 |
| E09 | `P/cosmosfarm-members/class/Cosmosfarm_Members_Security.class.php:11` auth/history/OTP hook, :159 history 저장, :436 SMS OTP. `Cosmosfarm_Members_Controller.class.php:3156` delete_account |
| E10 | `P/wp-members/wp-members.php:81` after_setup_theme; `includes/class-wp-members.php:519` constructor, :620 hooks, :1680 CSS; `class-wp-members-user.php:112` wp_signon; `class-wp-members-pwd-reset.php:106,148,181` Core reset |
| E11 | `P/kklidi-lms/kklidi-lms.php:104` prefix helper; `includes/Core/class-kklidi-lms-plugin.php` load manifest가 실제 includes 경로 선택. 중첩 복사본 `includes/includes`, `kklidi-lms/kklidi-lms`를 실행 근거로 사용하지 않음 |
| E12 | LMS `includes/Frontend/class-kklidi-lms-classroom-renderer.php:27`, `class-kklidi-lms-public-shortcodes-renderer.php:87` wp_login_url; `class-kklidi-lms-classroom-profile-renderer.php:9` profile/password UI; `class-kklidi-lms-public-actions-handler.php:222` 변경 처리 |
| E13 | LMS `includes/Integrations/class-kklidi-lms-woocommerce.php:95` order→get_user_id; :176 grant_entitlement. `includes/Frontend/class-kklidi-lms-frontend.php:100` user ID→LMS can_access |
| E14 | `P/kklidi-woocommerce-integration/includes/class-settings.php:8` option `kklidi_wci_settings`; 그 설정의 checkout login redirect=1. `includes/modules/class-checkout-login-redirect.php:26` wp_login_url(checkout URL) |
| E15 | postmeta: Cosmosfarm restriction 3페이지, WP-Members 메뉴 `in` 3개; KBoard settings 12개, content 412개; Cosmosfarm KBoard constructor의 알림 옵션 조건 |
| E16 | `P/kklidi-device-limit/includes/hooks.php:4` authenticate priority 100/101, :6 wp_login. WCI와 device-limit는 활성. 자식 테마 회원 관련 문자열 검색은 직접 참조 없음 |
| E17 | 로컬 파일 버전: Cosmosfarm 4.9, WP-Members 3.5.6, KKLIDI LMS 1.1.1, WooCommerce 11.1.0. WP-Members entry에 GPLv3, Cosmosfarm class에 All rights reserved; 배포 라이선스 전체 미확인 |

`OBSERVED`는 저장된 설정/행/파일의 사실, `INFERRED`는 해당 코드가 로드될 때의 실행 경로, `UNKNOWN`은 실제 HTTP·운영 정책 미검증이다. 비활성 플러그인의 활성 당시 사용을 현재 운영으로 바꾸어 서술하지 않는다. 정적 검색 범위 밖 custom loader 가능성까지 전부 배제한 것은 아니다.

기능 분류는 **이 사이트의 후속 전환에서 취할 처분**이다. REQUIRED=행동 유지, REPLACEABLE=Core 기반 대체, UNUSED=이 snapshot에서 활성 사용 근거 없음, KEEP_TEMPORARILY=전환 중 호환 책임/증거 유지, UNKNOWN=추가 확인 필요. KEEP_TEMPORARILY가 지금 비활성인 플러그인을 켜라는 뜻은 아니다.

## 3. Cosmosfarm Members

| 기능 | 설정·경로·데이터 근거 | 분류와 결론 |
| --- | --- | --- |
| 로그인 UI | E04 로그인 shortcode, skin=two, 두 플러그인 현재 비활성 | REQUIRED: `AUTH-UI-001` 화면 계약 고정. `AUTH-UI-002` 구현·브라우저 검증 대기 |
| 로그인 redirect | login_redirect_page=main; E08 login_redirect가 목적지를 home으로 덮음 | REPLACEABLE: 안전한 원래 목적지 우선으로 의도적 변경 |
| 가입 보정 | allow_email_login=1, username 숨김·email 대입; 로컬 nicename 보정 추가 코드 | REQUIRED: 한국어 표시명과 비어 있지 않은 slug를 별도로 검증 |
| 가입 후 자동 로그인 | auto_login_after_registration=1, verify_email 빈값; E08 Core cookie 설정 분기 | MVP_OPTIONAL에 해당하는 REPLACEABLE; 1.0 기본은 명시적 로그인 |
| 회원정보 수정 | E04 profile shortcode; WP-Members 필드 hook | REQUIRED: field allowlist로 대체 |
| 비밀번호 | pwd_link=1이라 legacy 임시 비밀번호 메일 분기 비선택, WP reset 연계 | REPLACEABLE: Core reset link 유지 |
| 탈퇴 | use_delete_account=1; E09 wp_delete_user 경로 | REQUIRED: 요청/차단/처리 정책으로 재설계, 삭제 코드는 재사용 금지 |
| 약관 | service/privacy 본문 options 존재, agree usermeta 각 386명 | REQUIRED: 과거 증거 보존 + 신규 versioned 기록 |
| 로그인 기록 | save_login_history=1; history 8,707행 | REQUIRED: 최소 감사, 과거 기록은 LEGACY_KEEP |
| PHP SESSION | plugins_loaded에서 !admin && !JSON이면 session_start; redirect·가입 역할 등에 SESSION 사용 | REPLACEABLE: 금지 구조. 비활성 현재 요청에 비용이 있다고 주장하지 않음 |
| 이메일 인증 | verify_email 빈값, 관련 검증 usermeta 증거 없음 | UNUSED: 신규 선택 모듈 |
| OTP | phone 설정 빈값, roles=[]; Security에는 SMS 코드 경로 존재 | UNUSED: TOTP 사용 증거 아님 |
| 본인인증 | use_certification 저장 option 없음(기본 빈값), history 0행 | UNUSED: 주민/CI/DI 수집 불필요 |
| Social | social_login_active=[]; Naver credential 흔적 있음, Google/Kakao client ID 빈값, social identity meta 증거 없음 | UNUSED: 설정 흔적만으로 연결·사용으로 판단하지 않음 |
| Woo | E08 전역 checkout/billing/shipping filter. phone1에서 checkout phone default를 읽으나 phone1 populated meta 없음 | KEEP_TEMPORARILY: field 의미 확인 후 명시적 adapter; 기존 동작 그대로 복제 금지 |
| KBoard | KBoard 활성, E15; notifications_kboard/options 없음(기본 꺼짐); 댓글 로그인 영역 social 버튼 hook 존재 | KEEP_TEMPORARILY: 제거 전 로그인 link·Members on/off no-fatal 호환성만 확인. 권한 엔진 이전·복제와 content migration은 범위 밖 |
| frontend CSS/JS | entry :494~522는 일반 enqueue에 script/style, skin 파일 있으면 추가 | REPLACEABLE: UI 존재 시에만 load |
| 전역 hook | E07~09: content/menu/auth/avatar/Woo/footer/admin 관련 등록 | REPLACEABLE: 소수 필수 hook와 route loader |
| 일반 bootstrap | 많은 class include, Security 생성, WPMEM 존재 시 다수 객체·option 조회·cron 존재 검사 | REPLACEABLE: 정적 비용 원인 확인, TTFB 수치 미측정 |

## 4. WP-Members 및 중복

| 기능 | 근거 | 분류 |
| --- | --- | --- |
| 로그인 | user class가 wp_signon 사용; Cosmosfarm이 label·form·redirect 필터 적용 | REQUIRED: Core 로그인 자체를 새 엔진으로 바꾸지 않음 |
| 가입·필드 | E03/E04: 이메일, 비밀번호/확인, 표시명, first_name, billing_phone, 두 동의가 표시·필수 설정 | REQUIRED: 고정 필드만 지원, generic form builder 제거 |
| username/email | username 필드는 설정상 존재하나 Cosmosfarm이 숨기고 이메일 대입. 434명 중 397명 login=email | REQUIRED: 기존 37명 username login도 유지. 이메일 변경 시 user_login 불변 |
| 분실/reset | pwd_link=1, Core key validation/reset 사용 | REPLACEABLE |
| profile | /profile shortcode; 현재 LMS에 별도 profile/password 구현 | KEEP_TEMPORARILY: 같은 core 값의 여러 editor를 전환 순서로 정리 |
| 약관 | policy_service/privacy 필드가 Cosmosfarm 본문과 연결. 기본 tos 비표시·52행 모두 빈값 | REQUIRED: 새 동의와 legacy 증거 구분 |
| 접근 제한 | block.post/page=0, post_types=[], products=0; 메뉴 3개 `in` 있음 | KEEP_TEMPORARILY: 일반 제한은 UNUSED, 메뉴 표시 계약은 확인 필요 |
| shortcode | register/profile shortcode publish 상태로 잔존 | KEEP_TEMPORARILY: 신규 화면 route alias 후보 |
| usermeta | reg IP 433명, reg URL/username 386명, confirmation 1명 | KEEP_TEMPORARILY: 데이터별 판정은 ARCHITECTURE |
| Cosmosfarm 연결 | Cosmosfarm init은 WPMEM_VERSION 전제, 다수 wpmem_* hook | REPLACEABLE: 확장 UI와 기본 form engine이 결합된 구조 |
| CSS/JS | global enqueue_style는 unconditional, loginout script는 자체 분기. PHP 파일에서 session_start 검색 결과 없음 | REPLACEABLE: WP-Members까지 PHP session 의존이라고 묶지 않음 |
| 전역 초기화 | forms/API/shortcodes/products/email/user/menus/dialogs 생성, content/query/widget/REST hook | REPLACEABLE: account 없는 request도 객체 생성 |
| 실제 site 의존 | publish shortcode·menu·meta가 잔존하지만 E02에서 비활성 | UNKNOWN: 페이지 동작은 격리 환경에서 재현 |

중복은 login/profile/password UI와 필드 검증·동의·redirect의 여러 layer다. WP-Members는 폼과 Core 처리 연결, Cosmosfarm은 한국형 폼 보정·약관·부가 인증·감사·연동을 덧붙였다. 두 개의 별도 password engine이 있는 것으로 해석하지 않는다. 현재 LMS profile/password와 Woo My Account까지 편집 진입점이 추가되어 있다.

## 5. LMS · Woo · 주변 의존성

LMS 실행 manifest의 관련 코드에서 Cosmosfarm/WP-Members 직접 참조를 찾지 못했다. E12는 Core login URL, WP_User, nonce, wp_update_user/wp_check_password를 사용한다. 이메일은 LMS 화면에서 disabled이며 이름·성·표시명·소개 및 비밀번호를 수정한다. Members 활성 후에는 공통 profile/password URL로 위임하고, 비활성 시 기존 UI 또는 Core fallback을 유지한다. 인증서 snapshot_name, `_kklidi_lms_verified_name*`는 계정 표시명과 다른 LMS 도메인으로 유지한다.

E13의 Woo entitlement는 order get_user_id가 0이면 진행하지 않으며, 같은 WP user ID/course/order로 enrollment를 만든다. 현재 enrollment 233행 중 Woo 출처는 1행이므로 구매 연동이 넓게 검증되었다고 볼 수 없다.

Woo 설정은 guest checkout=no, checkout signup=no, My Account registration=no, login reminder=no다. 가입 시 username/password 자동생성 설정은 yes지만 가입 진입 자체는 현재 꺼져 있다. Core users_can_register=0, default_role=subscriber다. 새 제품을 켜는 것과 공개 가입 허용은 별도 결정이다.

활성 WCI가 checkout에서 비회원에게 Core login URL + checkout 목적지를 전달한다. Cosmosfarm이 활성인 구성에서는 main redirect 설정과 충돌할 가능성이 있다. 현재는 실제 리다이렉트를 호출하지 않았다. Woo My Account는 주문·주소 화면의 소유자로 유지한다. 회원 프로필 이메일과 billing_email, 이름과 billing_first_name, 계정 전화와 주문 당시 phone은 자동 동기화하지 않는다.

HPOS가 켜져 있으며 611 shop_order 중 customer_id=0은 28행이다. 현재 guest 금지 정책으로 과거 guest 주문이 없어지는 것은 아니다. 과거 주문을 이메일만으로 회원에게 자동 연결하지 않는다.

KBoard는 12개 board 중 author/roles 제한을 갖는 board가 있고 412개 content가 회원 ID를 참조한다. KBoard 권한을 Members로 옮기지 않는다. KBoard를 제거하기 전까지는 기존 owner와 Members on/off 호환성만 확인하며, KBoard 권한 parity·content migration은 수행하지 않는다. Device-limit는 Core authenticate/wp_login에 붙어 있으므로 로그인 완료 순서·거부 결과를 보존하는 통합 harness가 필수다.

잔존 Cosmosfarm restriction: 10601 instructor-dashboard(value=1), 10987 partners_new(value=2), 11278 campus-partners(value=2). role meta도 남아 있다. 메뉴 9298/10608/10609의 WP-Members `in` 표시 계약을 포함해 page별 현재 보호 주체를 확인해야 한다. 단순히 restriction meta가 있다는 이유로 현재 보호된다고 보장하지 않는다.

## 6. 가장 작은 1.0

| 기능 | 우선순위 | 선택 이유 |
| --- | --- | --- |
| 로그인/로그아웃, safe redirect, 기존 username/email login | MVP_REQUIRED | LMS·checkout 공통 진입 |
| 가입, 중복 이메일 거부, 이름·표시명·전화·동의 검증 | MVP_REQUIRED | 제품 기본 기능. 공개 노출은 D01 gate |
| 분실/reset 및 현재 비밀번호 확인 후 변경 | MVP_REQUIRED | Core reset 계약 유지 |
| profile·이름·표시명·휴대폰 편집 | MVP_REQUIRED | 현재 실제 필드; 사용자 ID·role 편집 제외 |
| 약관/개인정보 동의 기록 | MVP_REQUIRED | 새 versioned 증거, 기존 동의는 소급 조작 금지 |
| 탈퇴 요청·로그인 차단·세션 철회, 관리자 처리 상태 | MVP_REQUIRED | 곧바로 전체 삭제하지 않는 최소 안전 기능 |
| 최소 로그인 audit, route rate limiting, 최소 관리자 설정 | MVP_REQUIRED | 인증 공격 대응·운영 가능성 |
| Woo/LMS URL·사용자 ID·device-limit 호환 | MVP_REQUIRED | 강결합 없이 기존 기능 유지 |
| 이메일 가입 인증 | MVP_OPTIONAL | 현재 꺼져 있음; 필요 정책이면 release gate 승격 |
| 가입 후 자동 로그인 | MVP_OPTIONAL | 현재 저장 설정과 다르므로 정책 고지; 기본 off |
| 기존 소개(description) 편집 | MVP_OPTIONAL | LMS 화면 있으나 populated 0명 |
| 프로필 이메일 셀프 변경 | FUTURE | 1.0은 표시 전용, 안전한 재검증 flow 완성 후 제공 |
| 이메일/SMS verification OTP | FUTURE | 소유 확인 요구가 생길 때만 |
| TOTP 2FA + recovery code | FUTURE | 사용할 때 recovery는 함께 필수; trusted device는 더 나중 |
| SocialProviderInterface 상세·Google 첫 구현 | FUTURE | 1.0은 문서상 경계만, 미사용 provider skeleton도 생성하지 않음 |
| Kakao/Naver/Apple | FUTURE | 실제 수요와 검증 가능한 provider 계약 후 |
| 자동 개인정보 익명화·완전삭제 | UNKNOWN | D02 보존·연동 정책 확정 필요 |
| 마케팅 동의 UI·신규 display_name 유일성 | UNKNOWN | 수집 목적/고유 nickname 정책 D03/D04 |
| 범용 유료회원/정기결제/쿠폰/쪽지/대량문자/자동등업/페이지 접근 엔진/본인인증 | REMOVE | 현재 회원 MVP에 불필요, 다른 domain과 중복 |

기존 전화가 없는 계정을 일괄 차단하지 않는다. 신규 필수 전화 정책은 self-asserted 연락처이며 인증된 휴대폰 또는 본인인증 증거가 아니다.

## 7. Fork 판정

**GREENFIELD_RECOMMENDED**. 동작·데이터 호환을 재사용하고 legacy 코드를 복사하지 않는 D를 선택한다. 실제 필요한 LOC 비율은 구현 범위가 미확정이고 정적 파일 크기로 판단할 수 없어 수치화하지 않았다. 아래 “적음/많음”은 모듈 적합도에 관한 정성 판단이다.

| 평가 기준 | A WP-Members fork | B Cosmosfarm fork | C 일부 코드 Hybrid | D Core 기반 신규 |
| --- | --- | --- | --- | --- |
| 필요한 코드 / 불필요 코드 | 폼·Core bridge 유용 / restriction·products·legacy 많음 | 한국형 UI 일부 유용 / billing·SMS·social·알림 많음 | 잘라낼 경계와 출처 검증 필요 | 필요한 workflow만 구현 |
| PHP session | 직접 session_start 미발견 | 일반 frontend session 시작 | 혼입 차단 필요 | 설계상 사용 금지 |
| bootstrap / 전역 CSS·JS | 전역 객체·CSS | 전역 include·객체·skin assets | 잘라내도 hook 잔존 위험 | route 중심 load |
| 보안 유지보수 | 기존 폼/legacy 경로까지 책임 | 탈퇴/OTP 등 추가 검토 큼 | 상호작용까지 책임 | 작은 공격면, 신규 구현 검증 필수 |
| Core 중복 | 이미 Core 사용, UX 중복 정리 필요 | WP-Members 위 확장 layer 중복 | 두 layer 잔존 위험 | Core API에 얇은 adapter |
| usermeta 호환 / migration | 기존 필드 읽기 유리 | WP-Members 함께 필요 | legacy adapter 유리 | 명시적 mapping 필요, ID migration 없음 |
| email / OTP / 2FA 확장 | reset/form hook 통합 필요 | 기존 인증 구현과 분리 필요 | 출처별 저장소 복잡 | 독립 검증 상태 machine |
| Social 확장 | 추가 필요 | 기존 provider 많으나 안전성 재검토 | provider별 조건 이식 | 문서 경계부터 최소 확장 |
| Woo / LMS / Community | generic integration 조정 | 강한 WPMEM 의존 제거 필요 | 계약 혼재 | WP ID·URL public facade |
| 테스트 부담 | upstream 전체 영향 범위 | 넓은 부가기능 조합 | 원본+수정 조합 | 새 행동 harness부터 필요 |
| upstream 업데이트 | fork diff 지속 관리 | vendor 변경과 로컬 보정 추적 | 복사 코드 patch 수동 추적 | WP/Woo public API 변화 추적 |
| 라이선스 영향 | 로컬 GPLv3 표기 확인, 재사용 전 준수 검토 | 로컬 전체 재배포 허용 범위 UNKNOWN | 복사 부분별 provenance 확인 필요 | legacy 소스 복사 없음; 신규 배포 license 별도 확정 |
| 장기 유지보수 | 범용 제품 책임을 떠안음 | 부가 domain까지 떠안을 위험 | 구조적 절충 비용 | 작은 제품 경계에 가장 적합 |

구현 시간이 무조건 적다는 주장은 하지 않는다. 새 인증 UX도 취약해질 수 있으므로 behavior/security harness 통과가 전제다. 로컬 탈퇴 조건식은 nonce 존재와 검증을 OR로 연결하고 있어 보안 재검토 사유다(E09); 비활성 reference에서 악용 가능성을 시험하지 않았다.

## 8. USER_DECISION_REQUIRED

| ID | 결정 | 기본 설계 제안 / 결정이 필요한 시점 |
| --- | --- | --- |
| D01 | 공개 가입을 열지, 전화 필수 여부, 이메일 인증 필수화, 자동 로그인 | 공개 가입은 현재 닫힘 유지. 구현은 가능, 활성화 직전 결정 |
| D02 | 탈퇴 비활성화·복구 가능성·개인정보 삭제 범위·Woo/LMS/정산/게시물 보존 기간 | 즉시 로그인 차단 후 관리 처리. 법적 기간 임의 확정 금지; 운영 탈퇴 전 결정 |
| D03 | 마케팅 수집 목적·문구·채널·철회 | 현행 명시적 증거 없으므로 기본 수집 안 함 |
| D04 | display_name 중복 금지 지속 여부 | nickname은 identity 아님. 1.0 제안은 중복 허용, 기존 이름 변경 안 함; UI 확정 전 결정 |
| D05 | 과거 계정의 email state와 재동의 조건 | legacy_unknown 유지, 전원 강제 차단/검증 완료 처리 금지 |
| D06 | restriction 3페이지·메뉴 3개의 소유자와 현재 비활성 상태가 의도인지 | 정상 clone baseline와 기대 계약을 분리 기록; 전환 시작 gate |
| D07 | 최소 지원 WP/PHP/Woo 버전·multisite | 우선 single-site, 로컬 버전은 관찰값이지 배포 지원 범위 아님; 테스트 환경 확정 시 결정 |

Phase 0 문서 작성은 위 답변 없이 완료 가능하다. 미확정 정책을 구현 중 임의로 운영에 적용하지 않는다.
