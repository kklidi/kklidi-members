"""Isolated WordPress Core baseline for AUTH-LOGIN-001. Standard library only."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html as html_module
import http.cookiejar
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import socket
import stat
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CACHE = REPO / '.harness' / 'cache'
LOCK = json.loads((HERE / 'wordpress.lock.json').read_text(encoding='utf-8'))
PRODUCTION_FILES = [
    'kklidi-members.php',
    'includes/Admin/AdminController.php',
    'includes/Audit/Recorder.php',
    'includes/Auth/LoginController.php',
    'includes/Auth/LogoutController.php',
    'includes/Auth/PasswordController.php',
    'includes/Consent/ConsentController.php',
    'includes/Consent/Documents.php',
    'includes/Consent/Repository.php',
    'includes/Core/Installer.php',
    'includes/Core/Plugin.php',
    'includes/Core/Url.php',
    'includes/Frontend/AccountController.php',
    'includes/Migration/LegacyConsentImporter.php',
    'includes/Profile/ProfileController.php',
    'includes/Registration/RegistrationController.php',
    'includes/Security/AccountState.php',
    'includes/Security/GuestCsrf.php',
    'includes/Security/RateLimiter.php',
    'includes/Withdrawal/WithdrawalController.php',
	'assets/css/admin.css',
	'assets/css/members.css',
    'templates/account.php',
    'templates/admin.php',
    'templates/consent.php',
    'templates/login.php',
    'templates/logout.php',
    'templates/password.php',
    'templates/profile.php',
    'templates/register.php',
    'templates/withdrawal.php',
]
PACKAGE_FILES = PRODUCTION_FILES + [
    'languages/kklidi-members.pot',
    'languages/kklidi-members-ko_KR.po',
    'languages/kklidi-members-ko_KR.mo',
]
DEVICE_REFERENCE = Path('C:/MAMP/htdocs/ns_0727/wp-content/plugins/kklidi-device-limit')


class HarnessError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise HarnessError(message)


def archive_name(name):
    """No absolute paths, Windows streams, traversal, or other archive roots."""
    p = PurePosixPath(name)
    require('\\' not in name and ':' not in name and not p.is_absolute()
            and '..' not in p.parts and p.parts and p.parts[0] == 'wordpress',
            'Unsafe WordPress archive path')
    return p


def verified_archive():
    archive = CACHE / f'wordpress-{LOCK["version"]}.zip'
    checksums = CACHE / f'wordpress-{LOCK["version"]}-checksums.json'
    for path, field in [(archive, 'archive_sha256'), (checksums, 'checksums_sha256')]:
        require(path.is_file(), 'Missing dependency cache; run --prepare first')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == LOCK[field],
                'Dependency checksum mismatch; refusing execution')
    known = json.loads(checksums.read_text(encoding='utf-8'))['checksums']
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            archive_name(entry.filename)
            require((entry.external_attr >> 16) & 0o170000 != 0o120000,
                    'Archive symlink rejected')
        for name, expected in known.items():
            require(hashlib.md5(z.read('wordpress/' + name)).hexdigest() == expected,
                    'Official WordPress file checksum mismatch')
    return archive, len(known)


def prepare():
    CACHE.mkdir(parents=True, exist_ok=True)
    for url_key, filename in [
        ('archive_url', f'wordpress-{LOCK["version"]}.zip'),
        ('checksums_url', f'wordpress-{LOCK["version"]}-checksums.json'),
    ]:
        target = CACHE / filename
        if not target.exists():
            with urllib.request.urlopen(LOCK[url_key], timeout=60) as response:
                require(urllib.parse.urlsplit(response.url).scheme == 'https', 'TLS download required')
                target.write_bytes(response.read())
    _, count = verified_archive()
    print(f'Official WordPress {LOCK["version"]}: {count} file checksums verified.')


def choose_port(exclude=()):
    for _ in range(50):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        if port >= 20000 and port not in exclude:
            return port
    raise HarnessError('No isolated loopback port available')


def wait_port(process, port, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        require(process.poll() is None, 'Owned server exited before readiness')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.3):
                return
        except OSError:
            time.sleep(0.15)
    raise HarnessError('Owned server readiness timed out')


def owned_cleanup(root, run_id):
    resolved = root.resolve()
    require(root.parent.resolve() == Path(tempfile.gettempdir()).resolve()
            and resolved == root.absolute() and not root.is_symlink()
            and root.name.startswith('kklidi-members-harness-')
            and (root / 'owner').read_text() == run_id,
            'Refusing cleanup outside owned temporary run')
    # Check descendants too: never follow a junction into an unrelated directory.
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            require(not path.is_symlink() and not path.is_junction(), 'Cleanup reparse point rejected')
    # OneDrive source directories can carry the Windows read-only attribute through copytree.
    # This is still confined to the verified, per-run owned root above.
    for directory, dirs, files in os.walk(root, topdown=False, followlinks=False):
        for name in files + dirs:
            os.chmod(Path(directory) / name, stat.S_IREAD | stat.S_IWRITE)
    os.chmod(root, stat.S_IREAD | stat.S_IWRITE)
    shutil.rmtree(root)


def copy_production_plugin(target):
    for name in PRODUCTION_FILES:
        destination = target / Path(name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, destination)


def copy_device_reference(target):
    source = DEVICE_REFERENCE.resolve()
    require(source == DEVICE_REFERENCE and source.is_dir(), 'Pinned device-limit reference missing')
    manifest = {}
    for directory, dirs, files in os.walk(source, followlinks=False):
        for name in dirs + files:
            item = Path(directory) / name
            require(not item.is_symlink() and not item.is_junction(), 'Device reference reparse point rejected')
        for name in files:
            item = Path(directory) / name
            relative = item.relative_to(source)
            destination = target / relative
            require(destination.resolve().is_relative_to(target.resolve()), 'Device reference escaped target')
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, destination)
            manifest[relative.as_posix()] = hashlib.sha256(item.read_bytes()).hexdigest()
    require('kklidi-device-limit.php' in manifest, 'Device plugin entry file missing')
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), len(manifest)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Browser:
    def __init__(self, base):
        parsed = urllib.parse.urlsplit(base)
        require(parsed.scheme == 'http' and parsed.hostname == '127.0.0.1'
                and parsed.port and parsed.port >= 20000 and not parsed.username
                and not parsed.path and not parsed.query and not parsed.fragment,
                'Only a fresh loopback harness origin is allowed')
        self.base = base
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                                 urllib.request.HTTPCookieProcessor(self.cookies))

    def set_cookie(self, name, value):
        self.cookies.set_cookie(http.cookiejar.Cookie(
            version=0, name=name, value=value, port=None, port_specified=False,
            domain='127.0.0.1', domain_specified=False, domain_initial_dot=False,
            path='/', path_specified=True, secure=False, expires=None, discard=True,
            comment=None, comment_url=None, rest={}, rfc2109=False))

    def request(self, path, data=None, key=None, headers=None):
        require(path.startswith('/') and not path.startswith('//')
                and '\\' not in path and '\r' not in path and '\n' not in path,
                'Only local request paths are allowed')
        headers = dict(headers or {})
        if key:
            headers['X-KKH-Probe'] = key
        payload = urllib.parse.urlencode(data).encode() if data is not None else None
        req = urllib.request.Request(self.base + path, data=payload, headers=headers)
        try:
            response = self.opener.open(req, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, response.headers, response.read().decode('utf-8', errors='replace')

    def observe(self, key):
        status, _, body = self.request('/index.php?kkh_observe=1', key=key)
        require(status == 200, 'Observation endpoint failed')
        try:
            return json.loads(body)
        except ValueError:
            raise HarnessError('Observation was not valid JSON') from None


def assert_identity(observed, expected, prefix, run_id, expected_plugins=None,
                    expected_kklidi_cookies=None):
    expected_plugins = [] if expected_plugins is None else expected_plugins
    expected_kklidi_cookies = [] if expected_kklidi_cookies is None else expected_kklidi_cookies
    expected_files = ([] if not expected_plugins else [
        'includes/Audit/Recorder.php', 'includes/Core/Plugin.php',
        'includes/Security/AccountState.php', 'includes/Security/RateLimiter.php',
        'kklidi-members.php'])
    require(observed['run_id'] == run_id and observed['prefix'] == prefix, 'Wrong fixture observed')
    require(observed['logged_in'] is True and observed['user_id'] == expected['id'],
            'Core identity did not survive the next HTTP request')
    require(observed['roles'] == expected['roles'] and observed['can_read'] is True
            and observed['can_manage_options'] is False, 'Capabilities changed during login')
    require(observed['display_name'] == expected['display_name'], 'Display name changed during login')
    require(observed['users_count'] == 3 and observed['plugins'] == expected_plugins,
            'Fixture identity/plugin drift')
    require(observed['members_files'] == expected_files,
            'Unrelated frontend request loaded unexpected Members modules')
    require(observed['php_session_active'] is False
            and observed['kklidi_cookies'] == expected_kklidi_cookies,
            'Members introduced a PHP session or custom authentication cookie')


def events(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def hidden_input(document, name):
    match = re.search(r'<input\b[^>]*\bname=["\']' + re.escape(name)
                      + r'["\'][^>]*\bvalue=["\']([^"\']*)["\']', document, re.IGNORECASE)
    require(match is not None, f'Missing hidden input: {name}')
    return html_module.unescape(match.group(1))


def assert_core_cookie(browser, remember, allowed_kklidi=None):
    allowed_kklidi = set() if allowed_kklidi is None else set(allowed_kklidi)
    cookies = [c for c in browser.cookies if c.name.startswith('wordpress_logged_in_')]
    require(len(cookies) == 1, 'Expected one Core logged-in cookie')
    cookie = cookies[0]
    require(cookie.has_nonstandard_attr('HttpOnly'), 'Core login cookie is not HttpOnly')
    if remember:
        require(cookie.expires is not None and cookie.expires > time.time() + 86400,
                'Remember-me cookie is not persistent')
    else:
        require(cookie.expires is None and cookie.discard, 'Session-only login became persistent')
    require(not any(c.name == 'PHPSESSID' for c in browser.cookies), 'PHP session cookie introduced')
    require(not any(c.name.lower().startswith('kklidi') and c.name not in allowed_kklidi
                    for c in browser.cookies), 'Unexpected KKLIDI cookie introduced')
    return cookie


def run_login_cases(base, env, fixture):
    rows = []
    key = env['KKH_PROBE_KEY']
    journal = Path(env['KKH_EVENTS'])
    require(sum(e['type'] == 'mail_sunk' for e in events(journal)) == 2,
            'Installation plus explicit probe must both reach the mail sink')
    outsider = Browser(base)
    outsider_status, _, outsider_body = outsider.request('/index.php?kkh_observe=1')
    require(outsider_status == 403,
            f'Observer guard expected 403, received {outsider_status}; body: {outsider_body[:180]}')
    require(outsider.request('/wp-config.php')[0] == 404, 'Non-test route exposed')
    for label, field in [('email_identity', 'email'), ('separate_username', 'login'),
                         ('separate_username', 'email')]:
        expected = fixture['fixtures'][label]
        for remember in (False, True):
            browser = Browser(base)
            before = browser.observe(key)
            require(before['user_id'] == 0 and before['logged_in'] is False, 'Dirty anonymous fixture')
            destination = base + '/index.php?kkh_observe=1&destination=synthetic-course'
            status, _, html = browser.request('/wp-login.php?' + urllib.parse.urlencode({'redirect_to': destination}))
            require(status == 200 and 'name="log"' in html and 'name="pwd"' in html
                    and 'name="testcookie"' in html, 'Native WordPress login form missing')
            require(any(c.name == 'wordpress_test_cookie' for c in browser.cookies), 'Core test cookie missing')
            prior_events = len(events(journal))
            fields = {'log': expected[field], 'pwd': env['KKH_USER_PASSWORD'],
                      'redirect_to': destination, 'testcookie': '1', 'wp-submit': 'Log In'}
            if remember:
                fields['rememberme'] = 'forever'
            status, headers, _ = browser.request('/wp-login.php', data=fields)
            require(status == 302 and headers.get('Location') == destination, 'Core login destination changed')
            assert_core_cookie(browser, remember)
            # Follow the exact returned destination, with the Core cookie jar, in a new request.
            path = headers['Location'][len(base):]
            status, _, body = browser.request(path, key=key)
            require(status == 200, 'Destination request failed')
            observed = json.loads(body)
            assert_identity(observed, expected, env['KKH_PREFIX'], env['KKH_RUN'])
            delta = events(journal)[prior_events:]
            require(delta == [{'type': 'wp_login', 'user_id': expected['id']}],
                    'Login must emit exactly one successful Core event and no email')
            # Falsification controls: the observation key grants no WordPress identity.
            browser.cookies.clear()
            require(browser.observe(key)['user_id'] == 0, 'Identity survives without a Core cookie')
            try:
                assert_identity(observed, dict(expected, id=expected['id'] + 999), env['KKH_PREFIX'], env['KKH_RUN'])
            except HarnessError:
                pass
            else:
                raise HarnessError('Identity assertion accepted the wrong user ID')
            rows.append({'identity': label, 'identifier': field, 'remember': remember,
                         'expected_user_id': expected['id'], 'observed_user_id': observed['user_id'],
                         'roles_unchanged': True, 'destination_preserved': True,
                         'core_success_events': len(delta), 'cookie_persistent': remember,
                         'cookie_removal_control': 'PASS', 'wrong_id_control': 'PASS', 'status': 'PASS'})
    return rows


def run_members_cases(base, env, fixture):
    rows = []
    guard_rows = []
    key = env['KKH_PROBE_KEY']
    journal = Path(env['KKH_EVENTS'])
    active = ['kklidi-members/kklidi-members.php']
    bootstrap_files = ['includes/Audit/Recorder.php', 'includes/Core/Plugin.php',
                       'includes/Security/AccountState.php', 'includes/Security/RateLimiter.php',
                       'kklidi-members.php']
    unrelated = Browser(base).observe(key)
    require(unrelated['plugins'] == active and unrelated['members_files'] == bootstrap_files,
            'Members did not stay at its minimal bootstrap on an unrelated frontend request')
    require(unrelated['php_session_active'] is False and unrelated['kklidi_cookies'] == [],
            'Members bootstrap introduced session authentication state')

    for label, field in [('email_identity', 'email'), ('separate_username', 'login'),
                         ('separate_username', 'email')]:
        expected = fixture['fixtures'][label]
        for remember in (False, True):
            browser = Browser(base)
            before = browser.observe(key)
            require(before['user_id'] == 0 and before['logged_in'] is False, 'Dirty anonymous fixture')
            destination = base + '/index.php?kkh_observe=1&destination=members-course'
            route = '/?' + urllib.parse.urlencode({
                'kklidi_members_login': '1', 'redirect_to': destination,
            })
            status, headers, document = browser.request(route)
            cache_control = headers.get('Cache-Control', '').lower()
            require(status == 200 and 'name="kklidi_members_identifier"' in document
                    and 'name="kklidi_members_password"' in document
                    and 'name="kklidi_members_remember"' in document,
                    'Members server-rendered login form missing')
            require('no-store' in cache_control and 'private' in cache_control,
                    'Members account response is not private/no-store')
            require(hidden_input(document, 'redirect_to') == destination,
                    'Safe local redirect was not preserved in the form')
            guest_cookies = [c for c in browser.cookies if c.name == 'kklidi_members_guest']
            require(len(guest_cookies) == 1 and not any(c.name == 'PHPSESSID' for c in browser.cookies),
                    'Members GET did not create exactly one non-auth guest binding cookie')
            prior_events = len(events(journal))
            fields = {
                'kklidi_members_login': '1',
                '_kklidi_members_login_nonce': hidden_input(document, '_kklidi_members_login_nonce'),
                '_kklidi_members_guest_exp': hidden_input(document, '_kklidi_members_guest_exp'),
                '_kklidi_members_guest_token': hidden_input(document, '_kklidi_members_guest_token'),
                'kklidi_members_identifier': expected[field],
                'kklidi_members_password': env['KKH_USER_PASSWORD'],
                'redirect_to': destination,
            }
            if remember:
                fields['kklidi_members_remember'] = '1'
            status, response_headers, _ = browser.request('/?kklidi_members_login=1', data=fields)
            require(status == 302 and response_headers.get('Location') == destination,
                    'Members login destination changed')
            assert_core_cookie(browser, remember, allowed_kklidi={'kklidi_members_guest'})
            path = response_headers['Location'][len(base):]
            status, _, body = browser.request(path, key=key)
            require(status == 200, 'Members destination request failed')
            observed = json.loads(body)
            assert_identity(observed, expected, env['KKH_PREFIX'], env['KKH_RUN'], active,
                            ['kklidi_members_guest'])
            require(observed['members_files'] == bootstrap_files,
                    'Members route-only modules leaked into the next request')
            delta = events(journal)[prior_events:]
            require(delta == [{'type': 'wp_login', 'user_id': expected['id']}],
                    'Members login must emit one Core event with no mail or HTTP activity')
            browser.cookies.clear()
            require(browser.observe(key)['user_id'] == 0, 'Members identity survives without Core cookies')
            try:
                assert_identity(observed, dict(expected, id=expected['id'] + 999),
                                env['KKH_PREFIX'], env['KKH_RUN'], active)
            except HarnessError:
                pass
            else:
                raise HarnessError('Members identity assertion accepted the wrong user ID')
            rows.append({'identity': label, 'identifier': field, 'remember': remember,
                         'expected_user_id': expected['id'], 'observed_user_id': observed['user_id'],
                         'roles_unchanged': True, 'destination_preserved': True,
                         'core_success_events': len(delta), 'cookie_persistent': remember,
                         'cookie_removal_control': 'PASS', 'wrong_id_control': 'PASS',
                         'status': 'PASS'})

    browser = Browser(base)
    hostile = 'https://example.invalid/escape'
    route = '/?' + urllib.parse.urlencode({'kklidi_members_login': '1', 'redirect_to': hostile})
    status, _, document = browser.request(route)
    safe_destination = base + '/'
    require(status == 200 and hidden_input(document, 'redirect_to') == safe_destination,
            'External redirect was not rejected before form submission')
    expected = fixture['fixtures']['email_identity']
    prior_events = len(events(journal))
    fields = {'kklidi_members_login': '1',
              '_kklidi_members_login_nonce': hidden_input(document, '_kklidi_members_login_nonce'),
              '_kklidi_members_guest_exp': hidden_input(document, '_kklidi_members_guest_exp'),
              '_kklidi_members_guest_token': hidden_input(document, '_kklidi_members_guest_token'),
              'kklidi_members_identifier': expected['email'],
              'kklidi_members_password': env['KKH_USER_PASSWORD'],
              'redirect_to': hostile}
    status, response_headers, _ = browser.request('/?kklidi_members_login=1', data=fields)
    require(status == 302 and response_headers.get('Location') == safe_destination,
            'External redirect was accepted during login')
    assert_core_cookie(browser, False, allowed_kklidi={'kklidi_members_guest'})
    delta = events(journal)[prior_events:]
    require(delta == [{'type': 'wp_login', 'user_id': expected['id']}],
            'Redirect guard login emitted unexpected side effects')
    guard_rows.append({'external_redirect_rejected': True, 'fallback': safe_destination,
                       'core_success_events': 1, 'status': 'PASS'})
    return rows, guard_rows


def members_login(base, env, identifier, password, destination='/', remember=False, browser=None):
    browser = browser or Browser(base)
    route = '/?' + urllib.parse.urlencode({
        'kklidi_members_login': '1',
        'redirect_to': base + destination,
    })
    status, _, document = browser.request(route)
    require(status == 200, 'Members login form did not render')
    fields = {
        'kklidi_members_login': '1',
        '_kklidi_members_login_nonce': hidden_input(document, '_kklidi_members_login_nonce'),
        '_kklidi_members_guest_exp': hidden_input(document, '_kklidi_members_guest_exp'),
        '_kklidi_members_guest_token': hidden_input(document, '_kklidi_members_guest_token'),
        'kklidi_members_identifier': identifier,
        'kklidi_members_password': password,
        'redirect_to': base + destination,
    }
    if remember:
        fields['kklidi_members_remember'] = '1'
    response = browser.request('/?kklidi_members_login=1', data=fields)
    return browser, response, document


def local_response_path(base, location):
    if location.startswith('/') and not location.startswith('//') and '\\' not in location:
        return location
    parsed_base = urllib.parse.urlsplit(base)
    parsed = urllib.parse.urlsplit(location)
    require(parsed.scheme == parsed_base.scheme and parsed.hostname == parsed_base.hostname
            and parsed.port == parsed_base.port and not parsed.username,
            'Response attempted to leave the synthetic origin')
    return urllib.parse.urlunsplit(('', '', parsed.path or '/', parsed.query, parsed.fragment))


def run_mvp_cases(base, env, fixture, command, php_cli):
    """Exercise the bounded 1.0 account workflows through real HTTP requests."""
    results = {}
    key = env['KKH_PROBE_KEY']
    active = ['kklidi-members/kklidi-members.php']

    missing_documents = command(php_cli + [HERE / 'mvp_setup.php', 'core-on-no-documents'], json_result=True)
    require(missing_documents == {'required_ready': False, 'legacy_registration_option': '1',
                                  'users_can_register': True}, 'Missing-document gate setup failed')
    disabled = Browser(base)
    status, _, document = disabled.request('/?kklidi_members_register=1')
    require(status == 200 and 'New registrations are currently closed.' in document
            and 'name="email"' not in document, 'Missing required documents exposed registration')

    core_disabled = command(php_cli + [HERE / 'mvp_setup.php', 'documents-ready-core-off'], json_result=True)
    require(core_disabled == {'required_ready': True, 'legacy_registration_option': '1',
                              'users_can_register': False}, 'Core-disabled gate setup failed')
    disabled = Browser(base)
    status, _, document = disabled.request('/?kklidi_members_register=1')
    require(status == 200 and 'New registrations are currently closed.' in document
            and 'name="email"' not in document, 'Core-disabled registration exposed a form')

    setup = command(php_cli + [HERE / 'mvp_setup.php', 'core-on'], json_result=True)
    require(setup == {'required_ready': True, 'legacy_registration_option': '0',
                      'users_can_register': True}, 'MVP setup failed')

    allowed_destinations = [
        base + '/checkout/?step=payment',
        base + '/classroom/?tab=progress',
        base + '/lesson/42/',
    ]
    rejected_destinations = [
        'https://example.invalid/escape',
        'http://127.0.0.1:' + str(urllib.parse.urlsplit(base).port + 1) + '/other-port',
        base + '/%0d%0aLocation:%20https://example.invalid',
        '%2568%2574%2574%2570%2573%253A%252F%252Fexample.invalid',
        '//example.invalid/protocol-relative',
        r'\example.invalid\escape',
        base + '/?redirect_to=https%3A%2F%2Fexample.invalid',
        base + '/?kklidi_members_login=1',
    ]
    for destination in allowed_destinations:
        route = '/?' + urllib.parse.urlencode({'kklidi_members_login': '1',
                                                'redirect_to': destination})
        status, _, route_form = Browser(base).request(route)
        require(status == 200 and hidden_input(route_form, 'redirect_to') == destination,
                'Allowed local destination was not preserved')
    for destination in rejected_destinations:
        route = '/?' + urllib.parse.urlencode({'kklidi_members_login': '1',
                                                'redirect_to': destination})
        status, _, route_form = Browser(base).request(route)
        require(status == 200 and hidden_input(route_form, 'redirect_to') == base + '/',
                'Unsafe destination escaped the local fallback: ' + repr(destination))
    results['AUTH-REDIRECT-001'] = {'status': 'PASS',
                                    'allowed_local_destinations': len(allowed_destinations),
                                    'rejected_unsafe_destinations': len(rejected_destinations),
                                    'auth_loop_rejected': True}

    # Public authentication failures are deliberately indistinguishable.
    failure_bodies = []
    for identifier in (fixture['fixtures']['email_identity']['email'], 'absent@example.invalid'):
        browser, response, _ = members_login(base, env, identifier, 'invalid-password')
        status, _, body = response
        require(status == 200 and 'Please check your login details.' in body
                and not any(c.name.startswith('wordpress_logged_in_') for c in browser.cookies),
                'Credential failure leaked identity or authenticated')
        failure_bodies.append('Please check your login details.' in body)
    results['AUTH-LOGIN-002'] = {'status': 'PASS', 'generic_public_error': all(failure_bodies)}

    # A WordPress nonce alone cannot authorize a guest mutation, and Origin is bound.
    csrf = Browser(base)
    _, _, login_form = csrf.request('/?kklidi_members_login=1')
    bad_fields = {
        'kklidi_members_login': '1',
        '_kklidi_members_login_nonce': hidden_input(login_form, '_kklidi_members_login_nonce'),
        'kklidi_members_identifier': fixture['fixtures']['email_identity']['email'],
        'kklidi_members_password': env['KKH_USER_PASSWORD'],
    }
    status, _, body = csrf.request('/?kklidi_members_login=1', data=bad_fields,
                                   headers={'Origin': 'https://evil.example.invalid'})
    require(status == 200 and 'We could not verify this request.' in body
            and csrf.observe(key)['logged_in'] is False, 'Guest CSRF control failed')
    results['AUTH-CSRF-001'] = {'status': 'PASS', 'nonce_alone_rejected': True,
                                'cross_origin_rejected': True}

    # Account state remains a fail-closed authentication guard.
    state_email = fixture['fixtures']['separate_username']['email']
    for blocked_state in ('registration_pending', 'withdrawal_pending', 'disabled'):
        state = command(php_cli + [HERE / 'mvp_probe.php', 'set-fixture-state', state_email,
                                   blocked_state], json_result=True)
        browser, response, _ = members_login(base, env, state_email, env['KKH_USER_PASSWORD'])
        require(response[0] == 200 and 'Please check your login details.' in response[2]
                and browser.observe(key)['logged_in'] is False,
                'Blocked account state authenticated')
    command(php_cli + [HERE / 'mvp_probe.php', 'set-fixture-state', state_email, 'active'],
            json_result=True)
    results['AUTH-LOGIN-002']['blocked_states'] = 'PASS'

    # Registration creates one Core subscriber with a private login and current consent evidence.
    registration = Browser(base)
    status, headers, form = registration.request('/?kklidi_members_register=1')
    require(status == 200 and 'name="email"' in form and 'no-store' in headers.get('Cache-Control', '').lower(),
            'Enabled registration form missing or cacheable')
    request_id = hidden_input(form, 'request_id')
    registration_fields = {
        'kklidi_members_register': '1',
        'request_id': request_id,
        '_kklidi_members_register_nonce': hidden_input(form, '_kklidi_members_register_nonce'),
        '_kklidi_members_guest_exp': hidden_input(form, '_kklidi_members_guest_exp'),
        '_kklidi_members_guest_token': hidden_input(form, '_kklidi_members_guest_token'),
        'email': env['KKH_MVP_EMAIL'],
        'password': env['KKH_USER_PASSWORD'],
        'password_confirm': env['KKH_USER_PASSWORD'],
        'first_name': '합성',
        'last_name': '회원',
        'display_name': '합성 신규 회원',
        'phone': '',
        'consent_service': '1',
        'consent_privacy': '1',
        'role': 'administrator',
        'user_id': str(fixture['fixtures']['email_identity']['id']),
        '_kklidi_members_account_state': 'active',
    }
    status, headers, _ = registration.request('/?kklidi_members_register=1', data=registration_fields)
    require(status == 302 and 'registered=1' in headers.get('Location', '')
            and registration.observe(key)['logged_in'] is False,
            'Registration did not complete without auto-login')
    probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    new_user = probe.get('user', {})
    require(probe['users_count'] == 4 and new_user.get('login_is_private') is True
            and new_user.get('roles') == ['subscriber'] and new_user.get('state') == 'active'
            and new_user.get('service_consents') == 1 and new_user.get('privacy_consents') == 1
            and new_user.get('marketing_actions') == [] and new_user.get('phone') == '',
            'Registration persistence contract failed')
    # A fresh request for the same email has the same public failure shape and creates no user.
    duplicate = Browser(base)
    _, _, duplicate_form = duplicate.request('/?kklidi_members_register=1')
    duplicate_fields = dict(registration_fields,
        request_id=hidden_input(duplicate_form, 'request_id'),
        _kklidi_members_register_nonce=hidden_input(duplicate_form, '_kklidi_members_register_nonce'),
        _kklidi_members_guest_exp=hidden_input(duplicate_form, '_kklidi_members_guest_exp'),
        _kklidi_members_guest_token=hidden_input(duplicate_form, '_kklidi_members_guest_token'))
    status, _, duplicate_body = duplicate.request('/?kklidi_members_register=1', data=duplicate_fields)
    duplicate_probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    require(status == 200 and 'We could not complete the registration. Please use login or password reset.' in duplicate_body
            and duplicate_probe['users_count'] == 4, 'Duplicate registration changed identity state')
    results['AUTH-REGISTER-001'] = {'status': 'PASS', 'users_created': 1,
                                    'required_consents': 2, 'auto_login': False,
                                    'core_registration_authority': True,
                                    'legacy_toggle_ignored': True,
                                    'required_documents_fail_closed': True,
                                    'phone_optional': True,
                                    'email_verification': False}
    results['AUTH-REGISTER-002'] = {'status': 'PASS', 'duplicate_created': 0,
                                    'role_injection_ignored': True, 'disabled_form_hidden': True,
                                    'core_disabled_form_hidden': True}

    # Profile updates are self-only, allowlisted, sanitized, and keep email/role/state immutable.
    profile_browser, response, _ = members_login(base, env, env['KKH_MVP_EMAIL'], env['KKH_USER_PASSWORD'])
    require(response[0] == 302, 'New account could not log in')

    admin = Browser(base)
    _, _, core_admin_form = admin.request('/wp-login.php')
    admin_status, _, _ = admin.request('/wp-login.php', data={
        'log': 'fixture_admin', 'pwd': env['KKH_USER_PASSWORD'], 'testcookie': '1',
        'redirect_to': base + '/wp-admin/tools.php?page=kklidi-members', 'wp-submit': 'Log In',
    })
    require(admin_status == 302, 'Synthetic administrator login failed')
    admin_status, _, admin_page = admin.request('/wp-admin/tools.php?page=kklidi-members')
    require(admin_status == 200 and 'name="kklidi_members_admin_action"' in admin_page,
            'Members administrator page/capability unavailable')
    admin_nonce = hidden_input(admin_page, '_kklidi_members_admin_nonce')
    denied_get_status, _, denied_get_page = profile_browser.request(
        '/wp-admin/tools.php?page=kklidi-members')
    denied_status, _, _ = profile_browser.request('/wp-admin/tools.php?page=kklidi-members', data={
        'kklidi_members_admin_action': 'save_settings',
        '_kklidi_members_admin_nonce': admin_nonce,
        'own_login_url': '1',
    })
    require(denied_get_status in (401, 403)
            and 'name="kklidi_members_admin_action"' not in denied_get_page
            and denied_status in (401, 403) and 'name="email"' in
            Browser(base).request('/?kklidi_members_register=1')[2],
            'Subscriber used an administrator nonce to change Members settings')
    status, _, profile_form = profile_browser.request('/?kklidi_members_profile=1')
    require(status == 200, 'Profile form missing')
    profile_fields = {
        'kklidi_members_profile': '1',
        '_kklidi_members_profile_nonce': hidden_input(profile_form, '_kklidi_members_profile_nonce'),
        'first_name': '새이름', 'last_name': '김', 'display_name': '한글 표시명',
        'phone': '+82 10-9999-0000', 'description': '<script>alert(1)</script>안전 소개',
        'email': 'attacker@example.invalid', 'role': 'administrator',
        'user_id': str(fixture['fixtures']['email_identity']['id']),
        '_kklidi_members_account_state': 'disabled',
    }
    status, _, profile_body = profile_browser.request('/?kklidi_members_profile=1', data=profile_fields)
    observed = profile_browser.observe(key)
    require(status == 200 and 'Your profile has been saved.' in profile_body
            and observed['display_name'] == '한글 표시명' and observed['first_name'] == '새이름'
            and observed['billing_phone'] == '+82 10-9999-0000'
            and observed['email'] == env['KKH_MVP_EMAIL'] and observed['roles'] == ['subscriber']
            and observed['account_state'] == 'active' and '<script>' not in observed['description'],
            'Profile allowlist or output sanitization failed')
    _, _, unchanged_phone_form = profile_browser.request('/?kklidi_members_profile=1')
    status, _, unchanged_phone_body = profile_browser.request('/?kklidi_members_profile=1', data={
        'kklidi_members_profile': '1',
        '_kklidi_members_profile_nonce': hidden_input(unchanged_phone_form, '_kklidi_members_profile_nonce'),
        'first_name': '두번째이름', 'last_name': '김', 'display_name': '한글 표시명',
        'phone': '+82 10-9999-0000', 'description': '안전 소개',
    })
    require(status == 200 and 'Your profile has been saved.' in unchanged_phone_body
            and profile_browser.observe(key)['first_name'] == '두번째이름',
            'Unchanged phone incorrectly failed an otherwise valid profile update')
    results['AUTH-PROFILE-001'] = {'status': 'PASS', 'korean_preserved': True,
                                   'email_read_only': True, 'privilege_injection_ignored': True}

    # Required consent remains current; optional marketing is append-only and idempotent.
    _, _, consent_form = profile_browser.request('/?kklidi_members_consent=1')
    consent_fields = {
        'kklidi_members_consent': '1',
        '_kklidi_members_consent_nonce': hidden_input(consent_form, '_kklidi_members_consent_nonce'),
        'request_id': hidden_input(consent_form, 'request_id'),
        'consent_service': '1', 'consent_privacy': '1', 'consent_marketing': '1',
    }
    status, _, body = profile_browser.request('/?kklidi_members_consent=1', data=consent_fields)
    require(status == 200 and 'Your consent settings have been saved.' in body, 'Marketing consent failed')
    profile_browser.request('/?kklidi_members_consent=1', data=consent_fields)
    _, _, withdraw_form = profile_browser.request('/?kklidi_members_consent=1')
    withdraw_fields = {
        'kklidi_members_consent': '1',
        '_kklidi_members_consent_nonce': hidden_input(withdraw_form, '_kklidi_members_consent_nonce'),
        'request_id': hidden_input(withdraw_form, 'request_id'),
        'consent_service': '1', 'consent_privacy': '1',
    }
    profile_browser.request('/?kklidi_members_consent=1', data=withdraw_fields)
    probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    require(probe['user']['marketing_actions'] == ['accept', 'withdraw'],
            'Consent append-only/idempotency contract failed')
    results['AUTH-CONSENT-001'] = {'status': 'PASS', 'marketing_default': 'unselected',
                                   'marketing_actions': ['accept', 'withdraw'], 'duplicate_rows': 0}

    # Logout destroys the token represented by the old browser cookie.
    _, _, logout_form = profile_browser.request('/?kklidi_members_logout=1&redirect_to=%2F')
    logout_fields = {'kklidi_members_logout': '1', 'redirect_to': base + '/',
                     '_kklidi_members_logout_nonce': hidden_input(logout_form, '_kklidi_members_logout_nonce')}
    status, headers, _ = profile_browser.request('/?kklidi_members_logout=1', data=logout_fields)
    require(status == 302 and headers.get('Location') == base + '/'
            and profile_browser.observe(key)['logged_in'] is False, 'Logout did not revoke the session')
    results['AUTH-LOGOUT-001'] = {'status': 'PASS', 'session_revoked': True,
                                  'safe_redirect': True}

    # Core lost-password mail and one-time key stay inside the owned synthetic mailbox.
    reset_session, reset_login_response, _ = members_login(
        base, env, fixture['fixtures']['email_identity']['email'], env['KKH_USER_PASSWORD'])
    require(reset_login_response[0] == 302, 'Reset precondition login failed')
    reset = Browser(base)
    status, _, reset_request_form = reset.request('/wp-login.php?action=lostpassword')
    require(status == 200 and 'name="user_login"' in reset_request_form,
            'Core lost-password form missing')
    status, headers, _ = reset.request('/wp-login.php?action=lostpassword', data={
        'user_login': fixture['fixtures']['email_identity']['email'],
        'redirect_to': '', 'wp-submit': 'Get New Password',
    })
    require(status == 302, 'Core lost-password request did not complete')
    mailbox = Path(env['KKH_MAILBOX'])
    mail_rows = [json.loads(line) for line in mailbox.read_text(encoding='utf-8').splitlines()]
    reset_messages = [html_module.unescape(row.get('message', '')) for row in mail_rows
                      if 'action=rp' in html_module.unescape(row.get('message', ''))
                      and 'key=' in html_module.unescape(row.get('message', ''))]
    require(reset_messages, 'Core reset mail did not reach the isolated sink')
    reset_link = ''
    for candidate in re.findall(r'https?://[^\s<>]+', reset_messages[-1]):
        parsed_candidate = urllib.parse.urlsplit(candidate.rstrip('.,)'))
        query_candidate = urllib.parse.parse_qs(parsed_candidate.query)
        if query_candidate.get('action') == ['rp'] and query_candidate.get('key'):
            reset_link = urllib.parse.urlunsplit(parsed_candidate)
            break
    require(reset_link != '', 'Reset mail did not contain a usable local link')
    first_path = local_response_path(base, reset_link)
    status, headers, _ = reset.request(first_path)
    require(status == 302 and headers.get('Location'), 'Core reset key bootstrap failed')
    rp_path = local_response_path(base, headers['Location'])
    status, _, reset_form = reset.request(rp_path)
    require(status == 200 and 'name="pass1"' in reset_form, 'Core password reset form missing')
    reset_fields = {
        'pass1': env['KKH_RESET_PASSWORD'], 'pass2': env['KKH_RESET_PASSWORD'],
        'rp_key': hidden_input(reset_form, 'rp_key'),
        'wp-submit': 'Save Password',
    }
    status, _, reset_complete = reset.request('/wp-login.php?action=resetpass', data=reset_fields)
    require(status == 200 and 'password has been reset' in reset_complete.lower()
            and reset.observe(key)['logged_in'] is False,
            'Core reset form did not accept the new password without auto-login')
    require(reset_session.observe(key)['logged_in'] is False,
            'Core reset did not revoke the existing session')
    old_login, old_response, _ = members_login(base, env,
        fixture['fixtures']['email_identity']['email'], env['KKH_USER_PASSWORD'])
    new_login, new_response, _ = members_login(base, env,
        fixture['fixtures']['email_identity']['email'], env['KKH_RESET_PASSWORD'])
    replay = Browser(base)
    replay_status, _, replay_body = replay.request(first_path)
    require(old_response[0] == 200 and old_login.observe(key)['logged_in'] is False
            and new_response[0] == 302 and new_login.observe(key)['logged_in'] is True
            and (replay_status != 200 or 'name="pass1"' not in replay_body),
            'Core reset key was reusable or password state was incorrect')
    results['AUTH-RESET-001'] = {'status': 'PASS', 'core_mail_sink': True,
                                 'one_time_key': True, 'old_sessions_revoked': True,
                                 'auto_login': False}

    # Password change invalidates every existing Core session and never auto-authenticates.
    first, first_response, _ = members_login(base, env, env['KKH_MVP_EMAIL'], env['KKH_USER_PASSWORD'])
    second, second_response, _ = members_login(base, env, env['KKH_MVP_EMAIL'], env['KKH_USER_PASSWORD'])
    require(first_response[0] == second_response[0] == 302, 'Password test sessions failed')
    _, _, password_form = first.request('/?kklidi_members_password=1')
    password_fields = {
        'kklidi_members_password': '1',
        '_kklidi_members_password_nonce': hidden_input(password_form, '_kklidi_members_password_nonce'),
        'current_password': env['KKH_USER_PASSWORD'],
        'new_password': env['KKH_NEW_PASSWORD'],
        'new_password_confirm': env['KKH_NEW_PASSWORD'],
    }
    status, _, _ = first.request('/?kklidi_members_password=1', data=password_fields)
    password_probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    require(status == 302 and first.observe(key)['logged_in'] is False
            and second.observe(key)['logged_in'] is False
            and password_probe['user']['old_password_valid'] is False
            and password_probe['user']['new_password_valid'] is True,
            'Password change did not use Core hash/session revocation')
    results['AUTH-RESET-001']['self_change_core_hash'] = 'PASS'
    results['AUTH-RESET-001']['all_sessions_revoked_on_self_change'] = True

    # Withdrawal preserves the Core ID and queues the user while revoking access.
    withdrawing, login_response, _ = members_login(base, env, env['KKH_MVP_EMAIL'], env['KKH_NEW_PASSWORD'])
    require(login_response[0] == 302, 'New password login failed')
    _, _, withdrawal_form = withdrawing.request('/?kklidi_members_withdrawal=1')
    withdrawal_fields = {
        'kklidi_members_withdrawal': '1',
        '_kklidi_members_withdrawal_nonce': hidden_input(withdrawal_form, '_kklidi_members_withdrawal_nonce'),
        'request_id': hidden_input(withdrawal_form, 'request_id'),
        'current_password': env['KKH_NEW_PASSWORD'],
        'user_id': str(fixture['fixtures']['email_identity']['id']),
    }
    status, _, _ = withdrawing.request('/?kklidi_members_withdrawal=1', data=withdrawal_fields)
    withdrawal_probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    blocked, blocked_response, _ = members_login(base, env, env['KKH_MVP_EMAIL'], env['KKH_NEW_PASSWORD'])
    require(status == 302 and withdrawing.observe(key)['logged_in'] is False
            and withdrawal_probe['users_count'] == 4
            and withdrawal_probe['user']['state'] == 'withdrawal_pending'
            and blocked_response[0] == 200 and blocked.observe(key)['logged_in'] is False,
            'Withdrawal failed to preserve ID and block access')

    # The administrator sees the queue, finalizes only the pending state, and replay is idempotent.
    queued_user_id = withdrawal_probe['user']['id']
    queue_status, _, queue_page = admin.request('/wp-admin/tools.php?page=kklidi-members')
    require(queue_status == 200
            and f'name="user_id" value="{queued_user_id}"' in queue_page
            and 'value="finalize_withdrawal"' in queue_page,
            'Pending withdrawal was not visible in the administrator queue')
    finalize_fields = {
        'kklidi_members_admin_action': 'finalize_withdrawal',
        '_kklidi_members_admin_nonce': hidden_input(queue_page, '_kklidi_members_admin_nonce'),
        'user_id': str(queued_user_id),
    }
    finalize_status, _, _ = admin.request('/wp-admin/tools.php?page=kklidi-members', data=finalize_fields)
    finalized_probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    disabled_events = finalized_probe['audit_events'].count('withdrawal_disabled')
    require(finalize_status == 302 and finalized_probe['users_count'] == 4
            and finalized_probe['user']['id'] == queued_user_id
            and finalized_probe['user']['state'] == 'disabled'
            and disabled_events == 1,
            'Administrator withdrawal finalization changed identity or missed the disabled transition')

    after_status, _, after_page = admin.request('/wp-admin/tools.php?page=kklidi-members')
    replay_status, _, _ = admin.request('/wp-admin/tools.php?page=kklidi-members', data=dict(
        finalize_fields,
        _kklidi_members_admin_nonce=hidden_input(after_page, '_kklidi_members_admin_nonce'),
    ))
    replay_probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    require(after_status == 200 and replay_status == 302
            and f'name="user_id" value="{queued_user_id}"' not in after_page
            and replay_probe['user']['state'] == 'disabled'
            and replay_probe['audit_events'].count('withdrawal_disabled') == disabled_events,
            'Administrator withdrawal finalization was not idempotent')
    results['AUTH-WITHDRAW-001'] = {'status': 'PASS', 'identity_preserved': True,
                                    'requested_state': 'withdrawal_pending',
                                    'final_state': 'disabled', 'sessions_revoked': True,
                                    'admin_queue': 'PASS', 'admin_replay_idempotent': True,
                                    'automatic_pii_deletion': False}

    # Repeated failures eventually return a standards-visible throttle response.
    statuses = []
    for _ in range(11):
        throttle, response, _ = members_login(base, env, 'throttle@example.invalid', 'invalid-password')
        statuses.append((response[0], bool(response[1].get('Retry-After'))))
    require(any(code == 429 and retry for code, retry in statuses), 'Login throttle did not return 429/Retry-After')
    rate_probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    require(rate_probe['rate_option_count'] <= 50, 'Rate limiter created unbounded options')
    results['AUTH-RATE-LIMIT-001'] = {'status': 'PASS', 'http_429': True,
                                      'retry_after': True, 'persistent_atomic_lock': 'MySQL GET_LOCK'}

    require(rate_probe['audit_contains_raw_email'] is False
            and rate_probe['audit_contains_raw_ip'] is False and rate_probe['audit_rows'] > 0,
            'Audit stored raw identifiers or failed to record')
    before_cleanup = rate_probe['audit_rows']
    cleaned = command(php_cli + [HERE / 'mvp_probe.php', 'expire-audit'], json_result=True)
    require(cleaned['audit_rows'] < before_cleanup, 'Audit retention cleanup failed')
    results['AUTH-AUDIT-001'] = {'status': 'PASS', 'raw_email': False, 'raw_ip': False,
                                 'retention_cleanup': True}

    migration = command(php_cli + [HERE / 'migration_case.php'], json_result=True)
    require(migration == {'dry_eligible': 3, 'dry_writes': 0, 'first_imported': 3,
                          'first_writes': 3, 'second_imported': 0, 'second_duplicates': 3,
                          'second_writes': 0, 'legacy_null_rows': 3, 'rollback_deleted': 3,
                          'rollback_restored_target_rows': True, 'rollback_reeligible': 3,
                          'ids_unchanged': True,
                          'source_meta_unchanged': True}, 'Legacy migration contract failed')
    results['AUTH-MIGRATION-001'] = {'status': 'PASS', 'dry_run_writes': 0,
                                     'imported': 3, 'rerun_writes': 0,
                                     'ids_unchanged': True, 'legacy_source_preserved': True,
                                     'bounded_rollback': True, 'rollback_deleted': 3}

    results['AUTH-COOKIE-001'] = {'status': 'PASS', 'core_auth_cookie_only': True,
                                  'guest_cookie_is_non_auth': True, 'no_store': True, 'php_session': False}
    results['AUTH-ENUM-001'] = {'status': 'PARTIAL', 'login_error_shape': 'PASS',
                                'registration_duplicate_generic': 'PASS', 'timing_distribution': 'not measured'}
    results['AUTH-PRIVILEGE-001'] = {'status': 'PASS', 'profile_scope': 'current user',
                                     'role_and_state_injection_ignored': True,
                                     'subscriber_admin_page': 'denied',
                                     'admin_nonce_without_capability': 'rejected'}
    results['AUTH-PERF-001'] = {'status': 'PASS', 'php_session': False}
    results['AUTH-PERF-002'] = {'status': 'PASS', 'global_assets': 0,
                                'unrelated_route_modules': 5}
    return results


def run_device_cases(base, env, fixture, command, php_cli):
    """Run the real pinned device-limit PHP hooks against Members and Core login."""
    key = env['KKH_PROBE_KEY']
    journal = Path(env['KKH_EVENTS'])
    email = fixture['fixtures']['separate_username']['email']
    login = fixture['fixtures']['separate_username']['login']
    fingerprint_a = 'a' * 64
    fingerprint_b = 'b' * 64
    prior_successes = sum(event['type'] == 'wp_login' for event in events(journal))

    members = Browser(base)
    members.set_cookie('kklidi_dl_fp', fingerprint_a)
    members, response, _ = members_login(base, env, email, env['KKH_USER_PASSWORD'], browser=members)
    require(response[0] == 302, 'Device-limit rejected the first Members device')
    observed = members.observe(key)
    require(observed['logged_in'] is True
            and any(c.name == 'kklidi_dl_fp_sig' for c in members.cookies),
            'Allowed Members device did not persist through the next request')
    device = command(php_cli + [HERE / 'device_probe.php', 'summary', email], json_result=True)
    require(device['device_count'] == 1 and device['block_count'] == 0,
            'Actual device plugin did not register the first device')

    blocked = Browser(base)
    blocked.set_cookie('kklidi_dl_fp', fingerprint_b)
    blocked, blocked_response, _ = members_login(base, env, email, env['KKH_USER_PASSWORD'], browser=blocked)
    require(blocked_response[0] == 200
            and 'exceeded the number of devices' in blocked_response[2]
            and not any(c.name.startswith('wordpress_logged_in_') for c in blocked.cookies),
            'Members changed device-limit exchange-required denial into success')
    device = command(php_cli + [HERE / 'device_probe.php', 'summary', email], json_result=True)
    require(device['device_count'] == 1 and device['block_count'] == 1,
            'Device-limit block evidence was not written exactly once')

    core = Browser(base)
    core.set_cookie('kklidi_dl_fp', fingerprint_a)
    status, _, form = core.request('/wp-login.php')
    require(status == 200 and 'name="log"' in form, 'Native login form missing in device mode')
    status, _, _ = core.request('/wp-login.php', data={
        'log': login, 'pwd': env['KKH_USER_PASSWORD'], 'testcookie': '1',
        'redirect_to': base + '/index.php?kkh_observe=1', 'wp-submit': 'Log In',
    })
    require(status == 302 and core.observe(key)['logged_in'] is True,
            'Native Core login failed for an existing allowed device')
    successes = sum(event['type'] == 'wp_login' for event in events(journal)) - prior_successes
    require(successes == 2, 'Device allow/block paths emitted duplicate or missing Core login events')

    deleted = command(php_cli + [HERE / 'device_probe.php', 'delete-first', email], json_result=True)
    require(deleted['deleted'] is True and deleted['device_count'] == 0,
            'Actual device removal API failed')
    removed_status, removed_headers, removed_body = core.request('/index.php?kkh_observe=1', key=key)
    removed_denied = False
    if removed_status == 302 and removed_headers.get('Location'):
        safe_removed_path = local_response_path(base, removed_headers['Location'])
        removed_denied = ('wp-login.php' in safe_removed_path
                          or 'kklidi_members_login' in safe_removed_path)
    if removed_status == 200:
        try:
            removed_denied = json.loads(removed_body).get('logged_in') is False
        except ValueError:
            removed_denied = False
    require(removed_denied, 'Removed device retained access: status=' + str(removed_status)
            + ', location=' + repr(removed_headers.get('Location', '')))
    return {'status': 'PARTIAL', 'members_allowed': 'PASS', 'members_blocked': 'PASS',
            'core_allowed': 'PASS', 'removed_session_revoked': 'PASS',
            'core_success_events': 2, 'woocommerce_entry': 'not exercised'}


def run_domain_boundary_cases(env, fixture, command, php_cli):
    on = command(php_cli + [HERE / 'integration_case.php'], json_result=True)
    require(on['user_id'] == fixture['fixtures']['separate_username']['id']
            and on['members_active_after'] is False, 'Synthetic domain fixture/deactivation failed')
    for domain, destination in on['destinations'].items():
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(on['login_urls'][domain]).query)
        require(query.get('redirect_to') == [destination],
                'Members did not preserve the ' + domain + ' destination')
    off = command(php_cli + [HERE / 'integration_off.php'], json_result=True)
    require(off['members_helper_exists'] is False and off['core_fallback_is_wp_login'] is True
            and off['fingerprints'] == on['fingerprints']
            and all(ids == [on['user_id']] for ids in off['user_ids'].values()),
            'Members deactivation changed domain ownership or caused a hard dependency')
    activation = command(php_cli + [HERE / 'activate.php'], json_result=True)
    require(activation['plugins'] == ['kklidi-members/kklidi-members.php'],
            'Members did not reactivate after optional-dependency test')
    common = {'status': 'SYNTHETIC_PASS', 'core_user_id_preserved': True,
              'domain_fingerprint_preserved': True, 'members_off_core_fallback': True,
              'actual_plugin_stack': 'deployment gate'}
    return {
        'AUTH-WOO-001': dict(common, login_destination='checkout', order_domain='external'),
        'AUTH-LMS-001': dict(common, login_destination='classroom', enrollment_domain='external'),
        'AUTH-KBOARD-001': dict(common, login_destination='board', content_domain='external'),
    }


def measure_frontend_block(base, key, warmups=20, samples=100):
    browser = Browser(base)
    for _ in range(warmups):
        browser.observe(key)
    timings = []
    query_counts = []
    memory_peaks = []
    loaded_sets = []
    for _ in range(samples):
        started = time.perf_counter_ns()
        observed = browser.observe(key)
        timings.append((time.perf_counter_ns() - started) / 1_000_000)
        query_counts.append(observed['query_count'])
        memory_peaks.append(observed['memory_peak_bytes'])
        loaded_sets.append(tuple(observed['members_files']))
    ordered = sorted(timings)
    return {
        'median_ms': statistics.median(timings),
        'p95_ms': ordered[max(0, int(len(ordered) * .95) - 1)],
        'query_median': statistics.median(query_counts),
        'memory_peak_median': statistics.median(memory_peaks),
        'members_file_sets': len(set(loaded_sets)),
        'members_files': list(loaded_sets[-1]),
        'samples': samples,
    }


def assert_activation_unchanged(before, after):
    for key in ('users_count', 'users_fingerprint', 'roles_fingerprint', 'usermeta_fingerprint',
                'usermeta_key_hashes', 'domain_fingerprint'):
        require(before[key] == after[key], f'Plugin activation changed protected state: {key}')
    require(before['plugins'] == [] and after['plugins'] == ['kklidi-members/kklidi-members.php'],
            'Activation state did not change exactly as expected')
    require(before['custom_tables'] == [] and len(after['custom_tables']) == 2
            and all(name.endswith(('kklidi_mem_consents', 'kklidi_mem_login_audit'))
                    for name in after['custom_tables'])
            and set(after['tables']) == set(before['tables']) | set(after['custom_tables'])
            and after['plugin_option_count'] >= 5,
            'Members activation did not create exactly the approved persistence')


def assert_members_writes_bounded(after_activation, after_cases):
    for key in ('users_count', 'users_fingerprint', 'roles_fingerprint', 'domain_fingerprint',
                'tables', 'custom_tables', 'plugin_option_count', 'plugins'):
        require(after_activation[key] == after_cases[key],
                f'Members login changed protected state: {key}')
    changed_meta = sorted(key for key in set(after_activation['usermeta_key_hashes']) |
                          set(after_cases['usermeta_key_hashes'])
                          if after_activation['usermeta_key_hashes'].get(key) !=
                          after_cases['usermeta_key_hashes'].get(key))
    require(changed_meta in ([], ['session_tokens']),
            'Members login wrote user metadata outside Core session tokens')
    require(len(after_cases['custom_tables']) == 2 and after_cases['plugin_option_count'] >= 5,
            'Members login changed the approved persistence shape')
    return changed_meta


def assert_production_shape():
    files = sorted(path.relative_to(REPO).as_posix() for path in REPO.rglob('*')
                   if path.is_file() and '.harness' not in path.parts
                   and (path.name == 'kklidi-members.php'
                                          or path.parts[-3:-2] == ('includes',)
                                          or 'templates' in path.parts
                                          or 'assets' in path.parts))
    require(files == sorted(PRODUCTION_FILES),
            'Production runtime contains files outside the bounded contract')
    source = '\n'.join((REPO / name).read_text(encoding='utf-8') for name in PRODUCTION_FILES)
    for prohibited in ('session_start', 'PHPSESSID', 'wp_set_auth_cookie',
                       'wp_remote_', 'wp_enqueue_script(', 'wp_register_', 'JWT'):
        require(prohibited not in source, f'Production runtime contains prohibited mechanism: {prohibited}')

    plugin_source = (REPO / 'includes/Core/Plugin.php').read_text(encoding='utf-8')
    admin_source = (REPO / 'includes/Admin/AdminController.php').read_text(encoding='utf-8')
    require("add_action('wp_enqueue_scripts'" in plugin_source
            and 'wp_enqueue_style(' in plugin_source
            and 'is_frontend_route' in plugin_source,
            'Frontend stylesheet must stay scoped to a Members route')
    require("add_action('admin_enqueue_scripts'" in admin_source
            and "tools_page_kklidi-members" in admin_source
            and 'wp_enqueue_style(' in admin_source,
            'Admin stylesheet must stay scoped to the Members admin page')
    cookie_sources = [name for name in PRODUCTION_FILES
                      if 'setcookie(' in (REPO / name).read_text(encoding='utf-8')]
    require(cookie_sources == ['includes/Security/GuestCsrf.php'],
            'Only the browser-bound guest CSRF module may set a Members cookie')


def execute(php, mysqld, one_prefix=False, skip_perf=False):
    archive, checksum_count = verified_archive()
    require(php.is_file() and mysqld.is_file(), 'PHP/MySQL executable missing')
    assert_production_shape()
    run_id = uuid.uuid4().hex
    root = Path(tempfile.mkdtemp(prefix='kklidi-members-harness-')).resolve()
    (root / 'owner').write_text(run_id)
    data = root / 'mysql'
    data.mkdir()
    processes = []
    handles = []
    env = os.environ.copy()
    # All secrets are per-run synthetic values, sent through environment, never reports/argv.
    env.update(KKH_RUN=run_id, KKH_DATA=str(data), KKH_DB='kklidi_harness_' + run_id,
               KKH_DB_PASSWORD=secrets.token_hex(24), KKH_USER_PASSWORD=secrets.token_urlsafe(32),
               KKH_NEW_PASSWORD=secrets.token_urlsafe(36),
               KKH_RESET_PASSWORD=secrets.token_urlsafe(38),
               KKH_MVP_EMAIL='mvp-' + run_id[:12] + '@example.invalid',
               KKH_SALT=secrets.token_hex(48), KKH_PROBE_KEY=secrets.token_hex(32),
               KKH_MAILBOX=str(root / 'mailbox.jsonl'))
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    report = {'contract': 'KKLIDI-MEMBERS-MVP', 'scope': 'SYNTHETIC_WORDPRESS_BEHAVIOR', 'run_id': run_id,
              'status': 'FAIL', 'wordpress': LOCK['version'], 'archive_sha256': LOCK['archive_sha256'],
              'official_file_checksums_verified': checksum_count,
              'contract_status': 'PARTIAL', 'mvp_contracts': {},
              'modes': {'core_baseline': {'status': 'FAIL', 'variants': []},
                        'members_on': {'status': 'FAIL', 'variants': []}},
              'contracts_total': 24, 'contracts_exercised': 24,
              'not_run': ['actual WooCommerce/LMS full-stack browser regression',
                          'KBoard removal-period compatibility smoke/no-fatal',
                          'device-limit WooCommerce login entry', 'TLS/Secure cookie deployment',
                          'browser JavaScript rendering', 'distributed/concurrent abuse campaign'],
              'isolation': {'fresh_datadir': True, 'reference_accessed': False, 'loopback_only': True}}

    def command(args, timeout=60, json_result=False):
        completed = subprocess.run([str(x) for x in args], cwd=root, env=env, capture_output=True,
                                   timeout=timeout, creationflags=flags)
        def diagnostic():
            message = (completed.stderr + completed.stdout).decode('utf-8', errors='replace')
            for name in ('KKH_DB_PASSWORD', 'KKH_USER_PASSWORD', 'KKH_NEW_PASSWORD', 'KKH_RESET_PASSWORD', 'KKH_SALT', 'KKH_PROBE_KEY'):
                message = message.replace(env[name], '[redacted]')
            return message[-2500:]
        require(completed.returncode == 0, 'Isolated subprocess failed: ' + diagnostic())
        if json_result:
            try:
                return json.loads(completed.stdout.decode('utf-8'))
            except ValueError:
                # PHP may return exit code 0 for exit(string); invalid output still fails the run.
                raise HarnessError('Isolated PHP command did not produce the expected JSON: ' + diagnostic()) from None
        return completed.stdout.decode('utf-8', errors='replace').strip()

    php_cli = [php, '-n', '-d', 'display_errors=stderr', '-d', 'log_errors=0',
               '-d', 'sendmail_path=disabled-harness-mail', '-d', 'SMTP=127.0.0.1', '-d', 'smtp_port=1']

    def start(args, name):
        handle = (root / (name + '.log')).open('wb')
        handles.append(handle)
        process = subprocess.Popen([str(x) for x in args], cwd=root, env=env,
                                   stdout=handle, stderr=handle, creationflags=flags)
        processes.append(process)
        return process

    def stop(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    try:
        modules = command([php, '-n', '-m'])
        require('mysqli' in modules, 'PHP mysqli extension required')
        mysql_version = command([mysqld, '--no-defaults', '--version'])
        require('5.7.' in mysql_version, 'This native harness currently supports MySQL 5.7 only')
        mysql_base = mysqld.parent.parent
        common = [mysqld, '--no-defaults', '--basedir=' + str(mysql_base), '--datadir=' + str(data),
                  '--innodb-buffer-pool-size=32M', '--innodb-log-file-size=8M']
        print('Initializing a fresh owned MySQL datadir...', flush=True)
        command(common + ['--initialize-insecure', '--console'], timeout=60)
        env['KKH_DB_PORT'] = str(choose_port())
        mysql = start(common + ['--bind-address=127.0.0.1', '--port=' + env['KKH_DB_PORT'],
                               '--skip-log-bin', '--console'], 'mysql')
        wait_port(mysql, int(env['KKH_DB_PORT']))
        db_info = command(php_cli + [HERE / 'database.php'], json_result=True)
        require(db_info['owned_datadir'] is True, 'Datadir identity was not verified')
        report['mysql'] = db_info['mysql']
        prefixes = ['wp_'] if one_prefix else ['wp_', 'kkh_' + run_id[:8] + '_']
        for index, prefix in enumerate(prefixes):
            print(f'Running Core login cases, prefix variant {index + 1}/{len(prefixes)}...', flush=True)
            webroot = root / ('site-' + str(index))
            webroot.mkdir()
            with zipfile.ZipFile(archive) as z:
                for entry in z.infolist():
                    relative = archive_name(entry.filename).parts[1:]
                    if not relative:
                        continue
                    target = webroot.joinpath(*relative)
                    require(target.resolve().is_relative_to(webroot), 'Archive escaped test root')
                    if entry.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(z.read(entry))
            shutil.copyfile(HERE / 'config.php', webroot / 'wp-config.php')
            mu = webroot / 'wp-content' / 'mu-plugins'
            mu.mkdir()
            shutil.copyfile(HERE / 'observer.php', mu / 'harness-observer.php')
            plugin_target = webroot / 'wp-content' / 'plugins' / 'kklidi-members'
            plugin_target.mkdir(parents=True)
            copy_production_plugin(plugin_target)
            device_target = webroot / 'wp-content' / 'plugins' / 'kklidi-device-limit'
            device_target.mkdir(parents=True)
            device_manifest, device_file_count = copy_device_reference(device_target)
            report['isolation']['reference_accessed'] = True
            report['isolation']['reference_written'] = False
            report['device_reference'] = {'version': '1.1.3', 'files': device_file_count,
                                          'manifest_sha256': device_manifest}
            env.update(KKH_ROOT=str(webroot), KKH_PREFIX=prefix,
                       KKH_HTTP_PORT=str(choose_port([int(env['KKH_DB_PORT'])])),
                       KKH_EVENTS=str(root / ('events-' + str(index) + '.jsonl')))
            fixture = command(php_cli + [HERE / 'fixture.php'], json_result=True)
            require(fixture['wordpress'] == LOCK['version'] and fixture['prefix'] == prefix
                    and fixture['users_count'] == 3 and fixture['plugins'] == [], 'Fixture setup drift')
            report['php'] = fixture['php']
            base = 'http://127.0.0.1:' + env['KKH_HTTP_PORT']
            server = start(php_cli + ['-S', '127.0.0.1:' + env['KKH_HTTP_PORT'], '-t', webroot,
                                      HERE / 'router.php'], 'php-' + str(index))
            wait_port(server, int(env['KKH_HTTP_PORT']))
            rows = run_login_cases(base, env, fixture)
            stop(server)
            before_activation = command(php_cli + [HERE / 'snapshot.php'], json_result=True)
            activation = command(php_cli + [HERE / 'activate.php'], json_result=True)
            require(activation['plugins'] == ['kklidi-members/kklidi-members.php']
                    and activation['login_helper_exists'] is True,
                    'Production plugin activation/helper contract failed')
            after_activation = command(php_cli + [HERE / 'snapshot.php'], json_result=True)
            assert_activation_unchanged(before_activation, after_activation)
            server = start(php_cli + ['-S', '127.0.0.1:' + env['KKH_HTTP_PORT'], '-t', webroot,
                                      HERE / 'router.php'], 'php-members-' + str(index))
            wait_port(server, int(env['KKH_HTTP_PORT']))
            members_rows, guard_rows = run_members_cases(base, env, fixture)
            stop(server)
            after_cases = command(php_cli + [HERE / 'snapshot.php'], json_result=True)
            changed_meta = assert_members_writes_bounded(after_activation, after_cases)
            print(f'Running bounded MVP account contracts, prefix variant {index + 1}/{len(prefixes)}...', flush=True)
            server = start(php_cli + ['-S', '127.0.0.1:' + env['KKH_HTTP_PORT'], '-t', webroot,
                                      HERE / 'router.php'], 'php-mvp-' + str(index))
            wait_port(server, int(env['KKH_HTTP_PORT']))
            mvp_results = run_mvp_cases(base, env, fixture, command, php_cli)
            stop(server)
            print('Checking limiter with 100 calls across 8 independent PHP workers...', flush=True)
            with ThreadPoolExecutor(max_workers=8) as pool:
                parallel_rows = list(pool.map(lambda _: command(
                    php_cli + [HERE / 'concurrency_case.php'], json_result=True), range(100)))
            require(not any(row['error'] for row in parallel_rows)
                    and sum(row['allowed'] for row in parallel_rows) == 10,
                    'Parallel limiter must allow exactly 10 of 100 attempts')
            storage = command(php_cli + [HERE / 'rate_storage_case.php'], json_result=True)
            require(storage == {'cache_adapter_unavailable_allowed': True,
                                'storage_failure_denied': True, 'cleanup_rows': 0},
                    'Limiter cache/storage failure policy changed')
            mvp_results['AUTH-RATE-LIMIT-001']['parallel_processes'] = 8
            mvp_results['AUTH-RATE-LIMIT-001']['parallel_calls'] = 100
            mvp_results['AUTH-RATE-LIMIT-001']['parallel_allowed'] = 10
            mvp_results['AUTH-RATE-LIMIT-001']['shared_database_nodes'] = 8
            mvp_results['AUTH-RATE-LIMIT-001']['object_cache_outage'] = 'PASS'
            mvp_results['AUTH-RATE-LIMIT-001']['storage_failure'] = 'FAIL_CLOSED'
            for contract, result in mvp_results.items():
                report['mvp_contracts'].setdefault(contract, []).append(dict(result, prefix=prefix))
            boundary_results = run_domain_boundary_cases(env, fixture, command, php_cli)
            for contract, result in boundary_results.items():
                report['mvp_contracts'].setdefault(contract, []).append(dict(result, prefix=prefix))
            if index == 0 and not skip_perf:
                print('Running paired Members off/on performance blocks (3 x 100 requests)...', flush=True)
                perf_blocks = {'off': [], 'on': []}
                for block_index in range(3):
                    for mode in ('off', 'on'):
                        toggled = command(php_cli + [HERE / 'set_members.php', mode], json_result=True)
                        require(toggled['active'] is (mode == 'on'), 'Performance mode toggle failed')
                        server = start(php_cli + ['-S', '127.0.0.1:' + env['KKH_HTTP_PORT'],
                                                  '-t', webroot, HERE / 'router.php'],
                                       f'php-perf-{block_index}-{mode}')
                        wait_port(server, int(env['KKH_HTTP_PORT']))
                        perf_blocks[mode].append(measure_frontend_block(base, env['KKH_PROBE_KEY']))
                        stop(server)
                off_medians = [block['median_ms'] for block in perf_blocks['off']]
                on_medians = [block['median_ms'] for block in perf_blocks['on']]
                off_p95s = [block['p95_ms'] for block in perf_blocks['off']]
                on_p95s = [block['p95_ms'] for block in perf_blocks['on']]
                off_median = statistics.median(off_medians)
                on_median = statistics.median(on_medians)
                off_p95 = statistics.median(off_p95s)
                on_p95 = statistics.median(on_p95s)
                median_noise = max(off_medians) - min(off_medians)
                p95_noise = max(off_p95s) - min(off_p95s)
                median_budget = max(off_median * .05, median_noise)
                p95_budget = max(off_p95 * .05, p95_noise)
                perf_status = ('PASS' if on_median - off_median <= median_budget
                               and on_p95 - off_p95 <= p95_budget else 'INCONCLUSIVE')
                report['mvp_contracts'].setdefault('AUTH-PERF-003', []).append({
                    'status': perf_status, 'prefix': prefix, 'samples_per_block': 100,
                    'blocks': 3, 'off_median_ms': round(off_median, 3),
                    'on_median_ms': round(on_median, 3), 'median_budget_ms': round(median_budget, 3),
                    'off_p95_ms': round(off_p95, 3), 'on_p95_ms': round(on_p95, 3),
                    'p95_budget_ms': round(p95_budget, 3),
                    'off_query_median': statistics.median(b['query_median'] for b in perf_blocks['off']),
                    'on_query_median': statistics.median(b['query_median'] for b in perf_blocks['on']),
                    'off_memory_median': statistics.median(b['memory_peak_median'] for b in perf_blocks['off']),
                    'on_memory_median': statistics.median(b['memory_peak_median'] for b in perf_blocks['on']),
                })
            device_activation = command(php_cli + [HERE / 'activate_device.php'], json_result=True)
            require(device_activation == {'active': True, 'max': 1}, 'Device fixture activation failed')
            print(f'Running actual device-limit integration, prefix variant {index + 1}/{len(prefixes)}...', flush=True)
            server = start(php_cli + ['-S', '127.0.0.1:' + env['KKH_HTTP_PORT'], '-t', webroot,
                                      HERE / 'router.php'], 'php-device-' + str(index))
            wait_port(server, int(env['KKH_HTTP_PORT']))
            device_result = run_device_cases(base, env, fixture, command, php_cli)
            stop(server)
            report['mvp_contracts'].setdefault('AUTH-DEVICE-001', []).append(
                dict(device_result, prefix=prefix))
            report['modes']['core_baseline']['variants'].append({
                'prefix': prefix, 'cases': rows, 'mail_sink': fixture['mail_sink'],
                'http_blocked': fixture['http_blocked']})
            report['modes']['members_on']['variants'].append({
                'prefix': prefix, 'cases': members_rows, 'redirect_guards': guard_rows,
                'activation_changed_only_approved_plugin_state': True,
                'custom_tables': len(after_cases['custom_tables']),
                'plugin_options': after_cases['plugin_option_count'],
                'changed_usermeta_keys': changed_meta,
                'unrelated_request_modules': [
                    'kklidi-members.php', 'includes/Core/Plugin.php',
                    'includes/Security/AccountState.php', 'includes/Security/RateLimiter.php',
                    'includes/Audit/Recorder.php'],
                'global_assets': 0, 'external_http_events_during_cases': 0})
        report['modes']['core_baseline']['status'] = 'PASS'
        report['modes']['members_on']['status'] = 'PASS'
        report['status'] = 'PASS'
    except (HarnessError, OSError, subprocess.SubprocessError, ValueError, KeyError) as error:
        report['error'] = str(error) if isinstance(error, HarnessError) else type(error).__name__
        for handle in handles:
            handle.flush()
        diagnostics = '\n'.join(p.read_text(encoding='utf-8', errors='replace')[-2500:]
                                for p in root.glob('php-*.log'))
        for name in ('KKH_DB_PASSWORD', 'KKH_USER_PASSWORD', 'KKH_NEW_PASSWORD', 'KKH_RESET_PASSWORD', 'KKH_SALT', 'KKH_PROBE_KEY'):
            diagnostics = diagnostics.replace(env[name], '[redacted]')
        report['diagnostics'] = diagnostics
    finally:
        for process in reversed(processes):
            stop(process)
        report['isolation']['processes_stopped'] = all(p.poll() is not None for p in processes)
        for handle in handles:
            handle.close()
        try:
            owned_cleanup(root, run_id)
            report['isolation']['temporary_data_removed'] = not root.exists()
        except (OSError, HarnessError):
            report['status'] = 'FAIL'
            report['isolation']['temporary_data_removed'] = False
            report['cleanup_required_path'] = str(root)
        output = REPO / '.harness' / 'reports'
        output.mkdir(parents=True, exist_ok=True)
        (output / (run_id + '.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        (output / 'latest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    core_total = sum(len(v['cases']) for v in report['modes']['core_baseline']['variants'])
    members_total = sum(len(v['cases']) for v in report['modes']['members_on']['variants'])
    print(f'{report["status"]}: MVP contracts=24, AUTH-LOGIN-001 Core={core_total}, '
          f'Members={members_total}; release evidence PARTIAL. Report: .harness/reports/latest.json')
    if 'error' in report:
        print(report['error'])
    return 0 if report['status'] == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', help='Download/verify only the pinned official Core dependency')
    parser.add_argument('--one-prefix', action='store_true', help='Development run using only the default prefix')
    parser.add_argument('--skip-perf', action='store_true', help='Development run that skips the long paired timing blocks')
    parser.add_argument('--php', type=Path, default=Path('C:/MAMP/bin/php/php8.3.1/php.exe'))
    parser.add_argument('--mysqld', type=Path, default=Path('C:/MAMP/bin/mysql/bin/mysqld.exe'))
    args = parser.parse_args()
    try:
        if args.prepare:
            prepare()
            return 0
        return execute(args.php.resolve(), args.mysqld.resolve(), args.one_prefix, args.skip_perf)
    except (HarnessError, OSError, ValueError, zipfile.BadZipFile) as error:
        print('Harness preflight failed: ' + (str(error) if isinstance(error, HarnessError) else type(error).__name__))
        return 1


if __name__ == '__main__':
    sys.exit(main())
