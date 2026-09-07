# Migration · Roadmap

이 문서는 소유권 전환·실패 복구·완료 gate의 기준이다. 데이터 mapping은 ARCHITECTURE, 미결정 정책은 PRODUCT §8, 보안 상태는 SECURITY를 참조한다. 이 계획은 실행하지 않았다.

## 1. 실제 시작점

reference에는 Cosmosfarm/WP-Members의 설정·페이지·데이터가 남아 있지만 두 플러그인은 현재 `active_plugins`에 없다. 사용자 설명과 로컬 상태의 차이를 D06으로 기록한다. 현재 reference를 고치거나 재활성화해서 “정상 상태”를 만들지 않는다.

후속 단계에서 **reference와 별도 경로·DB·메일 sink를 가진 테스트 환경**을 마련한다. 실회원 데이터 복제 없이 합성 fixture를 기본으로 하고 필요한 관찰 shape/count만 반영한다. 실제 익명화된 복제가 필요하면 원본과 목적을 명시한 별도 작업으로 수행한다. 기존 hash/credential/token을 테스트 저장소에 복사하지 않는다.

두 baseline을 구분한다. B0는 관찰된 비활성 구성(잔존 shortcode를 포함), B1은 정책상 기대하는 회원 UX다. legacy 활성 동작의 비교가 필요하면 라이선스와 격리 조건을 확인한 clone에서만 두 플러그인을 켠다. 실제 관찰되지 않은 B1을 “현재 정상 동작”으로 기록하지 않는다. 원본 로그인·메일·checkout을 호출해 baseline을 수집하지 않는다.

## 2. 변경 불변 조건

- users.ID/user_login, Woo customer ID/order ID, LMS enrollment/progress/certificate/question/activity 참조를 바꾸지 않는다. 동일 사용자에게 신규 user ID를 만들지 않는다.
- 계정 이메일 일치만으로 Woo guest 주문이나 social identity를 자동 claim/link하지 않는다.
- 이미 보관된 동의 빈값·누락을 agree로 채우지 않으며 과거 시각/약관 버전을 만들어내지 않는다.
- legacy meta/table 삭제는 최종 cleanup까지 하지 않는다. Members uninstall도 Core 사용자·Woo/LMS 데이터를 삭제하지 않는다.
- login/register/reset/profile은 각각 **단일 owner**를 가진다. 서로 다른 플러그인이 같은 POST·redirect·메일·cookie를 이중 처리하지 않게 한다.
- rollout은 명시적 route/cohort 설정으로 수행한다. global login_url 필터와 실제 form POST owner가 서로 어긋나지 않게 한다. 호환 shim은 일반 init에서 legacy plugin 전체를 load하는 방식이 아니다.

## 3. 일곱 migration phase

