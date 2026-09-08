"""Executable AUTH-LMS-001 verification for the fixed MAMP sandbox."""
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from run import NoRedirect

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'http://localhost:8888/kklidi-members-mamp-sandbox/'
PHP = 'C:/MAMP/bin/php/php8.3.1/php.exe'


class Client:
    def __init__(self, cookie_data=None):
        self.jar = http.cookiejar.CookieJar()
        for item in (cookie_data or {}).get('cookies', []):
            if not item.get('name'):
                continue
            self.jar.set_cookie(http.cookiejar.Cookie(
                0, item['name'], item['value'], None, False, 'localhost.local', False,
                False, '/kklidi-members-mamp-sandbox/', True, False,
                cookie_data.get('expires'), False, None, None, {}, False))
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPCookieProcessor(self.jar))

    def get(self, url):
        if not url.startswith(BASE):
            raise RuntimeError('LMS fixture returned an unexpected URL')
        try:
            response = self.opener.open(url, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read().decode('utf-8')


def main():
    token = secrets.token_hex(6)
    env = dict(os.environ, KKLIDI_LMS_PASSWORD=secrets.token_urlsafe(32))
    report = {
        'run_id': 'mamp-lms-' + token,
        'contract': 'AUTH-LMS-001',
        'status': 'FAIL',
        'environment': 'fixed dedicated MAMP sandbox',
    }
    fixture_created = False

    def call(action):
        result = subprocess.run(
            [PHP, '-d', 'display_errors=stderr', str(HERE / 'mamp_lms_case.php'),
             action, token], env=env, capture_output=True, timeout=90,
            creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError('LMS fixture failed: ' + action)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError('LMS fixture returned invalid JSON: ' + action) from error

    try:
        fixture = call('setup')
        fixture_created = True
        probe = call('probe')
        student_id = fixture['user_ids']['student']
        identity_fields = (
            'wordpress_user_id', 'enrollment_user_id', 'order_user_id',
            'progress_user_id', 'certificate_user_id', 'question_student_user_id')
        assert all(probe[field] == student_id for field in identity_fields)
        assert probe['enrollment_course_id'] == fixture['course_id']
        assert probe['enrollment_order_id'] == fixture['order_id']
        assert probe['enrollment_source'] == 'woocommerce'
        assert probe['order_enrollment_count'] == 1
        assert fixture['reconcile']['count_by_order'] == 1
        assert probe['progress_percent'] == 100
        assert probe['student_access'] is True and probe['outsider_access'] is False
        assert probe['student_can_view_question'] is True
        assert probe['outsider_can_view_question'] is False
        assert probe['student_course_visible'] is True
        assert probe['outsider_course_hidden'] is True
        assert probe['login_uses_members'] is True
        assert probe['members_style_on_lms'] is False
        assert probe['mail_attempts_sunk'] >= 1

        student = Client(call('student-cookie'))
        outsider = Client(call('outsider-cookie'))
        student_course = student.get(fixture['course_url'])
        student_lesson = student.get(fixture['lesson_url'])
        outsider_lesson = outsider.get(fixture['lesson_url'])
        profile_url = fixture['classroom_url'] + (
            '&' if '?' in fixture['classroom_url'] else '?') + 'kklidi_lms_classroom_tab=profile'
        profile = student.get(profile_url)
        assert student_course[0] == 200 and student_lesson[0] == 200
        assert outsider_lesson[0] in (200, 302, 403)
        assert 'Synthetic LMS lesson fixture.' not in outsider_lesson[2]
        assert profile[0] == 302 and 'kklidi_members_profile=1' in profile[1].get('Location', '')

        off = call('members-off')
        assert off == {'members_active': False, 'lms_active': True,
                       'student_access': True, 'outsider_access': False}
        off_course = student.get(fixture['course_url'])
        off_profile = student.get(profile_url)
        anonymous_classroom = Client().get(fixture['classroom_url'])
        assert off_course[0] == 200 and off_profile[0] == 200
        assert 'Fatal error' not in off_course[2] + off_profile[2]
        assert anonymous_classroom[0] in (200, 302)
        assert 'wp-login.php' in (
            anonymous_classroom[1].get('Location', '') + anonymous_classroom[2])
        assert call('members-on')['members_active'] is True

        report.update(status='PASS', wordpress_user_id_preserved=True,
                      order_reconciliation_idempotent=True, progress_percent=100,
                      student_course_and_lesson_access=True,
                      outsider_lesson_and_question_denied=True,
                      outsider_lesson_status=outsider_lesson[0],
                      members_profile_delegation=True, members_css_on_lms=False,
                      notification_mail_sunk=True, members_off_learning_status=200,
                      members_off_lms_profile_status=200,
                      members_off_anonymous_status=anonymous_classroom[0],
                      members_off_anonymous_core_login=True,
                      members_off_fatal_error=False)
    finally:
        if fixture_created:
            report['cleanup'] = call('cleanup')
            if report['cleanup'] != {
                'cleaned': True, 'run_token': token, 'users_remaining': 0,
                'course_remaining': False, 'lesson_remaining': False,
                'owned_postmeta_remaining': 0, 'device_remaining': 0,
                'state_remaining': False, 'members_active': True,
            }:
                report['status'] = 'FAIL'
        destination = ROOT / '.harness/reports' / (report['run_id'] + '.json')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report))


if __name__ == '__main__':
    main()
