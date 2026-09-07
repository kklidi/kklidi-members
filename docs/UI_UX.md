# UI/UX behavior contract

이 문서는 Members 화면의 상태·표현·접근성·자산 로딩 계약을 소유한다. 인증과 데이터 상태 전이는 `SECURITY.md`, 제품 범위는 `PRODUCT.md`, 모듈과 route 경계는 `ARCHITECTURE.md`가 우선한다.

## 1. 계약 상태

- 계약 ID: `AUTH-UI-001`
- 상태: **SPECIFIED**
- 다음 구현 계약: `AUTH-UI-002`
- 범위: 로그인, 가입, 계정 홈, 프로필, 비밀번호 변경, 동의, 탈퇴 요청, 로그아웃 확인, Members 관리자 화면

`AUTH-UI-001`은 화면 구현 전에 사용자에게 보이는 상태와 완료 기준을 고정한다. 현재 템플릿이 HTTP에서 렌더링된 사실만으로 이 계약이 구현되었다고 판정하지 않는다. CSS 적용, 반응형 브라우저 검증, 키보드 조작 검증은 `AUTH-UI-002`에서 수행한다.

`AUTH-UI-002`는 2026-09-07에 구현했다. 공통 frontend stylesheet, 관리자 전용 stylesheet, 8개 frontend page shell, route 전용 asset hook을 추가했으며 JavaScript는 추가하지 않았다. MAMP sandbox에서 가입·로그인 오류·로그인 회원의 6개 계정 화면·관리자 화면을 확인했다. 이 smoke는 화면 구조·자산 격리·반응형·focus의 증거이며, 모든 보안 상태 전이의 UI 회귀는 기존 MVP behavior harness와 후속 통합 gate가 계속 소유한다.

## 2. 공통 원칙

1. WordPress Core가 identity, password, authentication, auth cookie와 session token을 계속 소유한다.
2. 화면은 서버 렌더링을 기본으로 하며 JavaScript가 없어도 핵심 제출과 오류 복구가 가능해야 한다.
3. PHP source string은 영어와 `kklidi-members` text domain을 사용한다. 한국어는 PO/MO 번역 파일에서 제공한다.
4. 회원 화면은 Members route에서만 frontend 자산을 읽는다. 일반 글, LMS 화면, WooCommerce 화면에는 Members CSS/JS를 전역 enqueue하지 않는다.
5. 외부 font, CDN, analytics, provider 요청을 화면 렌더링의 전제로 두지 않는다.
6. label과 control의 관계, 키보드 focus, 오류와 상태의 의미, 모바일 reflow를 시각 구현보다 먼저 보존한다.
7. 보안 결정은 화면의 숨김 상태에 의존하지 않는다. nonce, capability, 현재 사용자, field allowlist는 서버에서 다시 검증한다.

## 3. 화면과 상태

| 화면 | 접근 대상 | 필수 상태 | 사용자 행동과 결과 |
| --- | --- | --- | --- |
| 로그인 | 비회원 | 기본, 필수값 누락, 요청 검증 실패, 일반 credential 실패, rate limit, device exchange 필요, 가입 완료/탈퇴 요청 안내 | username 또는 email과 password로 Core 로그인한다. 오류는 계정 존재 여부를 노출하지 않고, 안전한 로컬 목적지만 유지한다. |
| 가입 | 비회원 | 가입 닫힘, 문서 준비 안 됨, 입력 오류, 필수 동의 누락, 중복·경합의 공통 오류, 저장 재시도, 성공 | email을 Core `user_login`으로 사용하는 신규 회원을 만들되 role·user ID를 입력받지 않는다. 성공 후 자동 로그인하지 않고 로그인 화면으로 이동한다. |
| 계정 홈 | 비회원, 회원 | 비회원 진입, 로그인 상태, 탈퇴 요청 완료 안내 | 비회원은 로그인 진입을, 회원은 프로필·비밀번호·동의·탈퇴·로그아웃 동선을 본다. Woo 주문과 LMS 학습 정보는 이 화면이 소유하지 않는다. |
| 프로필 | 회원 | 비회원 redirect, 기본, 검증 오류, 저장 오류, 저장 성공 | email은 읽기 전용이다. 이름, 성, 표시명, 전화의 허용 필드만 현재 WordPress user ID에 저장한다. |
| 비밀번호 | 회원 | 비회원 redirect, 기본, nonce 오류, 현재 비밀번호 오류, 길이·확인 오류, 성공 | 현재 비밀번호를 다시 확인하고 Core password를 변경한다. 성공 후 기존 session을 철회하고 다시 로그인하게 한다. |
| 동의 | 회원 | 비회원 redirect, 필수 문서 없음, 기본, 필수 동의 누락, 저장 오류, 저장 성공 | 공개된 문서의 version/hash/snapshot에 대해 필수 동의를 기록한다. 선택 마케팅 동의는 체크와 철회를 모두 명시적으로 처리한다. |
| 탈퇴 요청 | 회원 | 비회원 redirect, 일반 회원 기본, 관리자 수동 검토 안내, nonce 오류, 현재 비밀번호 오류, 저장 오류, 요청 완료 | 즉시 user ID를 삭제하지 않는다. 요청을 저장하고 계정을 차단하며 Core session을 철회한 뒤 로그아웃한다. |
| 로그아웃 | 비회원, 회원 | 비회원 redirect, 확인, nonce 오류, 완료 | GET은 확인 화면만 보여준다. nonce가 있는 POST에서 Core logout을 실행하고 안전한 로컬 목적지로 이동한다. |
| 관리자 | `manage_kklidi_members` capability 보유자 | 접근 거부, 설정 기본/저장 완료, 탈퇴 queue 빈 상태/목록, audit 빈 상태/목록 | 공개 가입과 route 소유 설정을 관리하고 탈퇴 요청과 최소 audit을 검토한다. nonce만으로 capability 검사를 대신하지 않는다. |

