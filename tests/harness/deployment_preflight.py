"""Read-only HTTPS deployment preflight. Refuses HTTP and never accepts credentials."""
import argparse
import http.cookiejar
import json
from pathlib import Path
import socket
import ssl
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def inspect_tls(hostname, port, context):
    with socket.create_connection((hostname, port), timeout=30) as connection:
        with context.wrap_socket(connection, server_hostname=hostname) as secured:
            certificate = secured.getpeercert()
            version = secured.version()
    not_after = certificate.get('notAfter', '')
    expires_at = ssl.cert_time_to_seconds(not_after) if not_after else 0
    return {
        'version': version,
        'trusted_hostname': True,
        'not_after': not_after,
        'not_expired': expires_at > time.time(),
    }

def inspect(url, ca_file=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password \
            or parsed.query or parsed.fragment:
        return {'status': 'BLOCKED', 'reason': 'trusted_https_base_url_required',
                'network_request_sent': False}
    base = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip('/') + '/', '', ''))
    target = base + '?' + urllib.parse.urlencode({'kklidi_members_login': '1'})
    jar = http.cookiejar.CookieJar()
    context = ssl.create_default_context(cafile=str(ca_file) if ca_file else None)
    tls = inspect_tls(parsed.hostname, parsed.port or 443, context)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(jar), urllib.request.HTTPSHandler(context=context))
    with opener.open(urllib.request.Request(target, headers={'User-Agent': 'KKLIDI-Members-Deployment-Preflight/1'}),
                     timeout=30) as response:
        body = response.read().decode('utf-8', errors='replace')
        headers = response.headers
        relevant = [cookie for cookie in jar
                    if cookie.name in ('kklidi_members_guest', '__Host-kklidi_members_guest')]
        guest = relevant[0] if len(relevant) == 1 else None
        checks = {
            'https_final_url': urllib.parse.urlsplit(response.url).scheme == 'https',
            'tls_1_2_or_newer': tls['version'] in ('TLSv1.2', 'TLSv1.3'),
            'certificate_trusted_hostname': tls['trusted_hostname'],
            'certificate_not_expired': tls['not_expired'],
            'login_form': 'name="kklidi_members_identifier"' in body,
            'no_store': 'no-store' in headers.get('Cache-Control', '').lower(),
            'private_cache': 'private' in headers.get('Cache-Control', '').lower(),
            'hsts': bool(headers.get('Strict-Transport-Security')),
            'guest_cookie_present': guest is not None,
            'guest_cookie_host_prefix': guest is not None
                and guest.name == '__Host-kklidi_members_guest',
            'guest_cookie_secure': guest is not None and guest.secure,
            'guest_cookie_httponly': guest is not None and guest.has_nonstandard_attr('HttpOnly'),
            'guest_cookie_samesite_lax': guest is not None
                and str(guest.get_nonstandard_attr('SameSite')).lower() == 'lax',
            'guest_cookie_host_only': guest is not None and not guest.domain_specified,
            'guest_cookie_root_path': guest is not None and guest.path == '/',
            'php_session_absent': not any(cookie.name == 'PHPSESSID' for cookie in jar),
        }
        return {'status': 'PASS' if all(checks.values()) else 'PARTIAL', 'checks': checks,
                'tls': tls, 'network_request_sent': True, 'host': parsed.hostname}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True, help='Trusted HTTPS base URL; credentials are not accepted.')
    parser.add_argument('--ca-file', type=Path,
                        help='Optional CA certificate used with normal hostname verification.')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = inspect(args.url, args.ca_file)
    output = args.output or ROOT / '.harness/reports/deployment-preflight.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
