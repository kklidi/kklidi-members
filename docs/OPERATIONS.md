# 배포·운영 인수 기준

이 문서는 Phase 0의 보안·마이그레이션 계약을 실제 환경에서 닫기 위한 실행 기준이다. 회원 ID, 비밀번호, 인증 쿠키, 주문, 수강, 정산 데이터의 소유권은 기존 문서와 동일하다.

## 1. 로컬 MAMP 게이트

`mamp_https_run.py`는 고정 `kklidi-members-mamp-sandbox`를 MAMP Apache 뒤의 임시 TLS 프록시로 연다. 매 실행마다 하루짜리 로컬 CA·서버 인증서를 만들고 정상 hostname 검증을 사용한다. HTTP client가 보낸 forwarded header는 제거하고 loopback 프록시가 HTTPS 신호를 새로 설정한다.

검증 항목은 TLS 1.2 이상, HSTS, private/no-store, `__Host-kklidi_members_guest`의 Secure/HttpOnly/SameSite/host-only/root-path, Core 로그인 쿠키의 Secure/HttpOnly, 로그인 후 계정 화면, PHPSESSID 부재다. KBoard가 전역 PHP session을 시작하므로 이 Members 소유권 검증 동안 KBoard와 KBoard Comments만 임시 비활성화하고 원래 활성 목록을 복원한다. KBoard 호환성은 별도 `mamp_kboard_run.py`가 담당한다.

```powershell
python tests/harness/mamp_https_run.py
python tests/harness/mamp_lms_run.py
python tests/harness/mamp_lifecycle_run.py
```

LMS 검사는 실제 Woo 주문·수강·진도·수료증·비공개 질문의 동일 WordPress user ID와 Members 비활성 fallback을 확인한다. lifecycle 검사는 배포 ZIP의 신규 설치, 직전 릴리스→현재 버전 업데이트, 현재 버전 재설치, 비활성·재활성, 보호된 ID/domain 지문과 원본 파일 복원을 확인한다. 두 runner는 다른 site path/URL을 받지 않고 실행별 JSON을 `.harness/reports`에 기록한다.

lifecycle domain 지문은 WordPress posts/comments와 Woo/LMS/KBoard 소유 테이블만 포함한다.
Action Scheduler와 익명 Woo session처럼 일반 HTTP 요청으로 변하는 기반 테이블은 Members
소유권 판정에서 제외하며, 선택된 보호 테이블의 비식별 CHECKSUM만 비교한다.

로컬 CA는 운영 신뢰 증거가 아니다. 실제 인증서, CDN 또는 load balancer, 브라우저 신뢰 저장소는 실제 staging URL에서 `deployment_preflight.py`로 다시 확인한다. preflight는 기본 신뢰 저장소와 hostname 검증을 사용하는 별도 TLS handshake에서 TLS 1.2 이상과 인증서 유효기간도 기록한다.

HSTS는 응답 헤더가 존재하는 것만으로 통과시키지 않고 양수 `max-age`를 요구한다. Studio01 LiteSpeed의 최초 적용안은 `docs/deployment/studio01-hsts.htaccess`에 있으며 5분 정책부터 시작해 검증·관찰 뒤 7일, 1년으로 올린다. 모든 하위 도메인이 HTTPS-only임을 확인하기 전에는 `includeSubDomains`를 추가하지 않고, preload는 별도 영향 검토 없이 사용하지 않는다.

운영자가 실제 설정을 적용할 때는 `docs/deployment/HSTS_CHECKLIST.md`를 따른다. Members는 `.htaccess`나 CDN 설정을 자동 편집하지 않으며, preflight 결과로 적용 여부만 확인한다.

