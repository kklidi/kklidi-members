# Release audit 0.7.31 · Studio01

검증일: 2026-09-10 (Asia/Seoul)

대상은 `https://studio01.kklidi.com`의 활성 KKLIDI Members 0.7.31이다. 이 기록은 읽기 전용 운영 응답 검사와 저장소 정적 검사를 합친 것이며, 실제 메일 전달이나 데이터 삭제를 실행하지 않았다.

## 확인된 경계

- WordPress 관리자 플러그인 목록에서 0.7.31이 활성 상태임을 확인했다.
- TLS 1.3과 신뢰되는 hostname 인증서를 사용한다. 검사 시 인증서 만료 시각은 2026-11-02 13:11:07 UTC였다.
- 평문 HTTP의 Members 로그인 URL은 같은 HTTPS URL로 `301 Moved Permanently` 전환된다.
- 로그인·가입·비밀번호 재설정과 보호된 계정·프로필·비밀번호·동의·탈퇴·로그아웃 query route 모두 `no-store` 및 LiteSpeed 비캐시 경계를 보냈다.
- 같은 로그인 URL을 새 쿠키 상태로 세 번 요청했을 때 서로 다른 `__Host-kklidi_members_guest` 값이 발급됐다. 세 응답 모두 Secure, HttpOnly, SameSite=Lax, host-only, path `/` 조건을 만족했고 `X-LiteSpeed-Cache`, `Age`, `X-Cache`, `CF-Cache-Status` 적중 헤더는 없었다.
- 비밀번호 재설정 화면은 `Referrer-Policy: no-referrer`를 보냈다.
- 일반 홈페이지는 LiteSpeed 공개 캐시 정책을 유지했다. Members 비캐시 정책이 무관한 frontend 전체에 적용되지 않았다.
- 응답 경로는 LiteSpeed로 관찰됐으며 `Via`, `CF-Ray`, `X-Cache` 같은 외부 reverse proxy/CDN 표시는 없었다.
- limiter는 클라이언트가 보낸 `X-Forwarded-For`를 읽지 않고 서버가 정한 `REMOTE_ADDR`만 사용한다. 따라서 임의 forwarded header로 제한 network를 바꾸는 우회는 허용하지 않는다.
- PHP session cookie는 생성되지 않았고 Members는 Core 인증 쿠키를 대체하지 않는다.

## 운영 설정 상태

- clean member route는 비활성이다. query route가 현재 운영 주소다.
- WordPress 생성 로그인·회원가입 링크 소유권은 Core fallback으로 유지된다. `wp-login.php` 직접 접근을 강제로 리디렉션하지 않는다.
- LiteSpeed의 Members path/query/cookie 제외 설정과 0.7.31 route-scoped 비캐시 헤더가 함께 적용된 상태다.

## 닫히지 않은 게이트

- HTTPS 응답에 `Strict-Transport-Security`가 없다. HSTS는 plugin header가 아니라 서버 또는 CDN에서 전체 host와 subdomain 정책을 확인한 뒤 적용해야 한다.
- 현재 응답만으로 LiteSpeed 앞단의 비표시 load balancer 존재 여부나 내부 `REMOTE_ADDR` 전달 값을 증명할 수 없다. Cloudways처럼 reverse proxy를 두는 환경에서는 trusted staging에서 서로 다른 두 클라이언트가 서로 다른 limiter network로 계산되는지 별도 확인해야 한다.
- 서버는 `X-Powered-By: PHP/8.3.33`을 노출한다. Members 계약 위반은 아니지만 서버 hardening 항목으로 제거 여부를 결정할 수 있다.
- 배포 manifest는 담당 역할, 백업 artifact SHA-256·생성 시각, 별도 restore 시험 증거가 없어 `BLOCKED`다. HSTS가 적용되기 전 deployment preflight도 `PARTIAL`이다.

검사 뒤 `deployment_preflight.py`가 단순 헤더 존재 대신 양수 `max-age`를 요구하도록 보강했다. LiteSpeed/Apache 호환 단계적 적용안은 `docs/deployment/studio01-hsts.htaccess`에 기록했다. 실제 document-root 설정 반영은 호스팅 파일 또는 LiteSpeed WebAdmin 접근이 필요하다.

## 실행 증거

- `.harness/reports/studio01-sol-security-0.7.31-run1.json`
- `.harness/reports/studio01-sol-security-0.7.31-run2.json`
- `.harness/reports/studio01-deployment-manifest.validation-0.7.31.json`
- `python -m unittest test_runner.HarnessGuards.test_members_route_cache_boundary_is_platform_neutral_and_scoped`: PASS