| Phase | 작업과 owner 변경 | 진입/완료 gate | Rollback |
| --- | --- | --- | --- |
| 1 Behavior 고정 | B0/B1, page·shortcode·redirect·필드·제한·메일 계약 기록; synthetic fixture | D01/D06 확인, identity baseline와 Harness 기대값 고정, reference 분리 | 문서/fixture만 바꾸며 서비스 변화 없음 |
| 2 병행 설치 | 격리 환경에 Members 설치, 기본 route owner는 기존 상태, shadow read만 허용 | global session/assets 없음; 설치 후 users/meta/orders/LMS가 의도치 않게 바뀌지 않음 | Members 기능 flag off; tables는 보존. 현재 reference에는 설치하지 않음 |
| 3 login/register/reset/profile 전환 | login→reset→profile→register 순서로 개별 전환. legacy shortcode를 새 화면으로 매핑하거나 page 내용 변경은 clone에서 별도 배포 | 각 AUTH 통과, 기존 cookie·username·checkout 복귀·한글 이름·동의 확인; inactive 상태의 우발적 form 노출 방지 | endpoint owner/page mapping만 직전 검증 버전으로 복귀. 신규 계정/동의/주문을 과거 DB로 덮지 않음 |
| 4 Cosmosfarm 책임 제거 | redirect·자동 로그인·탈퇴·약관·감사·restriction 각 owner 이전 | 제한 3페이지의 domain guard, 메뉴 3개, KBoard 제거 전 login/no-fatal 호환성, Woo field 의미 검증. KBoard 권한 엔진 이전은 하지 않음. 새 로그 single writer | 검증된 adapter별 책임 복귀. 과거 위험한 탈퇴 코드를 rollback 기본으로 켜지 않음 |
| 5 WP-Members form/field 책임 제거 | publish shortcode·필드 validator·reset link·menu 설정의 대체 완료 | legacy 함수/shortcode 직접 의존 없음; 과거 reset link 만료 구간 처리; 신규 field writer 일원화 | 기존 URL 유지 shim으로 대응; schema additive 유지 |
| 6 기존 플러그인 비활성화 | 실제 활성인 대상 환경에서만 Cosmosfarm 먼저, 다음 WP-Members. 비활성 snapshot에서는 제거할 책임을 검증하는 no-op gate | Core login·LMS·Woo·KBoard 제거 전 호환성·privacy 시나리오 통과. KBoard 권한 parity는 대상이 아니며, 둘 중 하나만 켜진 조합도 fatal 검사 | 사전 검증된 정상 이전 stack/route owner로 복귀. reference의 현재 off 상태를 임의 on으로 바꾸지 않음 |
| 7 legacy cleanup | hook/option/meta/table 사용처와 보존 승인 후 범위별 정리 | D02 승인, 일정 관찰 기간(제안 2주+최소 실제 주문/복구 1회) 동안 사건 없음; reader 0; 보관·복원 검증 | 필요한 legacy export만 제한 접근 보관, 범위 복원. user ID migration은 없음 |

비활성→정상화 작업과 활성 운영 사이트→교체 작업은 시작점이 다르다. Phase 숫자는 책임 제거 순서이며 모든 환경에 동일 activation 조작을 실행하는 스크립트가 아니다.

## 4. URL·field·정책 소유권

| 현재 대상 | 새 책임 | 유지/주의 |
| --- | --- | --- |
| page 2813 login | Members Auth | 기존 bookmark 유지, safe redirect precedence로 변경 |
| page 50 sign-in | Members Registration | slug가 로그인처럼 보여도 실제 register. users_can_register 정책 먼저 확인 |
| page 56 profile/reset | Members Profile/Password | 과거 query/reset link가 있으면 호환 기간과 expiry 처리 |
| pages 42/43 | UNKNOWN | bracket shortcode 없음. 실제 layout/외부 link 확인 전 삭제/alias 금지 |
| page 35 Woo My Account | Woo 주문·주소, Members 공통 profile link | order/download/payment endpoint를 덮어쓰지 않음 |
| page 34 checkout | Woo checkout + 활성 WCI redirect | Members는 login URL/안전한 return target만 제공 |
| LMS 강의실 profile tab | Members 활성 시 공통 URL로 위임 | 비활성 시 기존 LMS/Core fallback, 인증서 verified name은 LMS |
| billing_phone | Members self-phone adapter + Woo customer API | 과거 주문 phone 불변, phone_number conflict 자동 해결 금지 |
| restriction pages/메뉴 | 해당 page를 소유한 서비스의 권한 + 테마/메뉴 표시 | UI 숨김만으로 권한 보호했다고 간주하지 않음 |
| device-limit | 기존 device-limit plugin | authenticate 거부·wp_login 후속 조치 보존; 자체 장치 인증 복제 없음 |

## 5. 데이터 전환 절차와 실패 복구

1. 새 schema는 additive로 설치한다. 설치 전 사용 중인 prefix와 users table을 API로 확인하고 non-default prefix 테스트를 통과한다. 일반 frontend에서 자동 upgrade를 실행하지 않는다.
2. 사용자 값은 기존 API/key를 읽는다. 1.0 전화는 billing_phone을 그대로 사용하므로 전화 일괄 migration이 없다. 과거 policy agree만 version/time unknown인 legacy event로 선택 import한다.
3. 동의 import는 `legacy:<site>:<user_id>:<consent_type>`를 안정적 논리 키로 사용하고, schema의 `char(36)` 제약에 맞춰 그 키에서 결정론적 UUID를 생성해 멱등 처리한다. batch cursor·처리/skip/error 수를 기록한다. 386개라는 snapshot 수를 운영 DB의 강제 기대값으로 쓰지 않고 실행 직전 집계를 비교한다. 원본 meta는 그대로 둔다.
4. 반영 전 dry-run report와 source counts, 반영 후 Core IDs·key 값·domain foreign reference·중복 event 여부를 검증한다. phone conflict와 billing_who는 미해결 queue에 남긴다.
5. 새 계정/동의 저장 부분 실패는 pending 상태에서 같은 요청을 재개한다. consent 실패 후 role·cookie를 먼저 부여하지 않는다. 외부 hooks/mail은 transaction rollback이 되지 않으므로 중복 송신을 따로 방지한다.

