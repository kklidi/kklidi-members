# 계정 알림 behavior contract

이 문서는 Phase 0 이후 승인된 사용자 계정 알림 범위를 고정한다. 기존 Phase 0의 identity, security, migration, domain ownership 계약을 바꾸지 않는다. 충돌이 생기면 `PRODUCT.md`, `ARCHITECTURE.md`, `SECURITY.md`, `MIGRATION.md`의 기존 경계를 우선한다.

| 항목 | 값 |
| --- | --- |
| Contract ID | `AUTH-NOTIFY-001` |
| 계약 상태 | **SPECIFIED** |
| Runtime 상태 | **IMPLEMENTED_AND_SYNTHETIC_VERIFIED** |
| 구현 단계 | P0-4 |
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

1. 전송 경계는 WordPress `wp_mail()`이다. 본문은 `text/plain` preset이며 0.7.29의 선택적 Members 발신자·footer 설정은 Members가 소유한 호출에만 적용한다. Members가 SMTP 또는 외부 provider 설정을 소유하지 않는다.
2. 수신 주소는 사건 처리 후 WordPress Core의 현재 사용자 레코드에서 다시 읽는다. 요청 body의 이메일이나 외부 도메인의 이메일을 신뢰하지 않는다.
3. 비밀번호, reset key, 인증 cookie, nonce, 사용자 ID, role, 원문 동의 증거를 제목·본문·header에 넣지 않는다. 주문·결제와 LMS 수강·진도·수료증 데이터도 넣지 않는다.
4. 사용자에게 보이는 source string은 영어 gettext와 `kklidi-members` text domain을 사용한다. 사용자 locale을 우선하고 사이트 locale을 fallback으로 하는 한국어 PO/MO catalog를 사용한다.
5. 논리 알림 키는 `event_type + event_id`다. 같은 등록 또는 상태 전이 요청의 재실행은 논리 알림을 중복 생성하지 않아야 한다. Queue가 없는 단계에서는 외부 전달의 exactly-once를 주장하지 않는다.
6. 알림은 최종 보안 상태가 저장된 뒤 발생한다. `wp_mail()` 성공은 WordPress가 발송 요청을 수락했다는 뜻이며 외부 mailbox 전달 완료로 표현하지 않는다. `wp_mail()` 실패로 계정 상태, 세션 철회, 비밀번호 변경을 rollback하지 않으며 이미 확정된 작업의 성공 응답도 실패로 바꾸지 않는다. 실패 시 감사 결과는 `failure/wp_mail_failed`이고 성공 전달 기록을 남기지 않는다. 자동 재시도는 0회다.
7. 전역 frontend bootstrap, 일반 GET hook, 무조건적인 CSS/JS 또는 provider SDK 로딩을 추가하지 않는다. 알림 코드는 위 네 사건의 성공 경로에서만 로딩한다.

## 3. Domain 소유권과 제외 범위

WooCommerce 주문·결제·환불 메일은 WooCommerce가 소유한다. LMS 수강·진도·수료증·질문 알림은 LMS가 소유한다. Members가 꺼져도 두 플러그인이 Members class나 함수 부재로 fatal을 내면 안 된다. KBoard/Community 메일도 Members로 옮기지 않는다.

이번 계약에는 이메일 가입 인증, 이메일 주소 변경 인증, OTP, 2FA, 관리자 수신 알림, 마케팅 캠페인, 편집 가능한 템플릿, 미리보기·시험 발송, 재시도 queue, 전달 이력 UI, SMTP provider 설정이 포함되지 않는다.

## 4. 후속 구현 합격 기준

- **P0-2 — 완료:** 네 사건만 실제 성공 경로에서 발송한다. `wp_`와 임의 prefix의 합성 WordPress에서 잘못된 상태·실패·중복 요청에 추가 알림이 없고, 현재 Core 이메일·금지 정보·WordPress ID 보존·Members 비활성 fallback이 유지됨을 검증했다.
- **P0-3 — 완료:** 12개 신규 메일 msgid를 영어 POT와 한국어 PO/MO로 제공하고, 합성 WordPress의 `ko_KR` 사이트 fallback 및 사용자 locale 전환에서 네 가지 알림 preset이 한국어로 렌더링됨을 `bacdd413b3444dd694baa26d725e7e9a` 실행으로 `wp_`/비기본 prefix 각각 검증했다.
- **P0-4 — 완료:** 릴리스 실행 `aed831b84fe140708b6346e244a2190c`에서 `wp_`와 비기본 prefix 각각 네 실제 계정 경로에 `wp_mail()` 실패를 주입했다. 가입 활성 상태·필수 동의, 변경 비밀번호·전 세션 철회, 탈퇴 접수 상태·접근 차단, 최종 비활성 상태가 모두 유지됐고 작업 성공 응답도 유지됐다. 각 prefix에서 실패 주입은 정확히 4회였고 감사 결과는 정확히 4건의 `failure/wp_mail_failed`, 전달 sink 기록과 자동 재시도는 0건이었다. 재시도 queue 또는 운영 UI는 구현하지 않았다.
- **0.7.4 회귀 — 완료:** 실행 `5886351d4d39439993fae700b0cb610a`에서 같은 두 prefix와 네 성공/실패 알림 경계를 다시 PASS했다. 0.7.4의 `AUTH-UX-003`은 알림 template 편집, SMTP, 재시도 queue 또는 관리자 수신 알림을 추가하지 않는다.

