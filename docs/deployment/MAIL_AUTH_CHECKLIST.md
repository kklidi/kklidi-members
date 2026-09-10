# 운영 메일 인증 체크리스트

KKLIDI Members는 WordPress `wp_mail()`을 사용하며 SMTP 계정, DNS, SPF, DKIM 또는 DMARC를 자동 변경하지 않는다. 이 항목은 사이트 메일 전송 계층과 DNS 운영자가 관리한다.

## Studio01 공개 DNS 기준값

2026-09-10 조회 결과다. 공개키 원문과 개인 정보는 기록하지 않았다.

- `kklidi.com` SPF: 현재 Studio01 서버 IP와 `include:relay.mailchannels.net`을 허용하며 `~all`로 종료한다.
- `studio01.kklidi.com` SPF: 현재 Studio01 서버 IP와 `include:relay.mailchannels.net`을 허용하며 `~all`로 종료한다.
- `default._domainkey.kklidi.com`: 유효한 RSA 2048비트 DKIM 공개키가 있다.
- `default._domainkey.studio01.kklidi.com`: 유효한 RSA 2048비트 DKIM 공개키가 있다.
- `_dmarc.kklidi.com`: `v=DMARC1; p=none;`이며 별도 `sp`가 없어 하위 도메인도 모니터링 정책을 상속한다.
- Studio01 서버 IP의 PTR은 호스팅 사업자 이름을 사용한다. 실제 메일이 MailChannels를 통과하는지 수신 헤더로 판정한다.

## 발송 전

- [ ] 실제 From 주소와 도메인을 정한다.
- [ ] Members 사용자 지정 발신자를 켜기 전에 해당 주소가 메일 제공업체에서 허용됐는지 확인한다.
- [ ] SMTP 또는 relay 제공업체가 `default` 선택자로 DKIM 서명하도록 설정됐는지 확인한다.
- [ ] DMARC 보고서를 받을 운영 주소를 정하기 전에는 임의 `rua`를 추가하지 않는다.
- [ ] SPF 레코드를 여러 개 만들지 않는다.

## 실제 수신 시험

WordPress 관리자에서 Members 테스트 메일을 현재 관리자의 Core 이메일로 한 건 보낸다. 이 작업은 `wp_mail()` 수락 여부만으로 완료 처리하지 않고 실제 받은 메일의 원문 헤더를 확인한다.

- [ ] `Authentication-Results`의 SPF가 pass다.
- [ ] `DKIM-Signature`의 `d=`가 From 도메인과 정렬되고 `s=default` 공개키로 pass다.
- [ ] DMARC가 pass다.
- [ ] 실제 `From`, `Return-Path`, `Received` 경로가 승인된 서버 또는 MailChannels를 사용한다.
- [ ] 제목·본문·footer가 예상한 한국어 plain-text로 표시된다.
- [ ] 스팸함 포함 실제 도착 시간을 기록한다.

## 정책 강화

- [ ] 실제 발송 헤더의 SPF 또는 DKIM 정렬과 DMARC pass를 확인하기 전에는 `p=quarantine` 또는 `p=reject`로 올리지 않는다.
- [ ] 모니터링 수신자와 처리 책임자를 정한 뒤 DMARC aggregate report를 수집한다.
- [ ] 정상 발송원을 모두 확인한 뒤 `p=none` → `p=quarantine` → `p=reject` 순서로 단계적으로 강화한다.
- [ ] Cloudways 스테이징이 생기면 그 서버의 발송 경로를 별도 확인하고 필요한 경우 기존 SPF 한 레코드 안에 승인된 provider만 추가한다.

실제 이메일 원문에는 수신자·서버 경로 등 민감 정보가 포함될 수 있으므로 저장소에 원문을 커밋하지 않는다. 결과는 pass/fail과 비식별 발송 경로만 기록한다.
