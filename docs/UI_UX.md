# UI/UX behavior contract

이 문서는 Members 화면의 상태·표현·접근성·자산 로딩 계약을 소유한다. 인증과 데이터 상태 전이는 `SECURITY.md`, 제품 범위는 `PRODUCT.md`, 모듈과 route 경계는 `ARCHITECTURE.md`가 우선한다.

## 1. 계약 상태

- 계약 ID: `AUTH-UI-001`
- `AUTH-UI-001` 상태: **SPECIFIED**
- `AUTH-UI-002` 상태: **IMPLEMENTED_AND_VERIFIED**
- `AUTH-UX-003` 상태: **0.7.8_WITHDRAWAL_AUDIT_OPERATIONS_IMPLEMENTED**
- 범위: 로그인, 가입, 계정 홈, 프로필, 비밀번호 변경, 동의, 탈퇴 요청, 로그아웃 확인, Members 관리자 화면

`AUTH-UI-001`은 화면 구현 전에 사용자에게 보이는 상태와 완료 기준을 고정한다. 현재 템플릿이 HTTP에서 렌더링된 사실만으로 이 계약이 구현되었다고 판정하지 않는다. CSS 적용, 반응형 브라우저 검증, 키보드 조작 검증은 `AUTH-UI-002`에서 수행한다.

`AUTH-UI-002`는 2026-09-07에 구현했다. 당시 공통 frontend stylesheet, 관리자 전용 stylesheet, 8개 frontend page shell, route 전용 asset hook을 추가했으며 JavaScript는 없었다. MAMP sandbox에서 가입·로그인 오류·로그인 회원의 6개 계정 화면·관리자 화면을 확인했고, 2026-09-09의 0.7.1 패키지를 Chrome 360px viewport에서 다시 확인해 한국어 번역 적용, route 전용 0.7.1 자산, focus 규칙과 가로 overflow 부재를 검증했다. 0.7.5는 로그인·가입 route 전용 password enhancement를, 0.7.6은 아홉 번째 frontend reset shell과 변경·reset route의 같은 enhancement를 추가했다. 후속 화면의 브라우저 회귀는 0.7.9 gate가 소유한다.

`AUTH-UX-003`은 0.7.4에서 승인한 UI·운영 구현의 전략 계약이다. 0.7.5의 로그인·회원가입, 0.7.6의 계정·재설정, 0.7.7의 관리자 정보 구조에 이어 0.7.8은 탈퇴 복구·확정과 상세 audit workflow를 구현했다. 0.7.9는 브라우저·접근성·release gate를 진행하며, Members 전용 글자 크기 기준은 별도 `AUTH-UX-004` 계약으로 고정한다. 0.7.17은 `AUTH-ADMIN-UX-001`으로 관리자 진단·빠른 작업·canonical route 링크와 운영 안내를 보강한다. 실행 가능한 전략 manifest는 `tests/harness/ux_strategy_contract.json`이고, 타이포그래피 계약은 `docs/TYPOGRAPHY.md`다.

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
| 가입 | 비회원 | 가입 닫힘, 문서 준비 안 됨, 입력 오류, 필수 동의 누락, 중복·경합의 공통 오류, 저장 재시도, 성공 | email 중심 UI를 제공하되 신규 Core `user_login`은 충돌 없는 비공개 후보로 생성하고 role·user ID를 입력받지 않는다. email 로그인과 기존 username 로그인을 모두 유지한다. 성공 후 자동 로그인하지 않고 로그인 화면으로 이동한다. |
| 계정 홈 | 비회원, 회원 | 비회원 진입, 로그인 상태, 탈퇴 요청 완료 안내 | 비회원은 로그인 진입을, 회원은 프로필·비밀번호·동의·탈퇴·로그아웃 동선을 본다. Woo 주문과 LMS 학습 정보는 이 화면이 소유하지 않는다. |
| 프로필 | 회원 | 비회원 redirect, 기본, 검증 오류, 저장 오류, 저장 성공 | email은 읽기 전용이다. 이름, 성, 표시명, 전화의 허용 필드만 현재 WordPress user ID에 저장한다. |
| 비밀번호 | 회원 | 비회원 redirect, 기본, nonce 오류, 현재 비밀번호 오류, 길이·확인 오류, 성공 | 현재 비밀번호를 다시 확인하고 Core password를 변경한다. 성공 후 기존 session을 철회하고 다시 로그인하게 한다. |
| 동의 | 회원 | 비회원 redirect, 필수 문서 없음, 기본, 필수 동의 누락, 저장 오류, 저장 성공 | 공개된 문서의 version/hash/snapshot에 대해 필수 동의를 기록한다. 선택 마케팅 동의는 체크와 철회를 모두 명시적으로 처리한다. |
| 탈퇴 요청 | 회원 | 비회원 redirect, 일반 회원 기본, 관리자 수동 검토 안내, nonce 오류, 현재 비밀번호 오류, 저장 오류, 요청 완료 | 즉시 user ID를 삭제하지 않는다. 요청을 저장하고 계정을 차단하며 Core session을 철회한 뒤 로그아웃한다. |
| 로그아웃 | 비회원, 회원 | 비회원 redirect, 확인, nonce 오류, 완료 | GET은 확인 화면만 보여준다. nonce가 있는 POST에서 Core logout을 실행하고 안전한 로컬 목적지로 이동한다. |
| 관리자 | `manage_kklidi_members` capability 보유자 | 접근 거부, 설정 기본/저장 완료, 탈퇴 queue 빈 상태/목록, audit 빈 상태/목록 | Core 공개 가입 상태와 필수 문서 전제조건을 안내하고 route 소유 설정을 관리하며 탈퇴 요청과 최소 audit을 검토한다. 공개 가입 자체는 WordPress 일반 설정이 소유한다. nonce만으로 capability 검사를 대신하지 않는다. |

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