## 5. AUTH-NOTIFY-002 — Core 우선 알림 문구 설정

| 항목 | 값 |
| --- | --- |
| Contract ID | `AUTH-NOTIFY-002` |
| 계약 상태 | **IMPLEMENTED_AND_SYNTHETIC_VERIFIED** |
| 목표 릴리스 | `0.7.10` |
| 선행 계약 | `AUTH-NOTIFY-001` |
| 승인 범위 | 기존 네 사건의 plain-text 제목과 본문을 관리자 설정으로 덮어쓰기 |

이 계약은 `AUTH-NOTIFY-001`의 사건, 수신자, 성공 후 발송, 중복 방지, 실패 처리 및 domain 소유권을 변경하지 않는다. 0.7.10 runtime과 단위 guard를 구현했고 합성 WordPress의 Settings API 저장·권한·fallback·메일 회귀를 검증했다.

### 5.1 관리자와 저장 계약

1. 설정 화면은 WordPress Users 하위 Members 관리자 정보 구조의 `알림` section에 둔다. 저장은 WordPress Settings API를 사용하며 `manage_kklidi_members` capability와 서버 nonce 검증을 모두 요구한다.
2. 관리자는 네 사건별 제목과 본문만 편집할 수 있다. 사건별 발송 중지, 수신자 변경, HTML/WYSIWYG, 미리보기와 시험 발송은 포함하지 않는다.
3. 설정은 custom table 없이 `wp_options`의 단일 versioned option `kklidi_members_notification_templates`에 저장하고 autoload하지 않는다. 누락·빈 값·손상·검증 실패가 있으면 해당 필드만 기존 gettext preset으로 되돌린다.
4. 제목은 최대 200자 단일 text, 본문은 최대 5,000자 plain text다. raw HTML, shortcode, PHP와 허용 목록 밖 placeholder는 거부한다. 감사 기록에는 변경 주체·시각·성공/실패 같은 metadata만 남기며 제목과 본문 원문은 기록하지 않는다.

### 5.2 허용 placeholder

| 사건 | 허용 placeholder |
| --- | --- |
| `registration_completed` | `{site_name}`, `{login_url}` |
| `password_changed` | `{site_name}`, `{password_reset_url}` |
| `withdrawal_requested` | `{site_name}` |
| `withdrawal_finalized` | `{site_name}` |

비밀번호, reset key, nonce, 인증 cookie, WordPress 사용자 ID, role, 주문·결제 및 LMS 데이터는 저장하거나 치환하지 않는다. 알려지지 않은 placeholder를 조용히 삭제하지 않고 저장을 거부한다.

### 5.3 WordPress Core와 전달 계층 경계

1. 전송 API와 형식은 계속 `wp_mail()`과 `text/plain`이다. Members 발신자 설정이 켜진 경우에도 승인된 Members 호출의 `From` header에만 적용하며 Core와 다른 plugin의 메일은 기존 정책을 따른다.
2. Members는 전역 `wp_mail_from`/`wp_mail_from_name` filter, SMTP 설정, provider credential, 외부 이메일 API, queue, 재시도, webhook 또는 전달 이력을 소유하지 않는다. 사이트가 SMTP plugin, Elastic Email 같은 provider 또는 managed transport를 도입해도 이 계약의 작성·치환 계층은 바뀌지 않는다.
3. WordPress Core 비밀번호 재설정 메일은 Core 소유로 유지한다. Members의 `password_changed` 안내만 이 설정 범위에 포함하며 Core reset 메일의 제목·본문을 가로채지 않는다.
4. 저장된 문구는 사이트별 plain text override다. override가 없을 때 영어 gettext 원문과 사용자 locale 우선·사이트 locale fallback의 번역 catalog를 그대로 사용한다.

실행 가능한 설계 manifest는 `tests/harness/notification_settings_contract.json`이다. 합성 실행 `d28853b554c5497eb50df18d7f24dffe`는 `wp_`와 임의 prefix에서 Settings API nonce·capability, non-autoload 저장, 허용 placeholder 치환, 미허용 placeholder 원자적 거부, 빈 값 gettext fallback, 문구 원문을 남기지 않는 감사와 기존 네 메일·실패 경계를 PASS했다. 실제 mailbox 전달 판정과 운영 메일 provider 설정은 배포 환경의 별도 책임이다.

## 6. AUTH-MAIL-SENDER-001 — 후속 발신자 확장 계약

`AUTH-NOTIFY-002`의 현재 runtime은 계속 사이트 기본 발신자를 사용한다. 사용자가 승인한 후속 `AUTH-MAIL-SENDER-001`은 기본 꺼짐의 발신 이름·주소와 plain-text footer를 Members 소유 메일에만 추가한다. 전역 sender filter, SMTP/provider credential, HTML, Core reset과 Woo/LMS/KBoard 메일은 범위 밖이다.

상세 정책과 보안·시험 발송 합격 기준은 `MAIL_SENDER_POLICY.md`, 실행 가능한 manifest는 `tests/harness/mail_sender_contract.json`이 소유한다. 0.7.29에서 Settings API 저장·권한·header injection·Members 메일 범위·시험 발송 실패/limit 합성 검증까지 완료했으며, 실제 mailbox 도착과 SPF/DKIM/DMARC 정렬은 운영 배포 gate다.
