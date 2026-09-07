"""Actual fixed-sandbox KBoard smoke. Never accepts another site URL."""
import json
from pathlib import Path
import secrets
import subprocess
import urllib.request

HERE = Path(__file__).resolve().parent
BASE = 'http://localhost:8888/kklidi-members-mamp-sandbox/'

def main():
    token = secrets.token_hex(6)
    report = {'contract': 'AUTH-KBOARD-001', 'run_id': 'mamp-kboard-' + token, 'status': 'FAIL'}
    def call(action):
        result = subprocess.run(['C:/MAMP/bin/php/php8.3.1/php.exe', '-d', 'display_errors=stderr',
            str(HERE / 'mamp_kboard_case.php'), action, token], capture_output=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError('KBoard fixture command failed: ' + action)
        return json.loads(result.stdout)
    try:
        data = call('setup')
        report['modes'] = {}
        for mode in ('on', 'off'):
            if mode == 'off':
                assert call('off')['active'] is False
            checks = call('probe')
            assert checks == {'guest_write': False, 'member_write': True, 'post_owner': True, 'comment_owner': True}
            with urllib.request.urlopen(BASE + '?page_id=' + str(data['page']), timeout=30) as response:
                listing = response.read().decode('utf-8')
                assert response.status == 200 and 'POST-' + token in listing
            with urllib.request.urlopen(BASE + '?page_id=' + str(data['page']) + '&mod=document&uid=' + str(data['content']), timeout=30) as response:
                document = response.read().decode('utf-8')
                if not ('BODY-' + token in document and 'COMMENT-' + token in document):
                    (HERE.parents[1] / '.harness/kboard-diagnostic.html').write_text(document, encoding='utf-8')
                assert response.status == 200 and 'BODY-' + token in document and 'COMMENT-' + token in document
                assert 'Fatal error' not in document
                assert 'kklidi-members-frontend-css' not in document
                assert ('kklidi_members_login=1' if mode == 'on' else 'wp-login.php') in document
            checks.update(list_and_document_http_200=True, comment_rendered=True, members_css=False,
                          comment_login_link='Members' if mode == 'on' else 'WordPress Core')
            report['modes'][mode] = checks
        report['status'] = 'PARTIAL'
        report['not_run'] = ['D06: actual ownership decisions for three legacy restriction pages and three menus',
                             'Interactive KBoard JavaScript submission']
    finally:
        report['cleanup'] = call('cleanup')
        destination = HERE.parents[1] / '.harness/reports' / (report['run_id'] + '.json')
        destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report))

if __name__ == '__main__':
    main()
