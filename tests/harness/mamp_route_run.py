"""Exercise 0.7.21 clean routes in the fixed MAMP sandbox and restore site state."""
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from run import NoRedirect

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SANDBOX = Path('C:/MAMP/htdocs/kklidi-members-mamp-sandbox')
BASE = 'http://localhost:8888/kklidi-members-mamp-sandbox/'
PHP = Path('C:/MAMP/bin/php/php8.3.1/php.exe')
HTACCESS = SANDBOX / '.htaccess'
VERSION = re.search(r'\* Version: (\d+\.\d+\.\d+)',
                    (ROOT / 'kklidi-members.php').read_text(encoding='utf-8')).group(1)


def request(path):
    url = urllib.parse.urljoin(BASE, path.lstrip('/'))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        response = opener.open(url, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read().decode('utf-8', errors='replace')


def main():
    token = secrets.token_hex(6)
    report = {'run_id': 'mamp-route-' + token, 'contract': 'AUTH-ROUTE-MAP-001',
              'status': 'FAIL', 'version': VERSION}
    fixture_created = False
    original_htaccess = HTACCESS.read_bytes() if HTACCESS.is_file() else None

    def call(action):
        result = subprocess.run(
            [str(PHP), '-d', 'display_errors=stderr', str(HERE / 'mamp_route_case.php'),
             action, token, VERSION], capture_output=True, timeout=90,
            creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or not result.stdout:
            detail = (result.stderr or result.stdout).decode('utf-8', errors='replace')[-2000:]
            raise RuntimeError('Route fixture failed: ' + action + ': ' + detail)
        return json.loads(result.stdout)

    try:
        fixture_created = True
        setup = call('setup')
        if setup != {'version': VERSION, 'enabled': True, 'rules': 9,
                     'page_count': setup['page_count'], 'menu_count': setup['menu_count']}:
            raise RuntimeError('Clean route setup was incomplete')
        # The fixed sandbox normally uses plain permalinks and therefore has no
        # Apache front-controller file. Provide only the standard WordPress
        # subdirectory rule for this run; finally restores the original bytes.
        HTACCESS.write_text(
            '<IfModule mod_rewrite.c>\nRewriteEngine On\n'
            'RewriteBase /kklidi-members-mamp-sandbox/\n'
            'RewriteRule ^index\\.php$ - [L]\n'
            'RewriteCond %{REQUEST_FILENAME} !-f\n'
            'RewriteCond %{REQUEST_FILENAME} !-d\n'
            'RewriteRule . /kklidi-members-mamp-sandbox/index.php [L]\n'
            '</IfModule>\n', encoding='ascii')
        rendered_paths = ('members/login/', 'members/register/', 'members/account/',
                          'members/password-reset/')
        protected_paths = ('members/account/profile/', 'members/account/password/',
                           'members/account/consent/', 'members/account/withdrawal/')
        paths = rendered_paths + protected_paths + ('members/logout/',)
        responses = {}
        for path in paths:
            status, headers, body = request(path)
            responses[path] = {'status': status, 'location': headers.get('Location', ''),
                               'members_response': 'kklidi-members-page' in body}
            rendered = path in rendered_paths and status == 200 \
                and 'kklidi-members-page' in body
            protected = path in protected_paths and status == 302 \
                and '/members/login/' in headers.get('Location', '')
            logged_out = path == 'members/logout/' and status == 302 \
                and headers.get('Location', '').rstrip('/') == BASE.rstrip('/')
            if not (rendered or protected or logged_out) or 'Fatal error' in body:
                report['failed_response'] = {'path': path, **responses[path],
                    'body_sha256': hashlib.sha256(body.encode()).hexdigest()}
                raise RuntimeError('Clean route did not reach Members: ' + path)
        query_status, _, query_body = request('?kklidi_members_login=1')
        home_status, _, home_body = request('')
        if query_status != 200 or 'name="kklidi_members_identifier"' not in query_body:
            raise RuntimeError('Query fallback failed while clean routes were enabled')
        if home_status != 200 or 'kklidi-members-frontend-css' in home_body:
            raise RuntimeError('Unrelated route loaded Members assets')
        disabled = call('disable')
        fallback_status, _, fallback_body = request('?kklidi_members_login=1')
        if disabled != {'enabled': False} or fallback_status != 200 \
                or 'name="kklidi_members_identifier"' not in fallback_body:
            raise RuntimeError('Clean route disable did not preserve query fallback')
        report.update(status='PASS', clean_routes=responses, query_fallback=True,
                      unrelated_assets=False, automatic_pages_or_menus=False,
                      rewrite_rules=setup['rules'])
    finally:
        if fixture_created:
            try:
                cleanup = call('cleanup')
                report['cleanup'] = cleanup
                if cleanup != {'route_restored': True, 'permalink_restored': True,
                               'rewrite_restored': True, 'page_count_unchanged': True,
                               'menu_count_unchanged': True, 'audit_remaining': 0}:
                    report['status'] = 'FAIL'
            except Exception as error:
                report['cleanup_error'] = str(error)
                report['status'] = 'FAIL'
        if original_htaccess is None:
            if HTACCESS.exists():
                HTACCESS.unlink()
        else:
            HTACCESS.write_bytes(original_htaccess)
        report['htaccess_restored'] = ((original_htaccess is None and not HTACCESS.exists())
            or (original_htaccess is not None and HTACCESS.read_bytes() == original_htaccess))
        if not report['htaccess_restored']:
            report['status'] = 'FAIL'
        destination = ROOT / '.harness/reports' / (report['run_id'] + '.json')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