## 8. AUTH-UX-003 · 0.7.4 전략 결정

### 8.1 회원 화면

- Members는 theme markup에 종속되지 않는 독립형 branded shell을 유지한다. 사이트명·로고·홈 링크 같은 최소 brand context만 WordPress 데이터에서 가져오고 외부 font·CDN을 요구하지 않는다.
- clean route의 기본 후보는 `/members/login/`, `/members/register/`, `/members/account/`와 account 하위 경로다. 기존 publish page·rewrite 충돌을 먼저 검사하고 관리자가 route map을 적용하기 전에는 활성화하지 않는다. 현재 query route는 항상 호환 fallback으로 유지한다.
- 로그인 화면은 비밀번호 찾기, 가입, 홈으로 돌아가기 동선을 제공한다. credential 오류는 계속 일반화하고 email/username 존재 여부를 노출하지 않는다.
- 0.7.17 가입 기본값은 email, password/confirmation, first name, display name, 서비스 약관과 개인정보 처리방침 동의가 필수이고 last name과 phone은 선택이다. `AUTH-REGISTER-FIELDS-001`은 0.7.18에도 이 기본값을 유지하면서 이름·성·전화만 필수/선택/숨김으로 설정하도록 지정한다. email·password·display name·필수 동의는 잠금이며 임의 custom field는 만들지 않는다. display name 중복은 허용하며 login identifier나 권한 판단에 사용하지 않는다.
- validation 실패 시 email·이름·표시명·전화 같은 안전한 같은-request 입력만 복원하고 password, nonce, guest token은 항상 비운다. 오류 요약과 field 연결 오류를 함께 제공한다.
- 약관은 현재 version을 표시하고 서버 렌더링 `<details>`와 전문 링크로 읽을 수 있게 한다. 동의 checkbox는 전문을 열지 않아도 키보드로 접근 가능해야 한다.
- password 표시/숨김은 route 전용의 작은 progressive-enhancement script와 입력 필드 안쪽의 눈 아이콘으로 제공한다. JavaScript가 없어도 제출·검증·복구가 모두 가능해야 하며 별도 password score를 인증 규칙으로 만들지 않는다.
- 가입 후 자동 로그인은 계속 하지 않는다. 로그인 화면의 완료 상태에서 다음 행동을 명확히 안내하고 password나 email을 URL에 넣지 않는다.
- 비밀번호 분실·reset의 branded 화면은 WordPress Core key 발급·검증·변경 API만 감싼다. 자체 token, password store, auth cookie를 만들지 않는다.
- WooCommerce와 LMS는 자신의 plugin이 등록하는 link-only navigation slot으로만 계정 홈에 진입점을 제공한다. Members가 주문·수강 데이터를 조회하거나 두 plugin의 존재를 필수로 만들지 않는다.

