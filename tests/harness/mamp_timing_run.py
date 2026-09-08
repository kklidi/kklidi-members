"""Measure existing/missing identity login response distributions in the fixed sandbox."""
import html
import json
import os
from pathlib import Path
import re
import secrets
import statistics
import subprocess
import time

from mamp_race_run import Client, BASE
from run import hidden_input

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]

def main():
    token = secrets.token_hex(6)
    env = dict(os.environ, KKLIDI_TIMING_PASSWORD=secrets.token_urlsafe(32))
    report = {'run_id': 'mamp-timing-' + token, 'status': 'FAIL', 'samples_per_group': 9}
    def call(action):
        result = subprocess.run(['C:/MAMP/bin/php/php8.3.1/php.exe', '-d', 'display_errors=stderr',
            str(HERE / 'mamp_timing_case.php'), action, token], env=env, capture_output=True,
            timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or not result.stdout:
            raise RuntimeError('Timing fixture failed: ' + action)
        return json.loads(result.stdout)
    try:
        fixture = call('setup')
        timings = {'existing': [], 'missing': []}
        messages = {'existing': set(), 'missing': set()}
        for _ in range(9):
            for group in ('existing', 'missing'):
                client = Client()
                status, _, form = client.request(BASE + '?kklidi_members_login=1')
                fields = {
                    'kklidi_members_login': '1',
                    '_kklidi_members_login_nonce': hidden_input(form, '_kklidi_members_login_nonce'),
                    '_kklidi_members_guest_exp': hidden_input(form, '_kklidi_members_guest_exp'),
                    '_kklidi_members_guest_token': hidden_input(form, '_kklidi_members_guest_token'),
                    'kklidi_members_identifier': fixture[group],
                    'kklidi_members_password': 'Wrong-password-with-equal-cost-2026!',
                }
                started = time.perf_counter()
                post_status, _, body = client.request(BASE + '?kklidi_members_login=1', fields)
                timings[group].append((time.perf_counter() - started) * 1000)
                match = re.search(r'<[^>]+role="alert"[^>]*>(.*?)</[^>]+>', body, re.S)
                messages[group].add(html.unescape(re.sub('<[^>]+>', '', match.group(1))).strip() if match else '')
                assert status == post_status == 200
        existing_median = statistics.median(timings['existing'])
        missing_median = statistics.median(timings['missing'])
        ratio = max(existing_median, missing_median) / max(1, min(existing_median, missing_median))
        shape_equal = messages['existing'] == messages['missing'] and '' not in messages['existing']
        report.update(status='PASS' if shape_equal and ratio <= 2.0 else 'PARTIAL',
            public_message_equal=shape_equal,
            existing_ms={'median': round(existing_median, 3), 'p95': round(percentile(timings['existing'], .95), 3)},
            missing_ms={'median': round(missing_median, 3), 'p95': round(percentile(timings['missing'], .95), 3)},
            median_ratio=round(ratio, 3), threshold_ratio=2.0)
    finally:
        report['cleanup'] = call('cleanup')
        destination = ROOT / '.harness/reports' / (report['run_id'] + '.json')
        destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report))

if __name__ == '__main__':
    main()
