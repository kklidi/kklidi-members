# Administrator registration notification

`AUTH-ADMIN-NOTIFY-001` 상태: **IMPLEMENTED_AND_SYNTHETIC_VERIFIED**

대상 버전: **0.7.20**

이 문서는 신규 회원가입이 완료됐을 때 사이트 관리자에게 보내는 선택 알림만 소유한다. 사용자 계정 알림은 `NOTIFICATIONS.md`, 공개 가입 여부는 WordPress Core `users_can_register`, 계정 승인·차단은 기존 계정 상태 계약이 계속 소유한다. 실행 가능한 manifest는 `tests/harness/admin_notification_contract.json`이다.

## 1. 관리자 결정과 기본값

`Users → KKLIDI Members → Notifications`에 “신규 회원가입 관리자 알림” checkbox를 둔다. 설치·업데이트 기본값은 꺼짐이다. 관리자가 명시적으로 켠 뒤 완료되는 가입부터 적용하며, 과거 가입을 소급 발송하지 않는다.

설정은 WordPress Settings API와 `manage_kklidi_members` capability를 사용한다. versioned non-autoload option `kklidi_members_admin_notifications`에는 `registration_enabled` boolean만 저장한다. 관리자 이메일 주소는 Members option이나 요청값에 저장하지 않고 발송 시 WordPress Core `admin_email`을 다시 읽는다. 주소 변경은 WordPress 일반 설정이 소유한다.

## 2. 발송 계약

필수 동의 저장과 `registration_pending → active` 전환이 확정된 뒤, 가입 요청 ID당 논리적으로 한 번만 `wp_mail()`을 호출한다. 본문은 plain text이며 사이트 locale의 gettext를 사용한다.

포함 내용은 사이트명, 회원 표시명, 회원 이메일, 가입 완료 UTC 시각이다. 비밀번호, reset key, 인증 cookie, nonce, WordPress 사용자 ID, role, 전화, 동의 원문·hash, WooCommerce 주문, LMS 수강·진도·수료 데이터는 제목·본문·header에 넣지 않는다.

`admin_email`이 유효하지 않거나 `wp_mail()`이 false를 반환해도 이미 완료된 가입과 사용자 응답을 rollback하지 않는다. 외부 전달의 exactly-once를 주장하지 않고 자동 재시도도 하지 않는다. 성공·실패는 기존 최소 감사 테이블의 `mail_admin_registration` event에 recipient나 본문 원문 없이 기록한다.

## 3. 경계

이 checkbox는 관리자 승인제가 아니다. 가입을 `registration_pending`에 보류하거나 관리자가 승인해야 로그인할 수 있게 만들지 않는다. 여러 수신자, 사용자 정의 관리자 주소·문구, HTML/WYSIWYG, 발신자·SMTP/provider, 시험 발송, delivery log와 retry queue는 포함하지 않는다.

WooCommerce 주문 메일, LMS 학습 메일과 KBoard 알림은 각 플러그인이 계속 소유한다. Members 비활성화가 다른 플러그인의 가입·로그인·메일 경로에 fatal을 만들면 안 된다.

## 4. 합격 기준

1. 초기값이 꺼짐이고 option이 autoload되지 않는다.
2. 관리자만 Settings API nonce로 checkbox를 변경할 수 있으며 다른 key나 주소는 저장되지 않는다.
3. 꺼짐에서는 관리자 메일이 없고, 켜짐에서는 활성 가입 완료 후 Core `admin_email`에 plain-text 메일 한 건이 추가된다.
4. 재실행은 같은 가입 요청의 관리자 알림을 중복 발송하지 않는다.
5. 잘못된 수신 주소와 `wp_mail()` 실패가 가입·로그인 가능 상태·사용자 알림을 rollback하지 않는다.
6. 메일과 감사에 금지 정보가 없고, frontend 일반 요청에 설정·메일 class 또는 새 자산을 로드하지 않는다.

2026-09-10 합성 실행 `b83fd4753406440a874f0e50e55d0860`에서 기본/임의 DB prefix 모두 기본 꺼짐, 관리자 Settings API, custom recipient 거부, Core `admin_email`, 활성 가입 뒤 사용자·관리자 메일 분리, 중복 방지, invalid recipient와 `wp_mail()` 실패 감사, 가입 상태 보존, 합성 사용자와 root 정리를 PASS했다. 같은 실행의 일반 요청 성능 budget과 무자산 경계도 PASS했다.
