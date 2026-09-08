"""Read-only HTTPS deployment preflight. Refuses HTTP and never accepts credentials."""
import argparse
import http.cookiejar
import json
from pathlib import Path
import ssl
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]

def inspect(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password \
            or parsed.query or parsed.fragment:
        return {'status': 'BLOCKED', 'reason': 'trusted_https_base_url_required',
                'network_request_sent': False}
    base = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip('/') + '/', '', ''))
    target = base + '?' + urllib.parse.urlencode({'kklidi_members_login': '1'})
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(jar), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    with opener.open(urllib.request.Request(target, headers={'User-Agent': 'KKLIDI-Members-Deployment-Preflight/1'}),
                     timeout=30) as response:
        body = response.read().decode('utf-8', errors='replace')
        headers = response.headers
        relevant = [cookie for cookie in jar if cookie.name == 'kklidi_members_guest']
        checks = {
            'https_final_url': urllib.parse.urlsplit(response.url).scheme == 'https',
            'login_form': 'name="kklidi_members_identifier"' in body,
            'no_store': 'no-store' in headers.get('Cache-Control', '').lower(),
            'private_cache': 'private' in headers.get('Cache-Control', '').lower(),
            'hsts': bool(headers.get('Strict-Transport-Security')),
            'guest_cookie_present': len(relevant) == 1,
            'guest_cookie_secure': len(relevant) == 1 and relevant[0].secure,
            'guest_cookie_httponly': len(relevant) == 1 and relevant[0].has_nonstandard_attr('HttpOnly'),
            'php_session_absent': not any(cookie.name == 'PHPSESSID' for cookie in jar),
        }
        return {'status': 'PASS' if all(checks.values()) else 'PARTIAL', 'checks': checks,
                'network_request_sent': True, 'host': parsed.hostname}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True, help='Trusted HTTPS base URL; credentials are not accepted.')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = inspect(args.url)
    output = args.output or ROOT / '.harness/reports/deployment-preflight.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
