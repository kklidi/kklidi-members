# kklidi-members

WordPress Core Auth 위에서 KKLIDI 서비스가 공유하는 회원·계정·인증 UX 계층.

**현재 배포 후보: 0.7.2 검증판.** 0.7.2는 0.7.1의 검증된 runtime을 유지하면서 Phase 0 문서의 역사적 snapshot과 현재 판정을 명확히 구분한다. 실제 운영 인증서·다중 서버·운영 migration 승인은 [0.7.2 릴리스 문서](docs/RELEASE-0.7.2.md)의 환경 gate를 따른다.

이전 검증 기록: **첫 MVP runtime 0.2.0 구현 및 24개 MVP 계약의 합성 WordPress 실행 완료**. 최신 합성 실행은 24개 MVP 계약이 모두 PASS다. 실제 device-limit 1.1.3의 Members/Core 허용·차단·제거 경로, WooCommerce 11.1.0/WCI 1.0.3의 checkout·cart·주문 귀속, KKLIDI LMS의 주문→수강·진도·수료증·비공개 질문과 Members-off 폴백, KBoard 제거 전 호환성, TLS/browser gate를 통과했다. KBoard 권한 엔진 이전·복제와 content migration은 범위 밖이다. 제품 방향 판정은 **GREENFIELD_RECOMMENDED**다.

## 문서의 기준 역할

| 문서 | Source of truth |
| --- | --- |
| [PRODUCT](docs/PRODUCT.md) | 현행 코드·설정·페이지 audit, 제품 경계, 기능 우선순위, fork 평가, 정책 결정 목록 |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | naming, 모듈, 데이터 audit·모델, public contract |
| [SECURITY](docs/SECURITY.md) | 인증·검증 상태 전이, threat model, 탈퇴·보안 정책 |
| [MIGRATION](docs/MIGRATION.md) | 전환 책임, 단계별 gate·rollback, 최대 5단계 roadmap |
| [OPERATIONS](docs/OPERATIONS.md) | MAMP TLS, 배포 담당자·백업·복구·관찰기간 인수 기준 |
| [HARNESS_PLAN](docs/HARNESS_PLAN.md) | 사용자 행동 검증, 성능 budget·측정 절차, release gate |
| [UI_UX](docs/UI_UX.md) | Members 화면 상태, 접근성, 번역, route 전용 자산 계약 |

중복 사양보다 위 소유 문서를 우선한다. runtime과 승인된 두 테이블은 합성 fixture에서만 실행했으며 현재 reference 사이트에 적용하지 않았다.

## 이번 조사에서 확인한 중요한 차이

2026-09-06 로컬 reference `C:/MAMP/htdocs/ns_0727`의 `active_plugins`에는 Cosmosfarm Members와 WP-Members가 **둘 다 없다**. 설치 파일·설정·shortcode·과거 데이터가 남아 있다. 따라서 이를 현재 활성 서비스나 운영 서버 상태로 단정하지 않는다. 현재 목록을 두 번 읽어 같은 상태를 확인했다.

현재 DB의 WordPress prefix는 `wp_`였다. 사용자 요청의 custom prefix 예시와 다르지만, 신규 제품은 항상 `$wpdb->prefix`와 WordPress API를 사용한다. 현지 payout 플러그인에는 `kklidi_pos_*`가 관찰되었다. 요청한 신규 convention `kklidi_mem_*`는 그대로 유지한다.

회원 434명과 기존 WordPress ID를 보존한다. 로그인·가입·reset·profile·동의·최소 감사·안전한 탈퇴 요청을 작은 1.0으로 권장한다. D01은 전화 선택, 이메일 가입 인증 없음, 가입 후 자동 로그인 없음으로 확정했다. 공개 가입 여부는 WordPress Core의 `users_can_register`가 단독으로 결정하며, 필수 서비스·개인정보 문서가 준비되지 않으면 Members 가입 화면은 닫힌다. D02는 자동 삭제 없이 즉시 접근 차단 후 관리자와 각 도메인 owner가 수동 조정하는 정책이다.

## 조사 안전 경계와 한계

- reference 사이트의 WordPress bootstrap, WP-CLI, HTTP, DB mutation은 실행하지 않았다. device-limit 파일은 임시 fixture에 읽기 전용 원본으로부터 복사해 실제 PHP hook을 실행했으며 원본에는 쓰지 않았다.
- DB 연결은 설정 파일을 실행하지 않고 연결 정보만 메모리에서 읽었다. mysqli 연결에 `SET SESSION TRANSACTION READ ONLY`, `START TRANSACTION READ ONLY`를 적용하고 SELECT·SHOW만 수행한 뒤 rollback했다. DB 인증 정보와 회원 개인정보 원문은 문서에 저장하지 않았다.
- 여러 read-only transaction의 조사 시점 집계이며 전체 사이트의 단일 시점 백업은 아니다. 측정한 것은 설정·코드·데이터이고, HTTP 행동·메일 전달·TTFB는 아직 측정하지 않았다.
- reference 코드·DB·설정·플러그인 활성 상태·MAMP 설정을 변경하지 않았다. 메일·SMS·OAuth 외부 송신, 실제 migration, commit, push를 수행하지 않았다.

## 후속 작업: synthetic harness

[실행 방법과 파일 역할](tests/harness/README.md). 공식 WordPress 7.1을 별도 임시 filesystem/DB에 설치하고 Core baseline 뒤 실제 Members runtime을 활성화한다. `wp_`/임의 prefix에서 Core 12개와 Members 12개 정상 로그인, 계정 workflow, Core reset mail/key, migration 멱등성, 실제 device-limit, 3×100 off/on 성능 block을 검증한다. MAMP UI나 기존 MySQL service는 켤 필요가 없다.

최신 실행 증거는 `.harness/reports/latest.json`, 검증 범위의 기준은 `docs/HARNESS_PLAN.md`다. 합성 경계 PASS를 실제 Woo/LMS/KBoard 브라우저 회귀 PASS로 해석하지 않는다.

## Localization

Members의 사용자 문구는 영어 source string과 `kklidi-members` text domain을 사용한다. 한국어는 `languages/kklidi-members-ko_KR.po`와 WordPress가 읽는 `languages/kklidi-members-ko_KR.mo`에서 제공하며, 템플릿·런타임 PHP에는 한국어 UI 문구를 직접 하드코딩하지 않는다. 사이트 언어가 `ko_KR`이면 WordPress Core의 locale 선택에 따라 해당 번역이 로드된다.

## UI implementation

`AUTH-UI-002`는 8개 frontend Members route와 Members 관리자 화면에 공통 page shell 및 stylesheet를 적용했다. frontend stylesheet는 Members query route에만, admin stylesheet는 `Tools → KKLIDI Members` 화면에만 로드된다. JavaScript와 외부 font/CDN 요청은 추가하지 않았다.
