# Messages

`AUTH-MESSAGE-UX-001` 상태: **SPECIFIED_NOT_IMPLEMENTED**

대상 버전: **0.7.19**

이 문서는 Members가 사용자에게 표시하는 기본 안내·성공·오류 문구를 관리자가 확인하는 방식과 수정 가능 범위를 소유한다. 실행 가능한 manifest는 `tests/harness/message_ux_contract.json`이다.

## 1. 결정

Members 관리자 화면에 읽기 전용 기본 메시지 catalog를 제공한다. catalog는 실제 PHP의 영어 gettext source와 현재 WordPress 관리자 사용자 locale의 번역 결과를 보여준다. 별도 메시지 option이나 전역 message filter를 만들지 않는다.

로그인 실패, 계정 존재 여부를 감추는 가입·reset 문구, CSRF와 rate limit 문구는 보안 계약이므로 관리자 편집을 허용하지 않는다. 사이트별 표현이 필요한 네 계정 이메일은 기존 Notifications 화면에서 plain-text 제목과 본문만 계속 수정한다.

## 2. 관리자 화면

`Users → KKLIDI Members → Messages`에 다음 그룹을 읽기 전용으로 표시한다.

| 그룹 | 대표 상태 |
| --- | --- |
| 계정 안내 | 가입 완료, 비밀번호 변경, reset 완료, 탈퇴 요청 접수 |
| 인증 | 일반 credential 실패, login rate limit |
| 회원가입 | 공개 가입 닫힘, 입력 오류, 중복·실패 일반 응답 |
| 비밀번호 재설정 | 존재 여부를 감추는 요청 응답, 잘못되거나 만료된 링크 |
| 프로필 | 저장 성공, 저장 실패 |
| 동의 | 저장 성공, 필수 동의 저장 실패 |
| 탈퇴 | 요청 저장 실패 |

각 행은 안정적인 message key, 유형과 현재 번역 문구를 표시한다. key는 API가 아니며 다른 플러그인이 문자열을 바꾸는 public extension point로 사용하지 않는다.

## 3. 이메일 기본값 표시

Notifications 화면의 각 승인 사건에서 현재 번역된 기본 제목과 기본 본문을 입력란 아래에 표시한다. 입력란은 계속 override만 저장한다.

- override가 비어 있으면 발송 시 수신자 locale의 gettext 기본값을 사용한다.
- 관리자 화면의 preview는 현재 관리자 locale 설명이며 실제 발송이나 시험 발송이 아니다.
- 기존 option schema, 허용 placeholder, plain-text 형식, 수신자와 `wp_mail()` transport는 변경하지 않는다.
- HTML/WYSIWYG, sender, SMTP/provider, retry와 delivery log는 포함하지 않는다.

## 4. 비밀번호 변경 완료 안내

현재 비밀번호 변경 성공은 Core password 변경과 기존 session 철회 후 로그인 화면으로 이동한다. 0.7.19는 이 redirect에 비밀이 없는 `password_changed=1` 상태만 전달하고 “비밀번호가 변경되었으니 다시 로그인” 안내를 표시한다. password, reset key, user ID, email은 URL에 넣지 않으며 자동 로그인하지 않는다.

## 5. 합격 기준

1. 관리자만 Messages catalog를 열 수 있고 일반 회원은 관리자 화면을 볼 수 없다.
2. catalog의 모든 key가 승인 manifest에 있으며 현재 gettext 번역을 사용한다.
3. 보안 관련 문구를 저장·수정하는 form과 option이 없다.
4. Notifications 화면은 네 사건의 번역 기본 제목·본문을 보여주며 기존 override 저장과 fallback을 그대로 유지한다.
5. 비밀번호 변경 성공 뒤 일반 상태값만 가진 로그인 URL로 이동하고 재로그인을 요구한다.
6. frontend 일반 요청에 catalog class, 관리자 자산이나 새로운 전역 filter를 로드하지 않는다.

## 6. 제외 범위

관리자 신규 가입 알림은 `AUTH-ADMIN-NOTIFY-001`에서 별도로 다룬다. HTML 이메일과 template layout, 전체 frontend 문구 편집, WooCommerce·LMS·KBoard 문구는 포함하지 않는다.
