# Members typography behavior contract

이 문서는 Members frontend 화면의 글자 크기와 줄간격 기준을 소유한다. 사이트 테마의 전역 스타일, LMS·WooCommerce·KBoard 화면, WordPress 관리자 전체 스타일을 변경하지 않는다.

| 항목 | 값 |
| --- | --- |
| Contract ID | `AUTH-UX-004` |
| 상태 | **IMPLEMENTED_AND_UNIT_VERIFIED** |
| 적용 범위 | Members가 소유한 9개 frontend route |
| 구현 버전 | 0.7.9 |
| 자산 경계 | route-scoped `assets/css/members.css` |

## 기준

CSS custom property를 기준 토큰으로 사용한다. 토큰은 Members stylesheet가 로드된 화면에서만 사용하며, 전역 reset이나 외부 font를 추가하지 않는다.

| 토큰 | 기준 | 용도 |
| --- | --- | --- |
| `--kklidi-members-font-body` | `16px` | 본문, 기본 텍스트 |
| `--kklidi-members-font-title` | `28px`~`32px` | 화면 H1 |
| `--kklidi-members-font-section` | `20px`~`22px` | 섹션 H2 |
| `--kklidi-members-font-control` | `16px` | label, input, button |
| `--kklidi-members-font-meta` | `14px` | 도움말과 오류 |
| `--kklidi-members-font-legal` | `15px` | 약관·개인정보 전문 |
| `--kklidi-members-line-body` | `1.6` | 일반 본문 줄간격 |
| 약관 줄간격 | `1.7` | 긴 문서 가독성 |

## 반응형·접근성 규칙

- H1은 desktop에서도 32px를 넘지 않으며, 좁은 화면에서 28px 아래로 내려가지 않는다.
- 본문과 입력 글자는 16px을 유지한다. 도움말·오류는 14px으로 낮추되 색상만으로 의미를 전달하지 않는다.
- 입력과 주요 버튼의 최소 높이는 기존 계약인 46px을 유지한다.
- 한국어 줄바꿈을 허용하고, 화면 확대·브라우저 기본 글꼴 설정을 막지 않는다.
- Members stylesheet는 route 전용으로만 enqueue한다. 일반 페이지, LMS, WooCommerce, KBoard 화면에는 이 토큰과 규칙이 로드되지 않는다.

## 제외 범위

- Kadence 또는 사이트 테마의 전역 typography 설정 변경
- 사용자별 글자 크기 설정 UI
- theme-wide CSS reset, 외부 font, page builder 스타일 통합
- 관리자 화면의 WordPress 기본 typography 변경

브라우저 desktop/mobile, 키보드, zoom 및 route isolation 검증은 0.7.9 browser release gate에서 별도로 수행한다. 이 계약의 unit guard는 토큰과 적용 경계가 유지되는지만 확인한다.
