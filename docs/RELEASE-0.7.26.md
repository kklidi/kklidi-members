# Release 0.7.26

## 관리자 라우트 링크 안내 개선

- Members 수동 메뉴용 링크와 WordPress가 생성하는 로그인·회원가입 링크를 별도 영역으로 표시한다.
- 현재 생성 링크와 WordPress Core fallback 주소를 함께 보여 설정 결과를 즉시 확인할 수 있다.
- “URL 소유권” 중심의 기술 용어를 “WordPress 생성 링크를 Members로 연결”하는 사용자 중심 문구로 바꾼다.
- `wp-login.php` 직접 접근은 계속 허용되며 강제 리디렉션하지 않는다는 경계를 관리자 화면에 표시한다.
- 설정 저장 방식, Core 인증 소유권, clean route/query fallback 동작은 변경하지 않는다.

검증: `tests/harness/test_runner.py` 41개 단위 하네스 테스트 통과.
