# Route management

`AUTH-ROUTE-MAP-001` 상태: **SPECIFIED_NOT_IMPLEMENTED**

대상 버전: **0.7.21**

이 문서는 shortcode나 WordPress 페이지에 의존하지 않고 Members 화면을 사이트 URL에 연결하는 규칙을 소유한다. 실행 가능한 설계 manifest는 `tests/harness/route_management_contract.json`이다.

## 1. 결정

Members는 기존의 query route를 계속 호환 경로로 제공하고, 관리자가 명시적으로 활성화한 경우에만 고정된 `/members/` clean route를 대표 링크로 사용한다. 로그인·회원가입·계정 화면을 위해 `wp_posts` 페이지를 만들거나 본문에 shortcode를 삽입하지 않는다.

이 선택은 화면이 없다는 뜻이 아니다. clean route와 query route가 같은 controller와 template을 호출하므로 로그인·회원가입·계정 화면은 Members가 직접 렌더링한다. 테마나 page builder의 본문 처리에 의존하지 않으며 WordPress Core가 identity, password, auth cookie와 session token을 계속 소유한다.

## 2. 고정 route map

| 화면 | clean route | 호환 query route |
| --- | --- | --- |
| 로그인 | `/members/login/` | `/?kklidi_members_login=1` |
| 회원가입 | `/members/register/` | `/?kklidi_members_register=1` |
| 내 계정 | `/members/account/` | `/?kklidi_members_account=1` |
| 프로필 | `/members/account/profile/` | `/?kklidi_members_profile=1` |
| 비밀번호 변경 | `/members/account/password/` | `/?kklidi_members_password=1` |
| 비밀번호 재설정 | `/members/password-reset/` | `/?kklidi_members_password_reset=1` |
| 동의 관리 | `/members/account/consent/` | `/?kklidi_members_consent=1` |
| 탈퇴 요청 | `/members/account/withdrawal/` | `/?kklidi_members_withdrawal=1` |
| 로그아웃 | `/members/logout/` | `/?kklidi_members_logout=1` |

0.7.21에서는 base와 slug를 사용자 정의하지 않는다. 사이트별 slug editor, 다국어별 path와 임의 page mapping은 별도 계약 전까지 추가하지 않는다. subdirectory WordPress 설치에서는 `home_url()`을 기준으로 위 상대 경로를 만든다.

## 3. 관리자 활성화와 충돌 처리

초기값은 clean route 꺼짐이다. `Users → KKLIDI Members`의 route 관리 화면에서 `manage_kklidi_members` capability와 WordPress nonce를 통과한 관리자가 한 번의 명시적 action으로 켜거나 끈다.

켜기 전에 `/members/` namespace와 아홉 경로를 모두 검사한다. 같은 path의 기존 WordPress 페이지, Members rule보다 먼저 같은 경로를 다른 query로 보내는 구체 rewrite rule이나 예약 endpoint가 있으면 전체 활성화를 거부한다. WordPress의 일반 page catch-all rule 자체를 충돌로 오판하지 않는다. Members는 충돌한 페이지를 삭제·휴지통 이동·이름 변경하거나 본문을 바꾸지 않는다. 충돌 대상의 path와 WordPress page ID처럼 관리에 필요한 최소 정보만 보여준다.

활성화 성공 시 versioned non-autoload option `kklidi_members_route_map`에 schema version과 `clean_routes_enabled` boolean만 저장한다. rewrite rule 추가·제거 뒤의 rewrite flush는 plugin 활성화나 이 설정의 실제 상태 변경 때 한 번만 수행하고 일반 요청에서는 수행하지 않는다. WordPress flush API의 반환값에 성공을 가정하지 않고 생성된 rule을 다시 확인하며, 저장 또는 rule 확인이 실패하면 option을 이전 상태로 되돌리고 켜졌다고 표시하지 않는다.

## 4. URL 소유권과 연결 방식

Members public URL helper는 clean route가 활성화됐을 때 clean URL을, 꺼져 있거나 설정이 손상됐을 때 query fallback을 반환한다. LMS·WooCommerce·다른 KKLIDI plugin은 이 helper가 존재하는지 확인한 뒤 사용하며 Members가 꺼지면 각자의 Core fallback을 사용한다.

기존 `kklidi_members_own_login_url`과 `kklidi_members_own_register_url`은 별도 opt-in으로 유지한다. 각각 켜졌을 때만 WordPress `login_url`과 `register_url` filter가 Members helper를 사용한다. password 재확인처럼 Core `force_reauth`가 필요한 로그인은 가로채지 않는다. `wp-login.php` 직접 접근을 강제로 redirect하지 않는다.

사이트 메뉴는 관리자가 대표 URL을 custom link로 추가한다. Members는 메뉴 항목을 자동 생성·수정·삭제하지 않는다. clean route를 끄면 관리자 화면에 표시하는 링크와 helper는 즉시 query fallback으로 돌아가며 기존 query route는 계속 동작한다.

## 5. 요청·보안·성능 경계

- clean route는 새 인증 엔진이 아니라 기존 query route를 같은 controller로 dispatch하는 URL adapter다.
- route별 로그인 상태, capability, nonce, rate limit, redirect allowlist와 no-store 규칙은 기존 계약을 그대로 적용한다.
- reset key와 login 값은 URL path에 넣지 않고 기존 Core 검증과 비밀 URL response header를 유지한다.
- clean route가 아닌 일반 frontend 요청에는 Members template, 관리자 class, CSS나 JavaScript를 load하지 않는다.
- rewrite 판정에 PHP session, 사용자별 cookie, custom auth token이나 별도 table을 사용하지 않는다.
- WordPress page, Woo 주문, LMS 수강·진도·수료증, KBoard content를 읽거나 수정하지 않는다.

## 6. 구현 합격 기준

1. 신규 설치와 업데이트의 기본값은 꺼짐이며 현재 query route 동작과 URL helper 결과가 바뀌지 않는다.
2. 관리자 capability와 nonce, strict option schema, non-autoload 저장과 실제 상태 변경 때만 수행되는 bounded rewrite flush를 검증한다.
3. namespace·page·rewrite 충돌에서는 아무 page·menu·option을 바꾸지 않고 활성화를 거부한다.
4. 활성화 후 아홉 clean route가 기존 controller와 template으로 동작하며 로그인·가입·프로필·reset·동의·탈퇴 상태 전이가 query route와 같다.
5. 위험한 `redirect_to`, reset key, Core `force_reauth`, 로그인/회원가입 URL ownership opt-in을 두 URL 형식에서 회귀 검증한다.
6. 비활성화와 설정 손상 시 query fallback으로 복구되고, Members plugin 자체 비활성화 시 Woo/LMS/다른 plugin에 fatal이 없다.
7. 일반 글 요청의 PHP session, Members route module, CSS/JS와 rewrite flush가 0인지 측정한다.

## 7. 제외 범위

WordPress 페이지 자동 생성, shortcode, block, page builder widget, 메뉴 자동 변경, custom slug, 언어별 route, 범용 접근 제한, redirect 일괄 강제, SEO canonical 설정과 multisite network route는 포함하지 않는다. 필요해지면 현재 route map 위의 별도 behavior contract로 검토한다.
