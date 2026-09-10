# Release 0.7.31

## 플랫폼 중립 인증 라우트 캐시 경계

- Members가 소유한 로그인·가입·계정·프로필·비밀번호·동의·탈퇴 라우트에만 캐시 방지 경계를 적용한다.
- WordPress 캐시 상수와 `Cache-Control`을 기본으로 사용하고, LiteSpeed·Varnish/Surrogate·CDN·Cloudflare가 이해할 수 있는 비캐시 헤더를 함께 보낸다.
- LiteSpeed가 활성화된 경우 공식 `litespeed_control_set_nocache` 경계도 사용한다. LiteSpeed가 없는 Cloudways Apache/Nginx 환경에서는 알 수 없는 헤더가 무시되고 표준 헤더와 `DONOTCACHE*` 상수만 적용된다.
- 다른 WordPress 화면, WooCommerce, LMS, PMS, KBoard에는 캐시 정책이나 자산을 전역 적용하지 않는다.

## 검증

- 플랫폼 중립 캐시 경계 정적 계약과 기존 Members 하네스 단위 테스트 45개가 통과한다.
- 실제 운영에서 LiteSpeed/Varnish/CDN 퍼지와 Cloudways 패널 설정은 별도 운영 작업으로 남는다. 플러그인 헤더만으로 이미 저장된 공개 캐시 객체를 삭제할 수 없기 때문이다.
