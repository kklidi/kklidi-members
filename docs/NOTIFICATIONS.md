# 계정 알림 behavior contract

이 문서는 Phase 0 이후 승인된 사용자 계정 알림 범위를 고정한다. 기존 Phase 0의 identity, security, migration, domain ownership 계약을 바꾸지 않는다. 충돌이 생기면 `PRODUCT.md`, `ARCHITECTURE.md`, `SECURITY.md`, `MIGRATION.md`의 기존 경계를 우선한다.

| 항목 | 값 |
| --- | --- |
| Contract ID | `AUTH-NOTIFY-001` |
| 계약 상태 | **SPECIFIED** |
| Runtime 상태 | **IMPLEMENTED_AND_SYNTHETIC_VERIFIED** |
| 구현 단계 | P0-2 |
| 승인 범위 | 가입 완료, 비밀번호 변경, 탈퇴 접수, 탈퇴 처리 완료의 사용자 안내 |

## 1. 알림 사건

| 사건 | 성공 조건과 발송 시점 | 수신자 | 최소 내용 |
| --- | --- | --- | --- |
| `registration_completed` | 필수 동의와 계정 상태가 저장되고 `registration_pending → active`가 확정된 뒤 | 해당 WordPress 사용자의 현재 `user_email` | 사이트명, 가입 완료, 로그인 또는 계정 URL |
| `password_changed` | WordPress Core 비밀번호 변경과 기존 세션 철회가 모두 성공한 뒤 | 해당 WordPress 사용자의 현재 `user_email` | 사이트명, 비밀번호 변경 사실, 본인이 아닌 경우 사용할 Core 복구 경로 |
| `withdrawal_requested` | `active → withdrawal_pending` 저장과 접근·세션 철회가 성공한 뒤 | 해당 WordPress 사용자의 현재 `user_email` | 탈퇴 접수, 로그인 차단, 관리자와 domain owner의 수동 처리 안내 |
| `withdrawal_finalized` | 관리자가 `withdrawal_pending → disabled`를 확정한 뒤 | 해당 WordPress 사용자의 현재 `user_email` | 처리 상태, 로그인 차단 유지, 보존 정책에 따른 Core ID와 주문·학습 참조 유지 가능성 |

상태 변경이 거부되거나 중간 저장이 실패한 요청에는 성공 알림을 만들지 않는다. 알림은 상태 변경의 원인이 아니며, 메일 성공을 인증·가입·탈퇴의 승인 조건으로 사용하지 않는다.

## 2. 전달·보안 규칙

1. P0-2의 전송 경계는 WordPress `wp_mail()`이다. 본문은 고정된 `text/plain` preset으로 시작하고 발신자와 reply-to는 WordPress 기본 메일 설정을 따른다. Members가 SMTP 또는 외부 provider 설정을 소유하지 않는다.
2. 수신 주소는 사건 처리 후 WordPress Core의 현재 사용자 레코드에서 다시 읽는다. 요청 body의 이메일이나 외부 도메인의 이메일을 신뢰하지 않는다.
3. 비밀번호, reset key, 인증 cookie, nonce, 사용자 ID, role, 원문 동의 증거를 제목·본문·header에 넣지 않는다. 주문·결제와 LMS 수강·진도·수료증 데이터도 넣지 않는다.
4. 사용자에게 보이는 source string은 영어 gettext와 `kklidi-members` text domain을 사용한다. P0-3에서 사용자 locale을 우선하고 사이트 locale을 fallback으로 하는 한국어 PO/MO catalog를 검증한다.
5. 논리 알림 키는 `event_type + event_id`다. 같은 등록 또는 상태 전이 요청의 재실행은 논리 알림을 중복 생성하지 않아야 한다. Queue가 없는 단계에서는 외부 전달의 exactly-once를 주장하지 않는다.
6. 알림은 최종 보안 상태가 저장된 뒤 발생한다. `wp_mail()` 성공은 WordPress가 발송 요청을 수락했다는 뜻이며 외부 mailbox 전달 완료로 표현하지 않는다. `wp_mail()` 실패로 계정 상태, 세션 철회, 비밀번호 변경을 rollback하지 않고 최소 감사 사건만 남긴다. 실패 주입, 사용자 응답, 재시도 여부의 세부 계약은 P0-4에서 확정한다.
7. 전역 frontend bootstrap, 일반 GET hook, 무조건적인 CSS/JS 또는 provider SDK 로딩을 추가하지 않는다. 알림 코드는 위 네 사건의 성공 경로에서만 로딩한다.

## 3. Domain 소유권과 제외 범위

WooCommerce 주문·결제·환불 메일은 WooCommerce가 소유한다. LMS 수강·진도·수료증·질문 알림은 LMS가 소유한다. Members가 꺼져도 두 플러그인이 Members class나 함수 부재로 fatal을 내면 안 된다. KBoard/Community 메일도 Members로 옮기지 않는다.

이번 계약에는 이메일 가입 인증, 이메일 주소 변경 인증, OTP, 2FA, 관리자 수신 알림, 마케팅 캠페인, 편집 가능한 템플릿, 미리보기·시험 발송, 재시도 queue, 전달 이력 UI, SMTP provider 설정이 포함되지 않는다.

## 4. 후속 구현 합격 기준

- **P0-2 — 완료:** 네 사건만 실제 성공 경로에서 발송한다. `wp_`와 임의 prefix의 합성 WordPress에서 잘못된 상태·실패·중복 요청에 추가 알림이 없고, 현재 Core 이메일·금지 정보·WordPress ID 보존·Members 비활성 fallback이 유지됨을 검증했다.
- **P0-3:** 모든 신규 사용자 문구가 영어 gettext source와 한국어 PO/MO로 제공되며 사용자 locale과 사이트 fallback에서 올바르게 렌더링되는지 검증한다.
- **P0-4:** `wp_mail()` 실패를 주입해 보안 상태가 유지되고 성공 전달로 오인되지 않는지 검증한다. 재시도 queue 또는 운영 UI는 별도 승인 전 구현하지 않는다.