Rollback은 schema/route/settings별로 한다. 전환 후 새 주문·progress·새 회원이 생겼는데 전체 DB backup을 복원하면 정상 업무가 사라지므로 일반 rollback 방법으로 사용하지 않는다. 신규 필수 동의/보안 상태를 legacy에서 집행할 수 없다면 무조건 재활성화하지 않고 가입·민감 mutation을 일시 차단한 복구 화면으로 전환한다. 사이트 전체 유지보수 모드가 기본 해법은 아니다.

탈퇴 차단 계정이나 미래 2FA가 생긴 후 Members 제거는 추가 gate가 필요하다. Core fallback만으로 그 정책이 유지되지 않으므로 동등 guard를 검증한 후 소유권을 넘긴다. 운영 장애 시의 관리자 복구는 테스트한 별도 절차를 갖추며 누구나 접근하는 bypass URL을 만들지 않는다.

## 6. 최대 다섯 단계 Roadmap

이 roadmap은 위 일곱 migration phase를 구현 작업으로 묶은 것이다. 기간·성능 개선 수치는 미측정이므로 확정하지 않는다. 아래 모델은 이 세션에서 사용 가능하며 공식 문서에서 reasoning 지원을 확인한 `gpt-5.5`를 일관되게 추천한다. 최고/최신 모델이라는 주장이 아니다. high는 보안·상태 경계의 복잡성에 따른 작업별 제안이며 결과 검증을 대신하지 않는다. [GPT-5.5 공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-5.5).

| 단계 | 목표 | 구현 범위 | 위험도 | 완료 조건 | 권장 모델 / 추론 |
| --- | --- | --- | --- | --- | --- |
| 1 | 검증 가능한 baseline 확립 | 격리 WP fixture/harness, B0/B1·필드·redirect·권한 기대값; runtime 이전 작업 | 중 | AUTH-LOGIN-001의 실행·관찰 구조와 prefix/메일 sink 검증, D01/D06/D07 기록 | GPT-5.5 / high |
| 2 | 작은 Core 계정 UX 제공 | 최소 bootstrap/Auth/Password/Profile/Frontend/Admin, safe URL와 limiter; Core/DL/Woo 호환 | 높음 | login/logout/reset/profile·CSRF/IDOR/rate/asset harness 통과, owner가 하나 | GPT-5.5 / high |
| 3 | 가입·동의·안전한 탈퇴 완성 | Registration/Consent/Audit/Withdrawal, 동의 2-table schema, pending/idempotency | 높음 | 동시 가입·동의 저장 실패·세션 철회·탈퇴 요청 통과, D02와 문구 확정 | GPT-5.5 / high |
| 4 | 1.0 전환·성능 검증 | migration 2~7의 단계 전환, LMS/Woo/KBoard/제한 페이지, rollback, 성능 budget 확정 | 높음 | 모든 MVP harness와 zero-ID-change, 안전한 rollback·관찰 기간 gate 통과 | GPT-5.5 / high |
| 5 | 필요 기반 인증 확장 | 수요가 확정된 이메일 검증부터; 이후 TOTP+recovery 또는 Google 1개만 독립 release | 높음 | 해당 FUTURE harness가 필수 gate로 승격, 우회/복구/도메인 연동 검증 | GPT-5.5 / high (문서·단순 UI는 medium) |

**다음 구현 단계에서 가장 먼저 할 작업 1개:** reference와 분리된 합성 데이터 WordPress 테스트 환경에 `AUTH-LOGIN-001`을 실행할 최소 behavior harness를 만든다.
