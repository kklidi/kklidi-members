# Registration fields

`AUTH-REGISTER-FIELDS-001` 상태: **SPECIFIED_NOT_IMPLEMENTED**

대상 버전: **0.7.18**

이 문서는 회원가입 필드 설정의 범위와 안전 경계를 소유한다. 실행 가능한 manifest는 `tests/harness/registration_fields_contract.json`이다. 0.7.17 runtime은 아직 이 설정을 읽지 않으며, 아래 기본값과 같은 고정 폼을 사용한다.

## 1. 목적

관리자는 회원가입 화면에서 실제로 필요한 기본 정보만 받을 수 있어야 한다. 이 기능은 범용 form builder가 아니다. 미리 승인한 내장 필드의 상태만 바꾸며, 임의의 meta key·HTML·PHP·shortcode·파일 업로드 필드를 만들지 않는다.

“추가”는 숨긴 내장 필드를 다시 표시하는 것을, “제거”는 해당 내장 필드를 가입 화면과 가입 POST 처리에서 제외하는 것을 뜻한다. 기존 사용자의 저장값을 생성·수정·삭제하는 작업은 아니다.

## 2. 필드 정책

| 필드 | 0.7.18 기본값 | 관리자 변경 | 저장·처리 책임 |
| --- | --- | --- | --- |
| 이메일 | 필수 | 잠금 | WordPress `user_email`; 로그인 식별 UI |
| 비밀번호 | 필수 | 잠금 | WordPress Core password API; 원문 별도 저장 금지 |
| 비밀번호 확인 | 필수 | 잠금 | 같은 요청에서 비교 후 폐기 |
| 표시명 | 필수 | 잠금 | WordPress `display_name`; 중복 허용 |
| 이름 | 필수 | 필수 / 선택 / 숨김 | WordPress `first_name` |
| 성 | 선택 | 필수 / 선택 / 숨김 | WordPress `last_name` |
| 전화 | 선택 | 필수 / 선택 / 숨김 | 1.0 `billing_phone` 호환 adapter; 인증된 전화로 간주하지 않음 |
| 서비스 약관 동의 | 필수 | 잠금 | 현재 문서 version/hash를 Members consent event로 저장 |
| 개인정보 처리방침 동의 | 필수 | 잠금 | 현재 문서 version/hash를 Members consent event로 저장 |
| 마케팅 동의 | 게시된 문서가 있을 때만 선택 | 이 계약에서 변경 불가 | 별도 목적·문서 정책에 따름 |

이름·성·전화의 상태 변경만 허용한다. 필드 순서와 source label은 고정하며 label은 영어 gettext source와 WordPress locale 번역 catalog로 제공한다. 문구 사용자 정의는 `AUTH-MESSAGE-UX-001`의 별도 범위다.

## 3. 관리자 설정

- `Users → KKLIDI Members → Registration`에서 WordPress Settings API를 사용한다.
- `manage_kklidi_members` capability와 Settings API nonce를 모두 요구한다.
- 단일 non-autoload option `kklidi_members_registration_fields`에 schema version과 세 필드 상태만 저장한다.
- option이 없거나 읽을 수 없으면 0.7.17과 같은 기본값을 사용한다.
- 허용하지 않은 field/state가 포함된 저장 요청은 전체를 거부하고 마지막 유효 설정을 유지한다.
- 설정 변경 audit에는 변경한 필드명과 이전/새 상태만 기록하며 회원 입력값을 기록하지 않는다.

## 4. 가입 요청 처리

화면에서 숨겼다는 사실만 신뢰하지 않는다. server allowlist가 현재 설정을 읽고 visible/required 상태를 다시 판정한다.

- 필수 필드는 서버에서도 빈값과 field별 형식을 검증한다.
- 선택 필드는 값이 있을 때만 같은 sanitizer와 길이 제한을 적용한다.
- 숨김 필드는 HTML에 렌더하지 않고 같은 이름의 POST 값이 주입되어도 저장하지 않는다.
- role, user ID, account state, verified state와 임의 meta key는 클라이언트 입력을 받지 않는다. 신규 role은 계속 `subscriber`다.
- 검증 오류 뒤에는 현재 표시 중인 안전한 text 값만 같은 요청에서 복원한다. password, password confirmation, nonce, guest token은 항상 비운다.
- 가입 공개 여부는 계속 Core `users_can_register`와 필수 문서 준비 상태만 결정한다.
- 성공 후 자동 로그인과 이메일 인증은 추가하지 않는다.

## 5. 변경 영향

설정은 다음 가입 요청부터 적용한다. 기존 WordPress 사용자 ID, 이름·성·표시명·전화, role, 동의 event를 다시 쓰지 않는다. 숨긴 전화나 이름을 기존 profile에서 삭제하지 않으며 0.7.18은 profile 화면의 필드 구성을 바꾸지 않는다.

전화는 승인된 1.0 compatibility adapter를 유지한다. WooCommerce 과거 주문 연락처를 변경하거나 checkout 필드를 소유하지 않는다. LMS의 profile·수강·진도·수료증 데이터도 조회하거나 변경하지 않는다.

## 6. 구현 합격 기준

1. option이 없는 신규 설치와 0.7.17 업데이트에서 현재 폼·필수/선택 동작이 그대로다.
2. 이름·성·전화의 세 상태 조합을 관리자와 일반 회원 권한으로 검증한다.
3. 숨김 field POST 주입, role/user ID/meta 주입, 잘못된 schema/state가 저장이나 권한 상승을 만들지 않는다.
4. 필수/선택 validation, 안전한 오류 복원, 접근성 연결과 한국어 gettext catalog를 검증한다.
5. `wp_`와 임의 prefix에서 같은 WordPress ID·Core auth·동의·중복 방지 계약을 유지한다.
6. Members 비활성 시 Core/Woo/LMS가 fatal 없이 동작하고 설정 option이 다른 domain 데이터를 변경하지 않는다.

## 7. 제외 범위

임의 custom field, meta key 지정, drag-and-drop 순서 변경, custom label/help text, 조건부/역할별 폼, 파일 업로드, 관리자 승인, 이메일·SMS 인증, social login, 자동 로그인은 포함하지 않는다. 필요하면 각각 별도 behavior contract와 개인정보·보안 검토를 거친다.
