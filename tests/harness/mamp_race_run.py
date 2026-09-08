"""Concurrent registration and Core password-reset consumption in the fixed MAMP sandbox."""
from concurrent.futures import ThreadPoolExecutor
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request

from run import NoRedirect, hidden_input, local_response_path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'http://localhost:8888/kklidi-members-mamp-sandbox/'

class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, url, data=None):
        assert url.startswith(BASE)
        request = urllib.request.Request(url,
            data=urllib.parse.urlencode(data).encode() if data is not None else None,
            headers={'Origin': 'http://localhost:8888'})
        try:
            response = self.opener.open(request, timeout=45)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read().decode('utf-8')

def main():
    token = secrets.token_hex(6)
    password = secrets.token_urlsafe(32)
    env = dict(os.environ, KKLIDI_RACE_PASSWORD=password)
    report = {'run_id': 'mamp-race-' + token, 'status': 'FAIL', 'workers': 8}
    def call(action):
        result = subprocess.run(['C:/MAMP/bin/php/php8.3.1/php.exe', '-d', 'display_errors=stderr',
            str(HERE / 'mamp_race_case.php'), action, token], env=env, capture_output=True,
            timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or not result.stdout:
            raise RuntimeError('Race fixture failed: ' + action)
        return json.loads(result.stdout)
    try:
        fixture = call('setup')
        clients = [Client() for _ in range(8)]
        fields = []
        for client in clients:
            status, _, form = client.request(fixture['register_url'])
            assert status == 200
            fields.append({
                'kklidi_members_register': '1', 'request_id': hidden_input(form, 'request_id'),
                '_kklidi_members_register_nonce': hidden_input(form, '_kklidi_members_register_nonce'),
                '_kklidi_members_guest_exp': hidden_input(form, '_kklidi_members_guest_exp'),
                '_kklidi_members_guest_token': hidden_input(form, '_kklidi_members_guest_token'),
                'email': fixture['registration_email'], 'password': password,
                'password_confirm': password, 'first_name': '동시', 'last_name': '가입',
                'display_name': '동시 가입', 'phone': '', 'consent_service': '1', 'consent_privacy': '1'})
        barrier = threading.Barrier(8)
        def register(index):
            barrier.wait()
            return clients[index].request(fixture['register_url'], fields[index])
        with ThreadPoolExecutor(max_workers=8) as executor:
            registration_results = list(executor.map(register, range(8)))
        probe = call('probe')
        successes = sum(status == 302 and 'registered=1' in headers.get('Location', '')
                        for status, headers, _ in registration_results)
        assert successes == 1 and probe == {'registration_users': 1,
            'registration_user_id': probe['registration_user_id'], 'registration_state': 'active',
            'registration_roles': ['subscriber'], 'required_consents': 2,
            'reset_matching_passwords': 0}
        report['registration'] = {'submissions': 8, 'successes': successes, 'users': 1,
            'required_consents': 2, 'phone_optional': True}

        reset_clients = [Client() for _ in range(8)]
        reset_fields = []
        reset_candidates = []
        bootstrap = []
        for index, client in enumerate(reset_clients):
            start = fixture['reset_url'] + '&' + urllib.parse.urlencode(
                {'key': fixture['reset_key'], 'login': fixture['reset_login']})
            status, headers, _ = client.request(start)
            assert status == 302 and headers.get('Location')
            path = local_response_path(BASE, headers['Location'])
            status, _, form = client.request('http://localhost:8888' + path)
            bootstrap.append({'status': status, 'has_form': 'name="pass1"' in form,
                'path': urllib.parse.urlsplit(path).path,
                'query_keys': sorted(urllib.parse.parse_qs(urllib.parse.urlsplit(path).query))})
            report['reset_bootstrap'] = bootstrap
            assert status == 200 and 'name="pass1"' in form
            candidate = secrets.token_urlsafe(32)
            reset_candidates.append(candidate)
            reset_fields.append({'pass1': candidate, 'pass2': candidate,
                'rp_key': hidden_input(form, 'rp_key'), 'wp-submit': 'Save Password'})
        reset_barrier = threading.Barrier(8)
        def reset(index):
            reset_barrier.wait()
            return reset_clients[index].request(BASE + 'wp-login.php?action=resetpass', reset_fields[index])
        with ThreadPoolExecutor(max_workers=8) as executor:
            reset_results = list(executor.map(reset, range(8)))
        reset_successes = sum(status == 200 and 'password has been reset' in body.lower()
                              for status, _, body in reset_results)
        env['KKLIDI_RESET_CANDIDATES'] = json.dumps(reset_candidates)
        after_reset = call('probe')
        replay = Client()
        replay_status, replay_headers, replay_body = replay.request(fixture['reset_url'] + '&' +
            urllib.parse.urlencode({'key': fixture['reset_key'], 'login': fixture['reset_login']}))
        replay_form = replay_status == 200 and 'name="pass1"' in replay_body
        if replay_status == 302 and replay_headers.get('Location'):
            replay_path = local_response_path(BASE, replay_headers['Location'])
            replay_status, _, replay_body = replay.request('http://localhost:8888' + replay_path)
            replay_form = 'name="pass1"' in replay_body
        one_time = after_reset['reset_matching_passwords'] == 1 and not replay_form
        report['reset'] = {'submissions': 8, 'localized_success_responses': reset_successes,
            'matching_final_passwords': after_reset['reset_matching_passwords'],
            'replay_form_available': replay_form, 'one_time_result': one_time}
        report['status'] = 'PASS' if one_time else 'PARTIAL'
    finally:
        report['cleanup'] = call('cleanup')
        destination = ROOT / '.harness/reports' / (report['run_id'] + '.json')
        destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report))

if __name__ == '__main__':
    main()
