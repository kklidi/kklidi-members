# AUTH-IDENTITY-002 — 이메일 중심 신규 계정과 기존 아이디 호환

| 항목 | 값 |
| --- | --- |
| Contract ID | `AUTH-IDENTITY-002` |
| 계약 상태 | **IMPLEMENTED_AND_SYNTHETIC_VERIFIED** |
| 목표 릴리스 | `0.7.28` |
| 선행 계약 | `AUTH-LOGIN-001`, `AUTH-REGISTER-001/002`, `AUTH-RESET-001`, `AUTH-REGISTER-FIELDS-001` |
| 원칙 | 신규 회원은 이메일 중심 UI, 기존 WordPress 아이디는 호환 유지 |

## 1. 제품 정책

1. 신규 회원가입 화면은 별도 아이디를 입력받지 않는다. 이메일은 필수이며 동일 정규화 이메일의 중복 가입은 기존 직렬화·재검사 계약으로 거부한다.
2. WordPress Core가 요구하는 `user_login`은 Members가 충돌 없는 비공개 후보로 생성한다. 이 값은 권한, 공개 닉네임 또는 이메일 변경의 동기화 대상이 아니다.
3. 공개될 수 있는 WordPress `user_nicename`은 내부 `user_login`과 다른 독립된 unique slug로 생성한다. 작성자 URL이나 REST 응답이 내부 로그인 값을 간접 노출하지 않아야 한다.
4. 표시명은 WordPress `display_name` 기반의 공개 닉네임이다. 로그인 식별자가 아니며 중복을 허용한다.
5. 신규 회원에게 안내하는 기본 로그인 수단은 이메일이다. 로그인과 비밀번호 찾기 화면의 기본 label은 `이메일`, 보조 안내는 `기존 회원은 기존 아이디로도 이용할 수 있습니다.`로 한다.
6. 기존 WordPress 계정은 현재 `user_login`과 사용자 ID를 그대로 유지한다. 기존 아이디와 현재 이메일 로그인 모두 계속 Core 인증 경로로 처리한다.
7. 프로필의 이메일은 현재 계약처럼 읽기 전용이다. 미래 이메일 변경 기능이 추가되어도 `user_login`을 변경하지 않는다.

## 2. WordPress Core와 보안 경계

- 인증은 계속 `wp_signon()`, 비밀번호 찾기는 Core `retrieve_password()`와 Core reset key API를 사용한다.
- Members는 별도 비밀번호 저장소, 인증 cookie, PHP session, JWT 사용자 session 또는 사용자 ID 매핑을 만들지 않는다.
- 비공개 `user_login`은 화면·메일·감사 기록과 공개 `user_nicename`에 새로 노출하지 않는다. 로그인 성공 여부와 무관하게 공개 오류는 계정 존재 여부를 구분하지 않는다.
- 기존 username 입력을 지원하더라도 rate limit, device-limit 및 다른 Core `authenticate` hook을 우회하지 않는다.
- 신규 입력에서 role, capability, user ID, `user_login`, account state와 verified state를 받지 않는다.
- 이메일 정규화·중복 검사·가입 lock은 기존 `AUTH-REGISTER-002`를 유지하며, 기존 사용자 병합이나 새 ID 재발급을 하지 않는다.

## 3. 구현 합격 기준

1. 신규 가입 form과 POST allowlist에는 username 필드가 없다.
2. 신규 계정은 충돌 없는 내부 `user_login`으로 생성되고 그 값이 이메일·표시명과 독립적이다.
3. 신규 `user_nicename`은 내부 `user_login`과 다르며 공개 경로에서 내부 로그인을 역으로 알 수 없다.
4. 신규 계정은 이메일과 비밀번호로 로그인할 수 있다.
5. 기존 `user_login != user_email` 계정은 기존 아이디와 이메일 모두 로그인할 수 있다.
6. 로그인·비밀번호 찾기 화면은 이메일을 주 label로 표시하고 기존 아이디 호환을 보조 문구로 정확히 안내한다.
7. 존재·부재 이메일/아이디에 대한 공개 오류와 rate-limit 경계가 동일하다.
8. 이메일 또는 표시명 변경이 기존 user ID와 `user_login`을 바꾸지 않는다.
9. Members 비활성화 시 기존 WordPress 계정과 Core 로그인 경로가 fatal 없이 남는다.

## 4. 범위 밖

사용자 지정 신규 아이디, 아이디 변경, 이메일 변경, 이메일 소유 확인, 자동 로그인, 2FA, 소셜 로그인, 계정 병합, 기존 `user_login` migration은 이 계약에 포함하지 않는다.

실행 가능한 manifest는 `tests/harness/identity_policy_contract.json`이다. 0.7.28 runtime은 신규 가입 username 미수집, 독립 공개 slug, 이메일 주 label, 기존 아이디 호환과 Core 인증 경계를 구현했다. 합성 WordPress 반복 실행이 완료되어도 실제 staging browser acceptance는 별도 배포 gate다.