### 8.2 관리자 화면

- 운영 화면은 `사용자` 메뉴 아래 Members page와 overview, documents, withdrawals, audit의 네 구역을 기본 정보 구조로 한다. 기존 Tools URL은 변경 시 안전한 관리자 redirect만 제공한다.
- overview는 Core 공개 가입 상태, 필수 문서 준비, route 충돌, Members URL 소유권, 필요한 table, cleanup schedule을 읽기 전용으로 진단한다.
- 약관 화면은 현재 version/hash, 새 version 작성, 저장 전 preview, 이전 version 목록을 구분한다. 게시된 consent snapshot을 수정하거나 과거 동의 행을 다시 쓰지 않는다.
- 탈퇴 queue는 `withdrawal_pending`을 표시하고 capability·nonce·현재 상태를 다시 검사해 `disabled` 확정 또는 사유가 있는 `active` 복구만 허용한다. 어느 action도 Core user ID나 외부 domain 행을 삭제하지 않는다. 복구 후 기존 session은 되살리지 않고 다음 로그인에서 새 Core session을 발급한다.
- audit은 사람에게 읽히는 번역 label, event/result/date/user ID filter와 bounded pagination을 제공한다. raw credential, token, email 본문, IP 원문을 추가하지 않는다.
- 계정 알림은 고정 template과 감사 결과를 읽기 전용으로 보여준다. template 편집, SMTP 설정, 재시도 queue, 관리자 수신 알림은 이번 계약에 포함하지 않는다.
- Core Users 목록에는 account state와 현재 필수 consent 충족 여부만 admin 전용 column/filter로 연결한다. 별도 사용자 원장을 만들지 않는다.
- audit retention 기본값 30일/90일은 현황으로 표시하되 법적 운영 정책 승인 전 일반 설정으로 노출하지 않는다. 기본 capability는 administrator에만 부여하고 `manage_kklidi_members` 서버 검사를 모든 action에 유지한다.

### 8.3 구현 순서와 gate

1. 0.7.5: login/register shell, action links, safe input recovery, field errors, terms presentation, clean-route preflight.
2. 0.7.6: account/profile/consent/password UX, Core reset wrapper, plugin-owned navigation slots.
3. 0.7.7: 관리자 정보 구조, overview 진단, 약관 preview/history, Core Users columns.
4. 0.7.8: withdrawal 복구/확정 workflow와 audit filter/pagination/read-only notification result.
5. 0.7.9: MAMP desktop/mobile browser, keyboard, no-JS, route isolation, Members-off 회귀와 release gate.

각 단계는 기존 Core Auth·ID·domain ownership 계약을 그대로 통과해야 한다. 다음 단계 기능을 먼저 넣지 않는다.

## 9. 0.7.5 구현 상태

0.7.5는 8.3의 첫 번째 단계인 로그인·회원가입 UX를 구현했다.

- 독립형 서버 렌더링 shell, 사이트명·안내 문구·홈/가입/로그인/비밀번호 재설정 action link를 제공한다.
- 같은 요청에서 안전한 email·이름·표시명·전화 값만 복원하고 비밀번호·nonce·guest token은 복원하지 않는다.
- 일반 오류 요약과 field 오류를 `aria-invalid`/`aria-describedby`로 연결한다. 이메일·기존 username 로그인을 유지하며 credential 존재 여부는 노출하지 않는다.
- 서비스 약관·개인정보 처리방침·선택 마케팅 문서를 현재 version과 함께 `<details>`로 표시한다. 필수 동의는 서버에서 계속 검증한다.
- 비밀번호 표시/숨김은 로그인·회원가입 route에서만 로드되는 작은 progressive-enhancement JavaScript다. JavaScript가 없어도 제출·검증·오류 복구가 동작한다.
- `/members/` clean route 후보의 기존 페이지 충돌을 읽기 전용 preflight로 반환하고, 충돌 전에는 query route fallback을 유지한다. 이 릴리스는 clean route 소유권을 자동 활성화하지 않는다.

