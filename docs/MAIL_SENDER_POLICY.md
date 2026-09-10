# AUTH-MAIL-SENDER-001 — Members 전용 발신자와 plain-text footer

| 항목 | 값 |
| --- | --- |
| Contract ID | `AUTH-MAIL-SENDER-001` |
| 계약 상태 | **IMPLEMENTED_AND_SYNTHETIC_VERIFIED** |
| 목표 릴리스 | `0.7.29` |
| 선행 계약 | `AUTH-NOTIFY-001/002`, `AUTH-ADMIN-NOTIFY-001` |
| 원칙 | WordPress `wp_mail()` 유지, Members가 소유한 메일에만 발신자 정책 적용 |

## 1. 관리자 설정

설정은 Users 하위 Members의 알림 section에서 WordPress Settings API로 관리한다. `manage_kklidi_members` capability와 서버 nonce를 요구하고 REST에 노출하지 않는다.

| 필드 | 기본값 | 검증 |
| --- | --- | --- |
| 사용자 정의 발신자 사용 | 꺼짐 | boolean allowlist |
| 발신 이름 | 빈 값 | plain text, 줄바꿈 금지, 최대 100자 |
| 발신 이메일 | 빈 값 | `is_email()`, CR/LF 금지, 최대 254자 |
| 발신 전용 footer 사용 | 꺼짐 | boolean allowlist |
| footer 문구 | gettext 기본 문구 | plain text, raw HTML/shortcode 금지, 최대 500자 |

설정은 `kklidi_members_mail_sender` 단일 versioned option에 non-autoload로 저장한다. 손상되거나 불완전한 발신자 설정은 활성화하지 않고 WordPress/사이트 기본 발신자로 되돌린다. footer는 발신자 사용 여부와 독립적으로 켜고 끌 수 있다.

## 2. 적용 범위

- 적용: Members의 가입 완료, 비밀번호 변경 완료, 탈퇴 요청, 탈퇴 처리 완료 사용자 알림과 opt-in 신규 가입 관리자 알림.
- 미적용: WordPress Core 비밀번호 재설정 메일, WooCommerce 주문·결제 메일, LMS 수강·진도·수료증 메일, KBoard 및 다른 플러그인의 메일.
- Members는 전역 `wp_mail_from` 또는 `wp_mail_from_name` filter를 등록하지 않는다. 승인된 Members `wp_mail()` 호출의 `From` header에만 설정을 적용한다.
- SMTP host, port, username, password, API key, provider credential, bounce 처리와 delivery webhook은 Members에 저장하지 않는다. 사이트 메일 전송 plugin 또는 관리형 인프라가 소유한다.
- v1 형식은 계속 `text/plain`이다. HTML/WYSIWYG 이메일은 별도 계약이다.

## 3. 발신 주소와 전달 정책

발신 주소는 사이트 운영자가 실제 소유하고 발송 권한을 설정한 도메인만 사용해야 한다. 예를 들어 `no-reply@kklidi.com`을 사용하려면 해당 도메인의 SPF·DKIM·DMARC와 실제 전송 계층 설정을 별도로 확인한다. 문법상 유효한 주소 저장이나 WordPress의 발송 요청 수락은 외부 mailbox 도착을 증명하지 않는다.

기본 footer gettext 문구는 다음 의미를 가진다.

> 본 메일은 발신 전용입니다. 문의가 필요한 경우 홈페이지의 고객지원 채널을 이용해 주세요.

v1은 임의 `Reply-To` 입력을 제공하지 않는다. 고객지원 주소 또는 URL을 footer에 넣는 정책은 개인정보처리방침·운영 채널 확정 후 별도 placeholder 계약으로 확장한다.

## 4. 실패·감사·시험 발송

1. `wp_mail()` 실패는 이미 완료된 가입·비밀번호 변경·탈퇴 상태를 rollback하지 않는다. 자동 재시도 queue도 만들지 않는다.
2. 감사에는 설정 변경 주체·시각·성공/실패와 메일 사건만 기록한다. 발신·수신 주소, 제목, 본문, footer 원문, credential은 기록하지 않는다.
3. 시험 발송은 별도 주소 입력을 받지 않고 현재 로그인한 관리자 자신의 Core `user_email`로만 보낸다. capability·nonce를 요구하고 관리자별 15분 3회로 제한한다.
4. 시험 결과는 `wp_mail()`이 요청을 수락했는지만 표시한다. 실제 inbox 도착을 주장하지 않는다.

## 5. 구현 합격 기준

1. 기본 설치와 기존 upgrade에서는 사용자 정의 발신자와 footer가 모두 꺼져 기존 발송 동작이 유지된다.
2. 유효한 설정은 Members 소유 메일에만 동일하게 적용된다.
3. CR/LF, invalid email, 지나치게 긴 이름/footer, HTML과 shortcode 입력은 원자적으로 거부되고 마지막 유효 설정이 유지된다.
4. Core reset, WooCommerce, LMS, KBoard 메일의 headers와 body가 바뀌지 않는다.
5. SMTP/provider가 없거나 발송이 실패해도 계정 상태 mutation은 보존되고 최소 실패 감사만 남는다.
6. Members 비활성화 시 전역 메일 filter나 callback이 남지 않는다.
7. 기본/비기본 DB prefix에서 non-autoload 저장, 권한·nonce 거부, 범위 분리와 실패 주입을 합성 WordPress 하네스로 검증한다.

실행 가능한 설계 manifest는 `tests/harness/mail_sender_contract.json`이다. 0.7.29 합성 하네스 실행 `2fb34a1a46b14894989c36e755b2dbd1`은 기본 및 임의 database prefix에서 설정 저장·권한·nonce·CR/LF 거부·Members 범위·시험 발송 실패와 rate limit을 검증했다. 격리 MAMP 메일 실행 `mamp-mail-sender-56dbd5af1df2`는 실제 WordPress runtime의 `wp_mail()` 수락과 sink header/body를 확인했다. 실제 mailbox 도착과 SPF/DKIM/DMARC 정렬은 배포 환경의 별도 gate다.
