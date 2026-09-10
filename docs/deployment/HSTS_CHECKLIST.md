# HSTS 배포 체크리스트

HSTS는 KKLIDI Members가 자동으로 서버 설정을 변경하는 기능이 아니다. 사이트 전체의 HTTPS 정책이므로 웹서버, CDN 또는 호스팅 운영자가 배포 단계에서 적용한다.

## 적용 전

- [ ] 사이트의 HTTP 요청이 HTTPS로 정상 `301` 또는 `308` 전환되는지 확인한다.
- [ ] WordPress 주소와 사이트 주소가 HTTPS인지 확인한다.
- [ ] 로그인·관리자·정적 리소스가 HTTPS에서 정상 로드되는지 확인한다.
- [ ] 모든 운영 서브도메인이 HTTPS를 지원하는지 확인한다. 확인 전에는 `includeSubDomains`를 사용하지 않는다.
- [ ] 기존 `.htaccess`, LiteSpeed, Nginx 또는 CDN 헤더 설정을 백업한다.

## Studio01 LiteSpeed/Apache 적용

사이트 document root의 기존 `.htaccess`에 기존 WordPress·LiteSpeed 블록을 유지한 채 아래 헤더를 추가한다.

```apache
<IfModule mod_headers.c>
Header always set Strict-Transport-Security "max-age=300"
</IfModule>
```

LiteSpeed WebAdmin을 사용하는 경우 Virtual Hosts → 해당 호스트 → Context에서 `/` Static context의 Extra Headers에 같은 정책을 추가하고 graceful restart 후 확인한다.

## 단계적 기간 확대

- [ ] 1단계: `max-age=300` 적용 후 HTTPS 응답에 헤더가 나타나는지 확인한다.
- [ ] 2단계: 문제 없이 확인되면 `max-age=604800`으로 변경하고 7일 관찰한다.
- [ ] 3단계: 운영 문제가 없으면 `max-age=31536000`으로 변경한다.
- [ ] `includeSubDomains`는 모든 하위 도메인의 HTTPS 전환을 확인한 뒤 별도 승인으로 추가한다.
- [ ] `preload`는 장기간 되돌리기 어렵기 때문에 별도 검토 전에는 추가하지 않는다.

## 검증

```powershell
python tests/harness/deployment_preflight.py --url https://studio01.kklidi.com/ --output .harness/reports/studio01-hsts-preflight.json
```

다음 조건을 모두 확인한다.

- `status`가 `PASS`
- `hsts_policy.enabled`가 `true`
- `hsts_policy.max_age`가 0보다 큼
- TLS 1.2 이상, 유효한 hostname 인증서
- Members 라우트의 `no-store`·private 캐시 경계 유지
- `__Host-kklidi_members_guest`의 Secure·HttpOnly·SameSite=Lax·host-only·`Path=/`
- `PHPSESSID` 미발급

HSTS가 적용되지 않아도 Members 기능 자체는 동작할 수 있지만, 운영 HTTPS 강제 정책의 배포 게이트는 닫히지 않은 상태로 기록한다.