검증은 하네스 단위 계약 25개, 번역 포함 ZIP 빌드, 합성 WordPress 전체 회귀 및 MAMP lifecycle gate로 갱신한다. 실제 HTTPS staging의 backup/restore와 관찰 기간이 없는 한 production acceptance는 계속 `PARTIAL`이다.

## 10. 0.7.6 구현 상태

0.7.6은 8.3의 두 번째 단계를 구현한다.

- 계정 홈은 회원 소유 화면과 외부 plugin이 등록한 link-only 영역을 구분한다. 등록값은 라벨·로컬 URL·순서만 허용하며 Members는 Woo/LMS API나 데이터를 읽지 않는다.
- 프로필은 현재 사용자와 기존 allowlist만 수정하고, email read-only와 안전한 같은-request 값 복구, field 오류 연결을 제공한다.
- 동의 화면은 현재 document version, 서버 렌더링 전문, 필수 동의 오류 연결, 선택 동의 철회를 표시한다. 기존 snapshot이나 legacy 사건은 수정하지 않는다.
- 로그인 회원의 비밀번호 변경은 현재 비밀번호 확인, Core password 변경, 기존 Core session 철회와 재로그인을 유지하며 비밀번호 필드를 오류와 연결한다.
- 공개 재설정 화면은 `retrieve_password()`, `check_password_reset_key()`, `reset_password()`를 사용한다. 자체 token·password store·auth cookie·PHP session을 만들지 않고 계정 존재 여부와 무관한 요청 완료 문구를 사용한다. key 화면은 no-store/no-referrer다.
- route 전용 password enhancement는 변경·재설정 화면으로 확장되지만 JavaScript 없이 제출과 서버 검증이 동작한다.

단위 계약, PHP lint, 번역/package 검사를 이번 단계의 로컬 증거로 남긴다. MAMP/브라우저의 실제 메일 링크, 키보드, no-JS, 모바일 반복 검증은 계획된 0.7.9 gate이며 이 구현 완료 주장에 포함하지 않는다.

## 11. 0.7.7 구현 상태

0.7.7은 8.3의 세 번째 단계를 구현한다.

- 관리자 화면을 WordPress `사용자` 메뉴 아래로 옮기고 overview, documents, withdrawals, audit 구역을 분리했다. 기존 Tools URL은 권한을 확인한 뒤 새 로컬 URL로 이동한다.
- overview는 Core 공개 가입, 필수 문서, clean route 충돌, Members URL 소유권, 소유 table과 cleanup schedule을 읽기 전용으로 진단한다.
- 약관 작성은 저장 전 서버 렌더링 preview와 최대 20개 immutable snapshot history를 제공한다. preview는 option을 쓰지 않고 기존 snapshot과 consent row를 수정하지 않는다.
- Core Users 목록에는 권한 있는 관리자에게만 account state와 현재 필수 consent 상태 컬럼·필터를 추가한다. 별도 사용자 원장이나 Woo/LMS 데이터 조회는 없다.
- 관리자 stylesheet는 `users_page_kklidi-members`에서만 로드되며 작은 화면의 표는 각 셀 label을 유지한다.

탈퇴 pending→active 복구, 처리 사유, audit filter/pagination과 읽기 전용 알림 결과는 0.7.8 범위다. 브라우저 반복검증은 0.7.9에 수행한다.

## 12. 0.7.8 구현 상태

0.7.8은 8.3의 네 번째 단계를 구현한다.