Members 인증 라우트의 캐시 경계는 특정 호스팅 사업자에 종속되지 않는다. 플러그인은 해당 라우트에서 WordPress `DONOTCACHE*` 상수와 표준 `Cache-Control`을 설정하고, LiteSpeed·reverse proxy·CDN이 이해할 수 있는 보조 비캐시 헤더를 함께 보낸다. LiteSpeed에서는 공식 `litespeed_control_set_nocache` action도 호출한다. Cloudways의 Apache/Nginx·Varnish·Breeze·Cloudflare 조합에서는 알 수 없는 헤더가 무시되고 표준 헤더와 호스트 캐시 예외 설정이 적용된다. 이미 저장된 공개 캐시 객체는 플러그인 코드가 삭제할 수 없으므로 각 환경에서 Members 경로와 `kklidi_members_*` query 변형을 캐시 제외 목록에 넣고 퍼지한 뒤 재검증한다.

## 2. 제한 저장소와 다중 노드

로그인·가입·복구 제한 카운터는 WordPress object-cache adapter를 통하지 않고 공유 MySQL options table과 `GET_LOCK`을 사용한다. object cache 호출이 실패해도 카운터는 공유 DB에서 동작하고, DB 또는 advisory lock을 사용할 수 없으면 인증 mutation을 일시 거부한다. 일반 읽기 화면은 이 실패 정책의 대상이 아니다.

합성 하네스는 같은 DB를 공유하는 독립 PHP 프로세스 8개에서 100회를 동시에 실행해 정확히 10회만 허용되는지 확인한다. 이 결과는 한 컴퓨터의 프로세스 격리 증거다. 운영 다중 노드는 실제 서버들이 같은 DB endpoint와 salt 구성을 사용하는지 staging에서 다시 확인한다.

## 3. 마이그레이션과 롤백

합성 마이그레이션은 dry-run, 최초 import, 재실행, 제한된 import-row 롤백, 재실행 가능 상태, Core user ID와 legacy meta 보존을 검사한다. 기능 롤백에 사이트 전체 DB 복원을 사용하지 않는다. 배포 뒤 생긴 주문·진도·회원이 사라질 수 있기 때문이다.

실제 전환 전 다음 자료를 `deployment_manifest.example.json` 형식으로 별도 제한 저장소에 작성한다. manifest에는 credential, token, password, 개인 정보를 넣지 않는다.

- WordPress/PHP/Members/Woo 버전과 trusted HTTPS staging URL
- Members, WordPress privacy, Woo, LMS, payout, 사이트 콘텐츠, rollback 담당 역할
- 백업 artifact SHA-256, 생성 시각, 별도 restore 시험 증거
- D06 route owner 매핑
- 이전 플러그인 버전 복구 방법과 가입·민감 mutation 차단 방법
- 최소 14일 관찰 및 계정 복구 1회 확인 조건. WooCommerce 11.1.0이 활성인 환경은 실제 주문 1회도 확인하며, `disabled` 환경은 주문 관찰을 요구하지 않는다.

```powershell
python tests/harness/validate_deployment_manifest.py --manifest path/to/deployment-manifest.json
```

검사 결과가 `READY`이고 실제 HTTPS preflight가 PASS일 때만 production acceptance를 완료한다.
manifest validator는 현재 Members 버전과 D07의 WordPress 7.1/PHP 8.3 조합을 요구하며,
WooCommerce는 검증한 11.1.0 또는 명시적 `disabled`만 허용한다. 주문 관찰 조건은 이 버전 상태와 일치해야 한다.

릴리스 evidence JSON과 ZIP manifest는 설치 ZIP 밖의 sidecar로 보관한다. lifecycle
보고서가 최종 ZIP의 SHA-256을 기록하므로 evidence를 ZIP 안에 넣어 다시 빌드하는
순환 절차를 사용하지 않는다.

## 4. 1.0 보수적 정책

운영 결정이 추가되기 전에는 마케팅 동의를 수집하지 않고, display_name 중복을 허용하며, 과거 계정의 이메일 상태를 `legacy_unknown`으로 유지한다. 이메일 가입 인증, TOTP/2FA, social login, 자동 개인정보 삭제는 별도 behavior contract와 사용자 결정이 생긴 뒤 시작한다.
