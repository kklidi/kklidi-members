# 0.7.30 출시 전 감사

- 감사일: 2026-09-10
- 판정: **LOCAL_RELEASE_CANDIDATE_PASS / PRODUCTION_ACCEPTANCE_BLOCKED**
- 배포 ZIP: `dist/kklidi-members-0.7.30.zip`
- SHA-256: `e67e0fabe8a24e58566ab966ac3115ae23fbe290b9270a4df9e604c8f5be65bb`

## 완료된 검증

- 단위·정적 계약 44개 PASS.
- fresh WordPress 합성 실행 `005ec18cf89143da88d23c9c389a019c`: 기본/임의 prefix에서 MVP 24개와 extension 8개 PASS, 임시 DB·파일·프로세스 정리 PASS.
- 실제 Chrome 실행 `mamp-browser-0.7.30-20260910`: 데스크톱 로그인, 360px 가입·계정 route, 필수 표시, 한 행 링크 위계, 가로 overflow 부재, password eye 동작, 관리자 알림·발신자 UI PASS.
- 브라우저 실행에서 탈퇴 route의 password script 누락을 발견했고, `is_password_enhancement_route()`에 해당 route를 추가한 뒤 버튼 표시·SVG·ARIA·input type 전환을 재검증했다.
- 최종 고정 MAMP 후보 `mamp-candidate-651b1c7c3b54`: route, TLS/cookie, LMS, WooCommerce, KBoard, race, timing, Members mail sender 8개 게이트 PASS. 원본 복원과 임시 디렉터리 삭제 PASS.
- PHP production 파일 40개 lint PASS. `git diff --check` 오류 없음.
- runtime에는 PHP session, custom authentication cookie, global `wp_mail_from` filter, SMTP credential 저장이 없다. `setcookie()` 사용은 비인증 guest CSRF binding 1곳으로 한정된다.
- MAMP `ns_0727`은 최종 0.7.30 package manifest 65개 파일과 일치하며, 기존 0.7.16 플러그인 백업 SHA-256은 `9aa5ae08c1ab33aa72c4f90fb2055af523bb0440cc96d2a5298bfc5f9cb68a08`이다.

## Studio01 관찰 결과

- WordPress 7.1, PHP 8.3.33, Members 0.7.25, WooCommerce disabled.
- 실제 TLS handshake: TLS 1.3, 인증서 hostname 신뢰와 유효기간 PASS.
- Members login form, private/no-store, PHPSESSID 부재 PASS.
- HSTS header는 없음.
- 새 cookie jar로 두 번 반복한 요청에서 `__Host-kklidi_members_guest`가 발급되지 않았다. LiteSpeed Cache 또는 proxy가 동적 Members 응답의 `Set-Cookie`를 제거·재사용하는지 확인해야 한다.
- 공개 DNS에는 SPF가 있고 DMARC는 `p=none`이다. DKIM selector와 실제 수신 메일 header가 없어 DKIM/From alignment 및 외부 mailbox 도착은 판정하지 않았다.

## 운영 인수 차단 항목

1. Studio01에 최종 0.7.30 ZIP 업로드 및 활성 버전 확인.
2. LiteSpeed/CDN cache에서 모든 Members route를 제외하고 purge한 뒤 deployment preflight 재실행.
3. 서버 또는 CDN에서 HSTS를 승인·적용한 뒤 재검증.
4. provider가 승인한 실제 발신 주소와 DKIM selector를 확정하고 관리자 본인 test mail의 수신 header로 SPF/DKIM/DMARC alignment 확인.
5. `.harness/reports/studio01-deployment-manifest.draft.json`의 담당자, 백업 artifact SHA-256·생성시각, 별도 restore 시험 증거를 실제 값으로 채우기.
6. 배포 뒤 최소 14일 관찰과 실제 계정 복구 1회 확인. Studio01은 WooCommerce가 비활성이므로 주문 관찰은 요구하지 않는다.

운영 인수 차단 항목은 plugin runtime 구현 실패가 아니라 현재 서버 설정, 배포 버전, 실제 메일 제공자와 운영 증거가 필요한 환경 gate다.
