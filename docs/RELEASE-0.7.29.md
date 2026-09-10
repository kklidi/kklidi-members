# Release 0.7.29

## Members 전용 메일 발신자와 footer

- Members가 소유한 계정 알림과 관리자 가입 알림에만 선택적 `From` 이름·주소와 plain-text footer를 적용한다.
- 설정은 Users → Members → 알림의 WordPress Settings API, `manage_kklidi_members` 권한, 서버 nonce, non-autoload 단일 option을 사용한다.
- 기본값은 꺼짐이며 Core reset, WooCommerce, LMS, KBoard 및 다른 플러그인의 메일에는 영향을 주지 않는다.
- CR/LF, 잘못된 이메일, HTML·숏코드·PHP와 길이 초과 입력은 마지막 유효 설정을 유지한 채 거부한다.
- 시험 발송은 현재 로그인한 WordPress 관리자의 Core 이메일로만 보내고 관리자별 15분 3회로 제한한다. 결과는 `wp_mail()` 요청 수락 여부만 의미한다.

## 검증

- 단위 계약 guard와 번역/package gate를 통과해야 한다.
- 합성 WordPress 하네스 실행 `2fb34a1a46b14894989c36e755b2dbd1`은 기본/임의 database prefix에서 설정·권한·nonce·발신 header·footer·실패 주입·rate limit·metadata-only 감사 경계를 검증했다.
- 격리된 MAMP 후보 실행 `mamp-candidate-2ac4faf1bb6b`에서는 route, HTTPS/cookie, WooCommerce/LMS/KBoard compatibility, race/timing 회귀를 PASS했다. 메일 전용 실행 `mamp-mail-sender-56dbd5af1df2`도 `wp_mail()` 요청 수락, Members 범위 `From`, plain-text footer, 계정 메일 감사와 정리까지 PASS했다. 이 sink는 외부 mailbox 도착을 증명하지 않으며 SPF/DKIM/DMARC 정렬은 운영 배포 gate다.

검증 실행 ID와 ZIP SHA-256은 `.harness/reports/latest.json` 및 `dist/kklidi-members-0.7.29.manifest.json`에 기록한다.
