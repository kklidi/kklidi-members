# Release 0.7.28

## 이메일 중심 신규 계정 식별자

- 신규 가입 화면은 별도 username을 받지 않고 이메일을 기본 식별자로 안내한다.
- 기존 WordPress 계정은 기존 username과 이메일 로그인을 계속 사용할 수 있다.
- 신규 계정의 내부 `user_login`과 공개될 수 있는 `user_nicename`을 독립적으로 생성한다.
- 로그인·비밀번호 찾기 화면에 기존 회원의 username 호환 안내를 추가했다.
- WordPress Core `wp_signon()`, Core password reset API, 사용자 ID와 기존 login 보존 경계는 유지한다.

검증: `tests/harness/test_runner.py` 44개 단위 guard 통과. 합성 WordPress 반복 실행 `c32099f406cb48b2ae6074bc38a0d997`에서 두 database prefix의 신규 이메일 로그인, 기존 username/email 로그인, 표시명 인증 거부, generic 오류, rate limit, Core ID/login 불변과 Members 비활성화 경계를 확인했다. 실행 보고서는 `.harness/reports/latest.json`에 기록한다.

배포 ZIP: `dist/kklidi-members-0.7.28.zip`. 생성된 `dist/kklidi-members-0.7.28.manifest.json`에 해당 ZIP의 SHA-256과 파일별 해시를 기록한다.
