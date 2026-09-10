# Release 0.7.30

## 탈퇴 화면 비밀번호 표시 회귀 수정

- 탈퇴 라우트를 기존 route 전용 password enhancement 대상에 포함한다.
- JavaScript가 꺼지거나 로드되지 않아도 비밀번호 재확인과 탈퇴 요청 제출은 기존 서버 경로를 유지한다.
- 다른 페이지나 다른 플러그인에는 자산을 전역 로드하지 않는다.

## 검증

- 단위 guard는 탈퇴 라우트가 password enhancement 목록에 포함되는지 확인한다.
- 실제 Chrome에서 데스크톱 로그인 중앙 정렬, 인라인 눈 아이콘, 360px 회원가입 필수 표시·가로 overflow 부재, 탈퇴 화면 눈 아이콘과 보존 기간 문구를 확인한다.
- 브라우저 결과는 `.harness/reports/mamp-browser-0.7.30.json`에 기록한다.
- 합성 WordPress 전체 계약과 고정 MAMP 후보 게이트는 최종 0.7.30 ZIP을 대상으로 다시 실행한다.

운영 `studio01.kklidi.com`은 현재 0.7.25이므로 0.7.30 업로드 전에는 새 sender/footer와 이 회귀 수정의 운영 인수를 완료할 수 없다. 실제 운영 preflight에서는 HSTS를 제외한 Members 로그인 폼, no-store/private cache, `__Host-` guest cookie와 PHP session 부재를 확인했다.