## 4. 화면 구조와 접근성

- frontend 화면은 공통 page shell, 제목, 설명, 본문, 상태 메시지, 주요 action 순서를 사용한다.
- form control에는 프로그램적으로 연결된 label이 있어야 한다. 필수 여부와 자동완성 목적을 markup으로 제공한다.
- validation 오류는 색상만으로 구분하지 않고 `role="alert"` 또는 동등한 연결 구조로 읽을 수 있어야 한다. 저장 완료 안내는 `role="status"` 또는 동등한 구조를 사용한다.
- 키보드 focus는 항상 보이고 DOM 순서는 시각 순서와 일치해야 한다. modal이나 custom keyboard widget은 이 MVP에 도입하지 않는다.
- 좁은 화면에서 가로 스크롤 없이 단일 열로 reflow한다. 입력과 주요 button은 touch 조작 가능한 크기를 확보한다.
- 탈퇴 action은 일반 계정 action과 시각적으로 분리하고 결과를 설명한다. 사용자 ID가 즉시 삭제된다는 문구를 사용하지 않는다.
- 관리자 표는 작은 화면에서도 행의 의미를 잃지 않게 제목 또는 데이터 label을 제공한다.

## 5. 자산 계약

- `AUTH-UI-002`는 공통 frontend stylesheet 한 개를 기본으로 한다. Members route가 실제로 렌더링될 때만 enqueue한다.
- JavaScript는 서버 렌더링으로 충족할 수 없는 동작이 생길 때만 추가한다. 추가 시에도 해당 Members route에서만 읽는다.
- 관리자 자산은 Members 관리자 화면의 hook suffix에서만 읽는다.
- theme 전역 reset이나 Woo/LMS/KBoard selector를 덮는 규칙을 만들지 않는다.
- 일반 frontend의 Members CSS/JS/외부 요청 0이라는 `AUTH-PERF-002` 계약을 유지한다.

## 6. 번역 계약

- 사용자와 관리자에게 보이는 모든 고정 문구는 gettext 대상이다.
- 영어 msgid를 PHP에 두고 한국어는 `languages/kklidi-members-ko_KR.po`와 `.mo`에서 제공한다.
- 관리자가 입력한 약관·개인정보 문서 본문은 사이트 데이터이므로 번역 파일로 대체하거나 자동 번역하지 않는다.
- 번역 때문에 label, action, 오류의 의미가 달라지거나 security detail이 추가 노출되어서는 안 된다.

## 7. AUTH-UI-002 완료 기준

1. 이 문서와 `tests/harness/ui_contract.json`의 9개 화면이 모두 구현되어 있다.
2. guest, member, administrator가 각 화면의 기본·오류·완료 상태를 브라우저에서 확인할 수 있다.
3. 360px 수준의 좁은 viewport와 desktop에서 잘림, 겹침, 불필요한 가로 스크롤이 없다.
4. keyboard만으로 처음부터 제출 또는 취소까지 이동할 수 있고 focus가 보인다.
5. 한국어 locale에서 source PHP 하드코딩 없이 번역이 적용된다.
6. Members 화면에서만 필요한 자산이 로드되고 일반 페이지에서는 Members 자산과 외부 요청이 0이다.
7. 기존 인증·가입·프로필·동의·탈퇴·관리자 behavior contract가 계속 통과한다.

## 8. 범위 밖

- site theme 전체 redesign과 page builder 통합
- WooCommerce 주문/결제 화면 및 LMS 학습 화면 UI
- email verification, 2FA, social login
- KBoard 권한 엔진, 권한 parity, content migration
- animation, modal, client-side form framework, 외부 design system