- 탈퇴 queue는 현재 상태를 다시 확인하고 `withdrawal_pending→disabled` 확정 또는 500자 이하 사유가 있는 `withdrawal_pending→active` 복구만 허용한다.
- 두 처리 모두 기존 Core session과 application password를 다시 철회한다. 복구는 새 로그인에서만 새 Core session을 만들 수 있고, WordPress user ID나 Woo/LMS/KBoard 행을 삭제하지 않는다.
- 복구 사유 원문은 audit에 저장하지 않고 HMAC digest만 남긴다. 상태·event·result·reason code와 request ID만 기존 최소 audit 계약에 기록한다.
- audit 화면은 알려진 event와 result, UTC 날짜, WordPress user ID 필터와 페이지당 25건·최대 100페이지의 제한을 사용한다. 알림 사건은 성공/실패 결과만 읽기 전용으로 표시한다.
- audit retention 30일/90일 값은 현황으로만 보여주며 편집 설정, SMTP, 재시도 queue, 관리자 알림은 추가하지 않았다.

합성 WordPress 하네스는 복구 사유 필수, 이전 session 0, 복구와 확정 재실행의 멱등성, 네 audit 필터와 25건 page limit을 검사한다. 실제 키보드·no-JS·모바일·Members-off 화면 회귀는 0.7.9에 남는다.

## 13. 범위 밖

- site theme 전체 redesign과 page builder 통합
- WooCommerce 주문/결제 화면 및 LMS 학습 화면 UI
- email verification, 2FA, social login
- KBoard 권한 엔진, 권한 parity, content migration
- animation, modal, client-side form framework, 외부 design system

## 14. AUTH-UX-004 · 0.7.9 타이포그래피 계약

Members frontend의 본문은 16px, H1은 28~32px, H2는 20~22px, 도움말·오류는 14px, 약관 전문은 15px을 기준으로 한다. 일반 본문 줄간격은 1.6, 약관 전문은 1.7로 고정한다. 이 기준은 Members route-scoped stylesheet에만 적용하며 사이트 테마의 전역 typography나 LMS·WooCommerce·KBoard 화면을 변경하지 않는다. 세부 토큰과 제외 범위는 `docs/TYPOGRAPHY.md`를 따른다.

## 15. AUTH-ROUTE-MAP-001 · 0.7.21 route 연결 설계

로그인·회원가입·계정 화면은 WordPress 페이지나 shortcode를 자동 생성하지 않고 Members route controller가 직접 렌더링한다. 관리자가 충돌 검사를 통과한 뒤에만 고정 `/members/` clean route를 켤 수 있으며 기존 query route는 항상 호환 fallback으로 남는다. URL helper와 화면 template은 두 형식에서 동일하다.

메뉴는 관리자 화면에 표시된 대표 URL을 WordPress custom link로 수동 추가한다. Members는 기존 페이지·메뉴를 삭제하거나 고치지 않는다. clean route 기본값, 충돌 거부, Core login/register URL 소유권과 rollback의 상세 계약은 `ROUTE_MANAGEMENT.md`와 `tests/harness/route_management_contract.json`이 소유한다.

## 16. AUTH-UX-005 · 0.7.22 입력 컨트롤 계약

비밀번호 표시/숨김은 각 비밀번호 입력 필드의 오른쪽 안쪽에 눈 아이콘으로 제공한다. 아이콘은 route 전용 progressive enhancement이며 JavaScript가 꺼져도 입력·제출·서버 검증은 그대로 동작한다. `required`가 있는 입력은 라벨에 일관된 별표를 표시하고, 선택 입력은 기존 `Optional` 안내를 유지한다. 사용자 화면의 설명은 내부 인증 구현이나 저장 주체를 설명하지 않고 현재 행동과 다음 단계를 짧게 안내한다.

## 17. AUTH-UX-006 · 0.7.23 인증 화면 배치와 링크 계약

로그인과 비밀번호 찾기 화면은 짧은 폼에 맞춰 화면 중앙에 배치하고 카드 폭을 480px 이하로 제한한다. 로그인 화면에는 사이트명을 반복하는 상단 eyebrow를 표시하지 않는다. 로그인 하단 링크는 `회원가입 | 비밀번호 찾기 | 홈` 순서의 단일 행으로 같은 위계를 유지하며, 각 링크는 기존 Members 라우트 URL을 사용한다. 회원가입처럼 긴 화면은 세로 중앙 정렬을 강제하지 않는다.
