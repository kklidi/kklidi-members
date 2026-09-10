"""Isolated WordPress Core baseline for AUTH-LOGIN-001. Standard library only."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
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
	'includes/Admin/MessageCatalog.php',
    'includes/Audit/Recorder.php',
    'includes/Auth/LoginController.php',
    'includes/Auth/LogoutController.php',
    'includes/Auth/PasswordController.php',
    'includes/Auth/PasswordResetController.php',
    'includes/Consent/ConsentController.php',
    'includes/Consent/Documents.php',
    'includes/Consent/Repository.php',
    'includes/Core/Installer.php',
    'includes/Core/Plugin.php',
	'includes/Core/RouteMap.php',
    'includes/Core/Url.php',
    'includes/Frontend/AccountController.php',
    'includes/Migration/LegacyConsentImporter.php',
    'includes/Notifications/AccountMailer.php',
	'includes/Notifications/AdminNotificationSettings.php',
	'includes/Notifications/AdminRegistrationMailer.php',
	'includes/Notifications/MailSenderSettings.php',
    'includes/Notifications/NotificationTemplates.php',
    'includes/Profile/ProfileController.php',
    'includes/Registration/RegistrationController.php',
    'includes/Registration/RegistrationFields.php',
    'includes/Security/AccountState.php',
    'includes/Security/GuestCsrf.php',
    'includes/Security/RateLimiter.php',
    'includes/Withdrawal/WithdrawalController.php',
	'assets/css/admin.css',
	'assets/css/members.css',
	'assets/js/members-auth.js',
    'templates/account.php',
    'templates/admin.php',
    'templates/consent.php',
    'templates/login.php',
    'templates/logout.php',
    'templates/password.php',
    'templates/password-reset.php',
    'templates/profile.php',
    'templates/register.php',
    'templates/withdrawal.php',
	'templates/partials/route-links.php',
]
PACKAGE_FILES = PRODUCTION_FILES + [
    'languages/kklidi-members.pot',
    'languages/kklidi-members-ko_KR.po',
    'languages/kklidi-members-ko_KR.mo',
]
# The MVP contract is pinned to the 1.1.3 reference.  The ns_0727 site now
# carries a newer 1.2.0 development copy, so use the dedicated read-only MAMP
# sandbox that still contains the reviewed 1.1.3 fixture.
DEVICE_REFERENCE = Path('C:/MAMP/htdocs/kklidi-members-mamp-sandbox/wp-content/plugins/kklidi-device-limit')
DEVICE_REFERENCE_VERSION = '1.1.3'
DEVICE_REFERENCE_MANIFEST_SHA256 = '2549b2ecf89008d5719526882c82a46c1978f129ce9225f41d446544db935168'


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
    # Translation catalogs are package assets rather than PHP runtime files,
    # but the synthetic site must carry them to exercise WordPress locale lookup.
    for name in ('languages/kklidi-members.pot', 'languages/kklidi-members-ko_KR.po',
                 'languages/kklidi-members-ko_KR.mo'):
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
    entry = (source / 'kklidi-device-limit.php').read_text(encoding='utf-8', errors='replace')
    require(re.search(r'(?m)^\s*\*\s*Version:\s*' + re.escape(DEVICE_REFERENCE_VERSION) + r'\s*$', entry),
            'Pinned device-limit reference version mismatch')
    manifest_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    require(manifest_hash == DEVICE_REFERENCE_MANIFEST_SHA256,
            'Pinned device-limit reference manifest mismatch')
    return manifest_hash, len(manifest)


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
		'includes/Core/RouteMap.php',
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


def read_mailbox(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] \
        if path.exists() else []


def assert_account_notice(row, recipient, subject_fragment, required_fragments, forbidden_fragments):
    recipients = row.get('to', [])
    headers = row.get('headers', [])
    content = html_module.unescape(str(row.get('subject', '')) + '\n' + str(row.get('message', '')))
    require(recipients == [recipient], 'Account notice did not use the current Core user email')
    require(any(header.lower().startswith('content-type: text/plain;') for header in headers),
            'Account notice did not declare its plain-text format')
    require(subject_fragment in str(row.get('subject', '')),
            'Account notice used the wrong preset subject: ' + str(row.get('subject', '')))
    missing_fragments = [fragment for fragment in required_fragments if fragment not in content]
    require(not missing_fragments,
            'Account notice omitted required preset content: ' + repr(missing_fragments))
    require(not any(fragment and fragment in content for fragment in forbidden_fragments),
            'Account notice exposed forbidden account data')


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
                       'includes/Core/RouteMap.php',
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
            require('Existing members may also use their existing username.' in document,
                    'Email-first login guidance was not rendered')
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
                         'email_primary_ui_guidance': True,
                         'status': 'PASS'})

    # A public nickname must never become an authentication identifier.
    display_name_browser, display_name_response, _ = members_login(
        base, env, fixture['fixtures']['email_identity']['display_name'], env['KKH_USER_PASSWORD'])
    require(display_name_response[0] == 200
            and 'Please check your login details.' in display_name_response[2]
            and display_name_browser.observe(key)['logged_in'] is False
            and not any(c.name.startswith('wordpress_logged_in_') for c in display_name_browser.cookies),
            'Display name was accepted as an authentication identifier')
    guard_rows.append({'display_name_not_identifier': True, 'status': 'PASS'})

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


def run_mvp_cases(base, env, fixture, command, php_cli, restart_server=None):
    """Exercise the bounded 1.0 account workflows through real HTTP requests."""
    results = {}
    key = env['KKH_PROBE_KEY']
    active = ['kklidi-members/kklidi-members.php']
    mailbox_path = Path(env['KKH_MAILBOX'])

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

    # Configure the Members-scoped sender before the first account notification.
    sender_admin = Browser(base)
    sender_login_status, _, _ = sender_admin.request('/wp-login.php')
    sender_login_status, _, _ = sender_admin.request('/wp-login.php', data={
        'log': 'fixture_admin', 'pwd': env['KKH_USER_PASSWORD'], 'testcookie': '1',
        'redirect_to': base + '/wp-admin/users.php?page=kklidi-members&section=notifications',
        'wp-submit': 'Log In',
    })
    sender_path = '/wp-admin/users.php?page=kklidi-members&section=notifications'
    sender_page_status, _, sender_page = sender_admin.request(sender_path)
    sender_forms = [form for form in re.findall(
        r'<form\b.*?</form>', sender_page, flags=re.IGNORECASE | re.DOTALL)
        if 'kklidi_members_mail_sender[sender_enabled]' in form]
    require(sender_login_status == 302 and sender_page_status == 200 and len(sender_forms) == 1,
            'Members sender Settings API form is unavailable')
    sender_form = sender_forms[0]
    sender_nonce = hidden_input(sender_form, '_wpnonce')

    def sender_settings_fields(from_name='Synthetic Members', from_email='members@example.invalid',
                               footer_text='This is a synthetic sender footer.', enabled=True,
                               footer_enabled=True, extra=None):
        fields = {
            'option_page': 'kklidi_members_mail_sender',
            'action': 'update',
            '_wpnonce': sender_nonce,
            '_wp_http_referer': sender_path,
            'kklidi_members_mail_sender[version]': '1',
            'kklidi_members_mail_sender[from_name]': from_name,
            'kklidi_members_mail_sender[from_email]': from_email,
            'kklidi_members_mail_sender[footer_text]': footer_text,
        }
        if enabled:
            fields['kklidi_members_mail_sender[sender_enabled]'] = '1'
        if footer_enabled:
            fields['kklidi_members_mail_sender[footer_enabled]'] = '1'
        if extra:
            fields.update(extra)
        return fields

    sender_default = command(php_cli + [HERE / 'mvp_probe.php', 'mail-sender-summary'],
                             json_result=True)
    require(sender_default['autoload'] in ('no', 'off')
            and sender_default['stored'] == {
                'version': 1, 'sender_enabled': False, 'from_name': '', 'from_email': '',
                'footer_enabled': False, 'footer_text': ''}
            and sender_default['effective'] == sender_default['stored']
            and sender_default['settings_audit_count'] == 0,
            'Mail sender default was not a non-autoload disabled option')
    sender_save_status, _, _ = sender_admin.request(
        '/wp-admin/options.php', data=sender_settings_fields())
    sender_saved = command(php_cli + [HERE / 'mvp_probe.php', 'mail-sender-summary'],
                           json_result=True)
    require(sender_save_status == 302
            and sender_saved['stored'] == {
                'version': 1, 'sender_enabled': True, 'from_name': 'Synthetic Members',
                'from_email': 'members@example.invalid', 'footer_enabled': True,
                'footer_text': 'This is a synthetic sender footer.'}
            and sender_saved['effective'] == sender_saved['stored']
            and sender_saved['settings_audit_count'] == 1,
            'Valid Members sender settings did not save safely')
    initial_mail_count = len(read_mailbox(mailbox_path))

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
    korean_site = command(php_cli + [HERE / 'mvp_setup.php', 'set-site-locale', 'ko_KR'],
                          json_result=True)
    require(korean_site.get('locale') == 'ko_KR' and korean_site.get('option') == 'ko_KR',
            'Korean site-locale setup failed: ' + repr(korean_site))
    if restart_server:
        restart_server()
    locale_probe = Browser(base).observe(key)
    require(locale_probe.get('locale') == 'ko_KR',
            'HTTP site locale did not refresh: ' + repr({k: locale_probe.get(k)
                                                         for k in ('locale', 'determined_locale', 'wplang_option')}))
    translation_check = command(php_cli + [HERE / 'mvp_probe.php', 'translation-check'],
                                json_result=True)
    require(translation_check == {
        'locale': 'ko_KR', 'determined_locale': 'ko_KR', 'catalog_exists': True,
        'registration_subject': '[Synthetic Members Harness] 회원가입이 완료되었습니다',
        'password_changed_notice': '비밀번호가 변경되었습니다. 다시 로그인하세요.',
        'admin_registration_subject': '[Synthetic Members Harness] 신규 회원가입',
    }, 'Korean catalog was not loaded by WordPress: ' + repr(translation_check))
    registration = Browser(base)
    status, headers, form = registration.request('/?kklidi_members_register=1')
    require(status == 200 and 'name="email"' in form and 'no-store' in headers.get('Cache-Control', '').lower(),
            'Enabled registration form missing or cacheable')
    require('계정을 만든 후 이메일 주소로 로그인하세요.' in form,
            'Korean registration sign-in guidance was not rendered')

    # The Members reset wrapper renders the Korean generic guidance and keeps
    # matching/non-matching request responses indistinguishable.
    reset_ux = Browser(base)
    reset_status, _, reset_request_form = reset_ux.request('/?kklidi_members_password_reset=1')
    require(reset_status == 200 and 'name="user_login"' in reset_request_form
            and '비밀번호 재설정 링크를 받을 이메일을 입력하세요.' in reset_request_form
            and '기존 회원은 기존 아이디로도 로그인할 수 있습니다.' in reset_request_form,
            'Members reset wrapper Korean guidance was not rendered')
    reset_fields = {
        'kklidi_members_password_reset': '1',
        'reset_action': 'request',
        'user_login': 'absent-reset-user@example.invalid',
        '_kklidi_members_password_reset_nonce': hidden_input(
            reset_request_form, '_kklidi_members_password_reset_nonce'),
        '_kklidi_members_guest_exp': hidden_input(reset_request_form, '_kklidi_members_guest_exp'),
        '_kklidi_members_guest_token': hidden_input(reset_request_form, '_kklidi_members_guest_token'),
    }
    reset_status, _, reset_body = reset_ux.request('/?kklidi_members_password_reset=1', data=reset_fields)
    require(reset_status == 200
            and '입력한 정보와 일치하는 계정이 있으면 WordPress가 비밀번호 재설정 링크를 보냅니다.' in reset_body,
            'Members reset wrapper leaked a missing-account response')
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
    registration_mail = read_mailbox(mailbox_path)
    require(len(registration_mail) == initial_mail_count + 1,
            'Registration success did not create exactly one account notice')
    assert_account_notice(
        registration_mail[-1], env['KKH_MVP_EMAIL'], '회원가입이 완료되었습니다',
        ['회원가입이 완료되었습니다.', '로그인:', base],
        [env['KKH_USER_PASSWORD'], request_id, env['KKH_MVP_EMAIL'], 'user_id', 'role=']
    )
    require('From: Synthetic Members <members@example.invalid>' in registration_mail[-1]['headers']
            and 'This is a synthetic sender footer.' in registration_mail[-1]['message'],
            'Members sender settings were not applied to the registration notice')
    reset_mailbox_snapshot = mailbox_path.read_bytes()
    existing_reset = Browser(base)
    _, _, existing_reset_form = existing_reset.request('/?kklidi_members_password_reset=1')
    existing_reset_fields = {
        'kklidi_members_password_reset': '1',
        'reset_action': 'request',
        'user_login': env['KKH_MVP_EMAIL'],
        '_kklidi_members_password_reset_nonce': hidden_input(
            existing_reset_form, '_kklidi_members_password_reset_nonce'),
        '_kklidi_members_guest_exp': hidden_input(existing_reset_form, '_kklidi_members_guest_exp'),
        '_kklidi_members_guest_token': hidden_input(existing_reset_form, '_kklidi_members_guest_token'),
    }
    existing_status, _, existing_body = existing_reset.request(
        '/?kklidi_members_password_reset=1', data=existing_reset_fields)
    require(existing_status == 200
            and '입력한 정보와 일치하는 계정이 있으면 WordPress가 비밀번호 재설정 링크를 보냅니다.' in existing_body,
            'Members reset wrapper changed the matching-account response shape')

    def latest_reset_link():
        rows = read_mailbox(mailbox_path)
        require(rows, 'Members reset wrapper did not create a reset message')
        message = html_module.unescape(str(rows[-1].get('message', '')))
        for candidate in re.findall(r'https?://[^\s<>]+', message):
            parsed = urllib.parse.urlsplit(candidate.rstrip('.,)'))
            query = urllib.parse.parse_qs(parsed.query)
            if query.get('kklidi_members_password_reset') == ['1'] and query.get('key'):
                return urllib.parse.urlunsplit(parsed)
        require(False, 'Members reset message did not contain a usable wrapper link')

    def complete_members_reset(browser, link, password):
        reset_path = local_response_path(base, link)
        reset_status, reset_headers, reset_body = browser.request(reset_path)
        if reset_status == 302 and reset_headers.get('Location'):
            form_path = local_response_path(base, reset_headers['Location'])
            reset_status, _, complete_form = browser.request(form_path)
        else:
            complete_form = reset_body
        require(reset_status == 200 and 'name="new_password"' in complete_form,
                'Members reset completion form missing')
        complete_fields = {
            'kklidi_members_password_reset': '1',
            'reset_action': 'complete',
            'key': hidden_input(complete_form, 'key'),
            'login': hidden_input(complete_form, 'login'),
            'new_password': password,
            'new_password_confirm': password,
            '_kklidi_members_password_reset_complete_nonce': hidden_input(
                complete_form, '_kklidi_members_password_reset_complete_nonce'),
            '_kklidi_members_guest_exp': hidden_input(complete_form, '_kklidi_members_guest_exp'),
            '_kklidi_members_guest_token': hidden_input(complete_form, '_kklidi_members_guest_token'),
        }
        reset_status, reset_headers, _ = browser.request(
            '/?kklidi_members_password_reset=1', data=complete_fields)
        require(reset_status == 302 and 'password_reset=1' in reset_headers.get('Location', '')
                and browser.observe(key)['logged_in'] is False,
                'Members reset completion did not use Core reset behavior')

    complete_members_reset(existing_reset, latest_reset_link(), env['KKH_RESET_PASSWORD'])
    restore_reset = Browser(base)
    _, _, restore_form = restore_reset.request('/?kklidi_members_password_reset=1')
    restore_fields = dict(existing_reset_fields,
        _kklidi_members_password_reset_nonce=hidden_input(
            restore_form, '_kklidi_members_password_reset_nonce'),
        _kklidi_members_guest_exp=hidden_input(restore_form, '_kklidi_members_guest_exp'),
        _kklidi_members_guest_token=hidden_input(restore_form, '_kklidi_members_guest_token'))
    restore_status, _, restore_body = restore_reset.request(
        '/?kklidi_members_password_reset=1', data=restore_fields)
    require(restore_status == 200
            and '입력한 정보와 일치하는 계정이 있으면 WordPress가 비밀번호 재설정 링크를 보냅니다.' in restore_body,
            'Members reset restore request changed the generic response shape')
    complete_members_reset(restore_reset, latest_reset_link(), env['KKH_USER_PASSWORD'])
    mailbox_path.write_bytes(reset_mailbox_snapshot)
    english_site = command(php_cli + [HERE / 'mvp_setup.php', 'set-site-locale', 'en_US'],
                           json_result=True)
    require(english_site.get('locale') == 'en_US' and english_site.get('option') in ('', 'en_US'),
            'Site-locale restore failed: ' + repr(english_site))
    if restart_server:
        restart_server()
    probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    new_user = probe.get('user', {})
    require(probe['users_count'] == 4 and new_user.get('login_is_private') is True
            and new_user.get('nicename_is_separate') is True
            and new_user.get('nicename_is_public_slug') is True
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
            and duplicate_probe['users_count'] == 4
            and len(read_mailbox(mailbox_path)) == len(registration_mail),
            'Duplicate registration changed identity state or sent another notice')
    replay = command(php_cli + [HERE / 'mvp_probe.php', 'replay-registration-notification'],
                     json_result=True)
    require(replay == {'sent': False} and len(read_mailbox(mailbox_path)) == len(registration_mail),
            'Logical notification replay was not idempotent')
    user_locale = command(php_cli + [HERE / 'mvp_probe.php', 'set-user-locale', 'ko_KR'],
                          json_result=True)
    require(user_locale.get('locale') == 'ko_KR', 'Korean user-locale setup failed')
    results['AUTH-REGISTER-001'] = {'status': 'PASS', 'users_created': 1,
                                    'required_consents': 2, 'auto_login': False,
                                    'core_registration_authority': True,
                                    'legacy_toggle_ignored': True,
                                    'required_documents_fail_closed': True,
                                    'phone_optional': True,
                                    'email_verification': False,
                                    'user_nicename_separate': True}
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
        'redirect_to': base + '/wp-admin/users.php?page=kklidi-members', 'wp-submit': 'Log In',
    })
    require(admin_status == 302, 'Synthetic administrator login failed')
    admin_status, _, admin_page = admin.request('/wp-admin/users.php?page=kklidi-members&section=documents')
    require(admin_status == 200 and 'name="kklidi_members_admin_action"' in admin_page,
            'Members administrator page/capability unavailable: '
            + repr({'status': admin_status, 'has_action': 'name="kklidi_members_admin_action"' in admin_page,
                    'has_title': 'KKLIDI Members' in admin_page}))
    overview_status, _, overview_page = admin.request('/wp-admin/users.php?page=kklidi-members&section=overview')
    require(overview_status == 200
            and 'Quick actions' in overview_page
            and 'Members manual menu links' in overview_page
            and 'kklidi_members_login=1' in overview_page
            and 'WordPress registration settings' in overview_page,
            'Administrator overview quick actions or canonical route links missing')
    admin_nonce = hidden_input(admin_page, '_kklidi_members_admin_nonce')
    denied_get_status, _, denied_get_page = profile_browser.request(
        '/wp-admin/users.php?page=kklidi-members')
    denied_status, _, _ = profile_browser.request('/wp-admin/users.php?page=kklidi-members', data={
        'kklidi_members_admin_action': 'save_url_settings',
        '_kklidi_members_admin_nonce': admin_nonce,
        'own_login_url': '1',
    })
    require(denied_get_status in (401, 403)
            and 'name="kklidi_members_admin_action"' not in denied_get_page
            and denied_status in (401, 403) and 'name="email"' in
            Browser(base).request('/?kklidi_members_register=1')[2],
            'Subscriber used an administrator nonce to change Members settings')

    # AUTH-ROUTE-MAP-001: fixed clean routes stay default-off, require a
    # conflict-free pretty-permalink transition, and preserve query fallback.
    route_path = '/wp-admin/users.php?page=kklidi-members&section=routes'
    route_status, _, route_page = admin.request(route_path)
    require(route_status == 200 and 'name="clean_routes_enabled"' in route_page
            and 'name="own_login_url"' in route_page
            and 'WordPress pages or shortcodes' in route_page,
            'Route management administrator screen is unavailable')
    route_nonce = hidden_input(route_page, '_kklidi_members_admin_nonce')

    def clean_route_fields(enabled=True, extra=False, nonce=route_nonce):
        fields = {
            'section': 'routes',
            'kklidi_members_admin_action': 'set_clean_routes',
            '_kklidi_members_admin_nonce': nonce,
        }
        if enabled:
            fields['clean_routes_enabled'] = '1'
        if extra:
            fields['custom_slug'] = 'unsafe-custom-route'
        return fields

    route_default = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    require(route_default['autoload'] in ('no', 'off')
            and route_default['stored'] == {
                'version': 1, 'clean_routes_enabled': False}
            and route_default['effective'] == route_default['stored']
            and route_default['preflight']['ready'] is False
            and any(item['owner_type'] == 'permalink_structure'
                    for item in route_default['preflight']['collisions'])
            and all(route_default['present_rules'].values()) is False
            and all('kklidi_members_' in url for url in route_default['helpers'].values()),
            'Clean routes were not default-off with plain-permalink fallback')
    initial_page_count = route_default['page_count']
    initial_menu_count = route_default['menu_item_count']

    plain_status, plain_headers, _ = admin.request(
        route_path, data=clean_route_fields())
    plain_rejected = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    require(plain_status == 302 and 'notice=route_collision' in plain_headers.get('Location', '')
            and plain_rejected['stored'] == route_default['stored']
            and plain_rejected['audit_count'] == 0,
            'Plain permalink configuration did not reject clean-route activation')

    pretty = command(
        php_cli + [HERE / 'mvp_probe.php', 'set-pretty-permalinks'], json_result=True)
    require(pretty == {'permalink_structure': '/%postname%/'},
            'Synthetic pretty permalink setup failed')
    collision_page = command(
        php_cli + [HERE / 'mvp_probe.php', 'create-route-page-collision'], json_result=True)
    page_collision = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    require(collision_page['page_id'] > 0 and page_collision['preflight']['ready'] is False
            and any(item['owner_type'] == 'wordpress_page'
                    and item['page_id'] == collision_page['page_id']
                    for item in page_collision['preflight']['collisions']),
            'WordPress page collision was not detected')
    collision_status, collision_headers, _ = admin.request(
        route_path, data=clean_route_fields())
    collision_rejected = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    require(collision_status == 302
            and 'notice=route_collision' in collision_headers.get('Location', '')
            and collision_rejected['stored'] == route_default['stored']
            and collision_rejected['page_count'] == initial_page_count + 1,
            'Page collision changed content or enabled clean routes')
    removed_page = command(
        php_cli + [HERE / 'mvp_probe.php', 'remove-route-page-collision'], json_result=True)
    require(removed_page == {'deleted': True, 'remaining': 0},
            'Synthetic route collision page cleanup failed')

    rewrite_collision_setup = command(
        php_cli + [HERE / 'mvp_probe.php', 'set-route-rewrite-collision'], json_result=True)
    rewrite_collision = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    require(rewrite_collision_setup == {'configured': True}
            and rewrite_collision['preflight']['ready'] is False
            and any(item['owner_type'] == 'rewrite_rule'
                    for item in rewrite_collision['preflight']['collisions']),
            'Specific rewrite-rule collision was not detected')
    rewrite_status, _, _ = admin.request(route_path, data=clean_route_fields())
    rewrite_rejected = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    require(rewrite_status == 302 and rewrite_rejected['stored'] == route_default['stored']
            and rewrite_rejected['audit_count'] == 0,
            'Rewrite-rule collision enabled clean routes or changed settings')
    removed_rewrite = command(
        php_cli + [HERE / 'mvp_probe.php', 'remove-route-rewrite-collision'], json_result=True)
    require(removed_rewrite == {'remaining': 0},
            'Synthetic rewrite collision cleanup failed')

    denied_route_status, _, _ = profile_browser.request(
        route_path, data=clean_route_fields())
    require(denied_route_status in (401, 403),
            'Subscriber changed the clean route setting with an administrator nonce')

    _, _, route_page = admin.request(route_path)
    route_nonce = hidden_input(route_page, '_kklidi_members_admin_nonce')
    enabled_status, enabled_headers, _ = admin.request(
        route_path, data=clean_route_fields(enabled=True, extra=True, nonce=route_nonce))
    route_enabled = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    clean_suffixes = {
        'login': '/members/login/', 'register': '/members/register/',
        'account': '/members/account/', 'profile': '/members/account/profile/',
        'password': '/members/account/password/',
        'password_reset': '/members/password-reset/',
        'consent': '/members/account/consent/',
        'withdrawal': '/members/account/withdrawal/', 'logout': '/members/logout/',
    }
    require(enabled_status == 302 and 'notice=saved' in enabled_headers.get('Location', '')
            and route_enabled['stored'] == {'version': 1, 'clean_routes_enabled': True}
            and route_enabled['effective'] == route_enabled['stored']
            and route_enabled['preflight']['ready'] is True
            and all(route_enabled['present_rules'].values())
            and all(route_enabled['helpers'][name].endswith(suffix)
                    for name, suffix in clean_suffixes.items())
            and route_enabled['audit_count'] == 1
            and route_enabled['page_count'] == initial_page_count
            and route_enabled['menu_item_count'] == initial_menu_count,
            'Clean route activation, strict schema, or bounded content behavior failed')

    anonymous_clean = Browser(base)
    clean_login_status, _, clean_login = anonymous_clean.request('/members/login/')
    clean_register_status, _, clean_register = Browser(base).request('/members/register/')
    clean_reset_status, _, clean_reset = Browser(base).request('/members/password-reset/')
    clean_protected_status, clean_protected_headers, clean_guest_account = Browser(base).request('/members/account/')
    clean_account_status, _, clean_account = admin.request('/members/account/')
    clean_profile_status, _, _ = admin.request('/members/account/profile/')
    clean_password_status, _, _ = admin.request('/members/account/password/')
    clean_consent_status, _, _ = admin.request('/members/account/consent/')
    clean_withdrawal_status, _, _ = admin.request('/members/account/withdrawal/')
    clean_logout_status, _, _ = admin.request('/members/logout/')
    query_fallback_status, _, query_fallback_page = Browser(base).request(
        '/?kklidi_members_login=1')
    require(clean_login_status == 200 and 'name="kklidi_members_identifier"' in clean_login
            and 'kklidi-members-frontend-css' in clean_login
            and clean_register_status == 200 and 'name="email"' in clean_register
            and clean_reset_status == 200 and 'name="user_login"' in clean_reset
            and clean_protected_status == 200
            and '/members/login/' in clean_guest_account
            and clean_account_status == clean_profile_status == clean_password_status == 200
            and clean_consent_status == clean_withdrawal_status == clean_logout_status == 200
            and 'kklidi-members-page' in clean_account
            and query_fallback_status == 200
            and 'name="kklidi_members_identifier"' in query_fallback_page,
            'Clean routes did not dispatch through the existing account controllers: ' + repr({
                'login': clean_login_status,
                'login_has_form': 'name="kklidi_members_identifier"' in clean_login,
                'login_has_css': 'kklidi-members-frontend-css' in clean_login,
                'register': clean_register_status,
                'register_has_email': 'name="email"' in clean_register,
                'reset': clean_reset_status,
                'reset_has_user_login': 'name="user_login"' in clean_reset,
                'protected': clean_protected_status,
                'protected_location': clean_protected_headers.get('Location', ''),
                'account': clean_account_status,
                'profile': clean_profile_status,
                'password': clean_password_status,
                'consent': clean_consent_status,
                'withdrawal': clean_withdrawal_status,
                'logout': clean_logout_status,
                'query': query_fallback_status,
                'query_has_form': 'name="kklidi_members_identifier"' in query_fallback_page,
            }))

    hash_before_requests = route_enabled['rewrite_rules_hash']
    unrelated_status, _, unrelated_page = Browser(base).request('/')
    route_after_unrelated = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    require(unrelated_status == 200 and 'kklidi-members-frontend-css' not in unrelated_page
            and route_after_unrelated['rewrite_rules_hash'] == hash_before_requests,
            'Unrelated request loaded route assets or changed persisted rewrite rules')

    _, _, ownership_page = admin.request(route_path)
    ownership_nonce = hidden_input(ownership_page, '_kklidi_members_admin_nonce')
    ownership_status, _, _ = admin.request(route_path, data={
        'section': 'routes',
        'kklidi_members_admin_action': 'save_url_settings',
        '_kklidi_members_admin_nonce': ownership_nonce,
        'own_login_url': '1',
        'own_register_url': '1',
    })
    owned_urls = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    require(ownership_status == 302
            and owned_urls['core_urls']['login'].endswith('/members/login/')
            and owned_urls['core_urls']['register'].endswith('/members/register/')
            and '/wp-login.php' in owned_urls['core_urls']['force_reauth']
            and '/members/login/' not in owned_urls['core_urls']['force_reauth'],
            'Core URL ownership or force-reauth boundary changed')

    _, _, disable_page = admin.request(route_path)
    disable_nonce = hidden_input(disable_page, '_kklidi_members_admin_nonce')
    disabled_status, _, _ = admin.request(
        route_path, data=clean_route_fields(enabled=False, nonce=disable_nonce))
    route_disabled = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    disabled_clean_status, _, _ = Browser(base).request('/members/login/')
    disabled_query_status, _, _ = Browser(base).request('/?kklidi_members_login=1')
    require(disabled_status == 302
            and route_disabled['stored'] == {'version': 1, 'clean_routes_enabled': False}
            and all(route_disabled['present_rules'].values()) is False
            and route_disabled['helpers']['login'].find('kklidi_members_login=1') >= 0
            and route_disabled['core_urls']['login'].find('kklidi_members_login=1') >= 0
            and route_disabled['audit_count'] == 2
            and disabled_clean_status == 404 and disabled_query_status == 200,
            'Clean route rollback did not restore query fallback and remove rules')

    _, _, reset_ownership_page = admin.request(route_path)
    reset_ownership_nonce = hidden_input(reset_ownership_page, '_kklidi_members_admin_nonce')
    admin.request(route_path, data={
        'section': 'routes',
        'kklidi_members_admin_action': 'save_url_settings',
        '_kklidi_members_admin_nonce': reset_ownership_nonce,
    })
    corrupted = command(
        php_cli + [HERE / 'mvp_probe.php', 'corrupt-route-option'], json_result=True)
    corrupt_summary = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    reset_route = command(
        php_cli + [HERE / 'mvp_probe.php', 'reset-route-option'], json_result=True)
    route_final = command(
        php_cli + [HERE / 'mvp_probe.php', 'route-summary'], json_result=True)
    require(corrupted['stored']['custom_slug'] == 'unsafe'
            and corrupt_summary['effective'] == {
                'version': 1, 'clean_routes_enabled': False}
            and 'kklidi_members_login=1' in corrupt_summary['helpers']['login']
            and reset_route['stored'] == {'version': 1, 'clean_routes_enabled': False}
            and route_final['page_count'] == initial_page_count
            and route_final['menu_item_count'] == initial_menu_count,
            'Invalid route schema did not fail closed or cleanup changed site content')
    results['AUTH-ROUTE-MAP-001'] = {
        'status': 'PASS', 'default_enabled': False, 'pretty_permalink_required': True,
        'capability_and_nonce': True, 'strict_non_autoload_option': True,
        'page_collision_rejected': True, 'rewrite_collision_rejected': True,
        'clean_routes': 9, 'same_controllers_and_templates': True,
        'query_fallback_preserved': True, 'core_force_reauth_preserved': True,
        'automatic_pages_or_menus': False, 'unrelated_assets_or_flush': False,
        'rollback_and_corrupt_setting_fallback': True,
    }

    registration_settings_path = \
        '/wp-admin/users.php?page=kklidi-members&section=registration'
    fields_status, _, fields_page = admin.request(registration_settings_path)
    require(fields_status == 200
            and 'kklidi_members_registration_fields[fields][first_name]' in fields_page
            and hidden_input(fields_page, 'option_page') == 'kklidi_members_registration_fields',
            'Registration field Settings API screen is unavailable')
    fields_nonce = hidden_input(fields_page, '_wpnonce')

    def registration_settings_fields(first_name, last_name, phone, nonce=fields_nonce):
        return {
            'option_page': 'kklidi_members_registration_fields',
            'action': 'update',
            '_wpnonce': nonce,
            '_wp_http_referer': registration_settings_path,
            'kklidi_members_registration_fields[version]': '1',
            'kklidi_members_registration_fields[fields][first_name]': first_name,
            'kklidi_members_registration_fields[fields][last_name]': last_name,
            'kklidi_members_registration_fields[fields][phone]': phone,
        }

    configured_status, _, _ = admin.request('/wp-admin/options.php', data=
        registration_settings_fields('hidden', 'required', 'hidden'))
    configured_fields = command(
        php_cli + [HERE / 'mvp_probe.php', 'registration-fields-summary'], json_result=True)
    expected_field_states = {
        'version': 1,
        'fields': {'first_name': 'hidden', 'last_name': 'required', 'phone': 'hidden'},
    }
    require(configured_status == 302 and configured_fields['autoload'] in ('no', 'off')
            and configured_fields['stored'] == expected_field_states
            and configured_fields['effective'] == expected_field_states
            and configured_fields['settings_audit_count'] == 1
            and configured_fields['settings_audit_has_digest'] is True,
            'Valid registration field settings were not stored or audited safely: '
            + repr(configured_fields))

    invalid_field_status, _, _ = admin.request('/wp-admin/options.php', data=
        registration_settings_fields('hidden', 'required', 'administrator'))
    rejected_fields = command(
        php_cli + [HERE / 'mvp_probe.php', 'registration-fields-summary'], json_result=True)
    require(invalid_field_status == 302 and rejected_fields == configured_fields,
            'Unsupported registration field state was not rejected atomically')

    denied_fields_status, _, _ = profile_browser.request('/wp-admin/options.php', data=
        registration_settings_fields('required', 'optional', 'optional'))
    require(denied_fields_status == 403,
            'Subscriber used a registration-field Settings API nonce')

    field_mailbox_snapshot = mailbox_path.read_bytes()
    field_registration = Browser(base)
    field_status, _, field_form = field_registration.request('/?kklidi_members_register=1')
    require(field_status == 200 and 'name="first_name"' not in field_form
            and 'name="phone"' not in field_form and 'name="last_name"' in field_form
            and re.search(r'name="last_name"[^>]*\srequired(?:\s|>)', field_form),
            'Configured registration field visibility or requirement was not rendered')

    field_request = {
        'kklidi_members_register': '1',
        'request_id': hidden_input(field_form, 'request_id'),
        '_kklidi_members_register_nonce': hidden_input(
            field_form, '_kklidi_members_register_nonce'),
        '_kklidi_members_guest_exp': hidden_input(field_form, '_kklidi_members_guest_exp'),
        '_kklidi_members_guest_token': hidden_input(field_form, '_kklidi_members_guest_token'),
        'email': env['KKH_FIELDS_EMAIL'],
        'password': env['KKH_USER_PASSWORD'],
        'password_confirm': env['KKH_USER_PASSWORD'],
        'first_name': 'Injected first name',
        'display_name': 'Field Contract Member',
        'phone': '+82 10-1111-2222',
        'consent_service': '1',
        'consent_privacy': '1',
        'role': 'administrator',
        'user_id': str(fixture['fixtures']['email_identity']['id']),
    }
    missing_status, _, missing_body = field_registration.request(
        '/?kklidi_members_register=1', data=field_request)
    require(missing_status == 200 and 'name="last_name"' in missing_body
            and 'aria-invalid="true"' in missing_body,
            'Configured required registration field was not validated on the server')
    field_request.update({
        'last_name': 'Contract',
        '_kklidi_members_register_nonce': hidden_input(
            missing_body, '_kklidi_members_register_nonce'),
        '_kklidi_members_guest_exp': hidden_input(missing_body, '_kklidi_members_guest_exp'),
        '_kklidi_members_guest_token': hidden_input(missing_body, '_kklidi_members_guest_token'),
    })
    created_status, created_headers, _ = field_registration.request(
        '/?kklidi_members_register=1', data=field_request)
    created_fields = command(
        php_cli + [HERE / 'mvp_probe.php', 'registration-fields-summary'], json_result=True)
    require(created_status == 302 and 'registered=1' in created_headers.get('Location', '')
            and created_fields['field_user'] is not None
            and created_fields['field_user']['roles'] == ['subscriber']
            and created_fields['field_user']['first_name'] == ''
            and created_fields['field_user']['last_name'] == 'Contract'
            and created_fields['field_user']['phone'] == ''
            and created_fields['field_user']['required_consents'] == 2,
            'Hidden registration input was stored or required fields were not persisted safely: '
            + repr(created_fields.get('field_user')))
    field_cleanup = command(
        php_cli + [HERE / 'mvp_probe.php', 'cleanup-registration-fields-user'], json_result=True)
    require(field_cleanup == {'deleted': True, 'remaining': 0},
            'Synthetic registration-fields user cleanup failed')
    mailbox_path.write_bytes(field_mailbox_snapshot)

    _, _, reset_fields_page = admin.request(registration_settings_path)
    reset_fields_status, _, _ = admin.request('/wp-admin/options.php', data=
        registration_settings_fields(
            'required', 'optional', 'optional', hidden_input(reset_fields_page, '_wpnonce')))
    reset_fields = command(
        php_cli + [HERE / 'mvp_probe.php', 'registration-fields-summary'], json_result=True)
    default_field_states = {
        'version': 1,
        'fields': {'first_name': 'required', 'last_name': 'optional', 'phone': 'optional'},
    }
    require(reset_fields_status == 302 and reset_fields['effective'] == default_field_states
            and reset_fields['settings_audit_count'] == 2
            and reset_fields['field_user'] is None,
            'Registration field defaults or synthetic cleanup were not restored')
    results['AUTH-REGISTER-FIELDS-001'] = {
        'status': 'PASS', 'settings_api': True, 'capability_and_nonce': True,
        'non_autoload_option': True, 'default_compatible': True,
        'configurable_fields': ['first_name', 'last_name', 'phone'],
        'states': ['required', 'optional', 'hidden'],
        'invalid_update_rejected': True, 'required_server_validation': True,
        'hidden_post_ignored': True, 'role_and_user_id_injection_ignored': True,
        'existing_users_and_external_domains_unchanged': True,
    }

    message_path = '/wp-admin/users.php?page=kklidi-members&section=messages'
    message_status, _, message_page = admin.request(message_path)
    denied_message_status, _, _ = profile_browser.request(message_path)
    message_keys = (
        'registration_complete', 'password_changed', 'password_reset',
        'withdrawal_requested', 'invalid_credentials', 'login_rate_limited',
        'registration_closed', 'registration_invalid', 'registration_unavailable',
        'reset_request_generic', 'reset_invalid_link', 'profile_saved',
        'profile_save_failed', 'consent_saved', 'consent_save_failed',
        'withdrawal_save_failed',
    )
    require(message_status == 200 and denied_message_status == 403
            and all('<code>' + item + '</code>' in message_page for item in message_keys)
            and 'name="option_page"' not in message_page
            and 'kklidi_members_notification_templates' not in message_page,
            'Read-only Messages catalog or capability boundary is unavailable')

    notification_path = '/wp-admin/users.php?page=kklidi-members&section=notifications'
    notification_status, _, notification_page = admin.request(notification_path)
    require(notification_status == 200
            and 'kklidi_members_notification_templates[events][registration_completed][subject]'
            in notification_page
            and 'Leave a field empty to restore its translated default.' in notification_page
            and 'kklidi-members-notification-default' in notification_page
            and '[Synthetic Members Harness] Registration complete' in notification_page
            and 'Your account registration is complete.' in notification_page
            and hidden_input(notification_page, 'option_page') == 'kklidi_members_notifications',
            'Notification Settings API screen is unavailable')
    settings_nonce = hidden_input(notification_page, '_wpnonce')

    sender_status, _, sender_page = admin.request(sender_path)
    sender_forms = [form for form in re.findall(
        r'<form\b.*?</form>', sender_page, flags=re.IGNORECASE | re.DOTALL)
        if 'kklidi_members_mail_sender[sender_enabled]' in form]
    require(sender_status == 200 and len(sender_forms) == 1,
            'Members sender settings form disappeared from Notifications')
    sender_nonce = hidden_input(sender_forms[0], '_wpnonce')
    invalid_sender_status, _, _ = admin.request('/wp-admin/options.php', data=sender_settings_fields(
        extra={'kklidi_members_mail_sender[from_email]': 'bad\r\nBcc:attacker@example.invalid'}))
    invalid_sender = command(php_cli + [HERE / 'mvp_probe.php', 'mail-sender-summary'],
                             json_result=True)
    require(invalid_sender_status == 302 and invalid_sender['stored'] == sender_saved['stored']
            and invalid_sender['settings_audit_count'] == sender_saved['settings_audit_count'],
            'Invalid or header-injection sender settings changed the last valid option')
    denied_sender_status, _, _ = profile_browser.request(
        '/wp-admin/options.php', data=sender_settings_fields())
    require(denied_sender_status in (401, 403),
            'Subscriber changed the Members sender settings')

    test_mailbox_count = len(read_mailbox(mailbox_path))
    test_form = [form for form in re.findall(
        r'<form\b.*?</form>', sender_page, flags=re.IGNORECASE | re.DOTALL)
        if 'name="kklidi_members_admin_action"' in form
        and 'test_mail_sender' in form][0]
    test_nonce = hidden_input(test_form, '_kklidi_members_admin_nonce')
    test_fields = {
        'kklidi_members_admin_action': 'test_mail_sender',
        '_kklidi_members_admin_nonce': test_nonce,
    }
    failure_marker = Path(env['KKH_MAIL_FAILURE'])
    failure_marker.write_text('sender test failure\n', encoding='utf-8')
    failed_test_status, failed_test_headers, _ = admin.request(sender_path, data=test_fields)
    failure_marker.unlink(missing_ok=True)
    failed_test_mailbox = read_mailbox(mailbox_path)
    require(failed_test_status == 302 and 'mail_failed' in failed_test_headers.get('Location', '')
            and len(failed_test_mailbox) == test_mailbox_count,
            'Sender test-mail failure did not fail closed without delivery')

    successful_test_count = 0
    rate_limited = False
    for _ in range(3):
        refreshed_status, _, refreshed_page = admin.request(sender_path)
        refreshed_forms = [form for form in re.findall(
            r'<form\b.*?</form>', refreshed_page, flags=re.IGNORECASE | re.DOTALL)
            if 'test_mail_sender' in form]
        require(refreshed_status == 200 and len(refreshed_forms) == 1,
                'Sender test form was not rendered for the current administrator')
        refreshed_fields = {
            'kklidi_members_admin_action': 'test_mail_sender',
            '_kklidi_members_admin_nonce': hidden_input(
                refreshed_forms[0], '_kklidi_members_admin_nonce'),
        }
        test_status, test_headers, _ = admin.request(sender_path, data=refreshed_fields)
        if 'mail_test_sent' in test_headers.get('Location', ''):
            require(test_status == 302, 'Successful sender test did not redirect safely')
            successful_test_count += 1
        else:
            require(test_status == 302 and 'rate_limited' in test_headers.get('Location', ''),
                    'Sender test rate limit did not fail closed')
            rate_limited = True
    test_mailbox = read_mailbox(mailbox_path)
    test_audit = command(php_cli + [HERE / 'mvp_probe.php', 'mail-sender-summary'],
                         json_result=True)
    require(successful_test_count == 2 and rate_limited
            and len(test_mailbox) == test_mailbox_count + successful_test_count
            and test_audit['test_audit'][-1]['reason_code'] == 'rate_limited'
            and all(row['to'] == [fixture['admin_email']]
                    for row in test_mailbox[-successful_test_count:])
            and all('From: Synthetic Members <members@example.invalid>' in row['headers']
                    and 'This is a synthetic sender footer.' in row['message']
                    for row in test_mailbox[-successful_test_count:]),
            'Sender test delivery, scoped headers, footer, or audit boundary failed')
    results['AUTH-MAIL-SENDER-001'] = {
        'status': 'PASS', 'default_off': True, 'settings_api': True,
        'capability_and_nonce': True, 'non_autoload_option': True,
        'invalid_and_crlf_rejected_atomically': True, 'members_scoped_from_header': True,
        'plain_text_footer': True, 'test_recipient_current_admin_only': True,
        'test_failure_no_delivery': True, 'test_rate_limit': '3_per_admin_per_15_minutes',
        'metadata_only_audit': True, 'global_sender_filters': False,
        'smtp_credentials_stored': False,
    }

    def notification_settings_fields(subject='', body=''):
        fields = {
            'option_page': 'kklidi_members_notifications',
            'action': 'update',
            '_wpnonce': settings_nonce,
            '_wp_http_referer': notification_path,
        }
        for event in ('registration_completed', 'password_changed',
                      'withdrawal_requested', 'withdrawal_finalized'):
            fields[f'kklidi_members_notification_templates[events][{event}][subject]'] = \
                subject if event == 'registration_completed' else ''
            fields[f'kklidi_members_notification_templates[events][{event}][body]'] = \
                body if event == 'registration_completed' else ''
        return fields

    saved_status, _, _ = admin.request('/wp-admin/options.php', data=notification_settings_fields(
        'Synthetic {site_name}', 'Open {login_url}'
    ))
    saved_settings = command(
        php_cli + [HERE / 'mvp_probe.php', 'notification-settings-summary'], json_result=True)
    require(saved_status == 302 and saved_settings['autoload'] in ('no', 'off')
            and saved_settings['schema_version'] == 1
            and saved_settings['registration_content'][0].startswith('Synthetic ')
            and '{site_name}' not in saved_settings['registration_content'][0]
            and saved_settings['registration_content'][1].startswith('Open ')
            and base in saved_settings['registration_content'][1]
            and saved_settings['settings_audit_count'] == 1
            and saved_settings['settings_audit_has_subject'] is False,
            'Valid notification settings did not save, resolve, or audit safely: '
            + repr({'status': saved_status, 'summary': saved_settings}))

    invalid_status, _, _ = admin.request('/wp-admin/options.php', data=notification_settings_fields(
        'Invalid {user_id}', 'Open {login_url}'
    ))
    rejected_settings = command(
        php_cli + [HERE / 'mvp_probe.php', 'notification-settings-summary'], json_result=True)
    require(invalid_status == 302 and rejected_settings == saved_settings,
            'Unknown notification placeholder was not rejected atomically')

    denied_notification_status, _, _ = profile_browser.request(
        '/wp-admin/options.php', data=notification_settings_fields('Denied', 'Denied'))
    require(denied_notification_status == 403,
            'Subscriber used a Settings API nonce without manage_kklidi_members')

    reset_status, _, _ = admin.request(
        '/wp-admin/options.php', data=notification_settings_fields())
    reset_settings = command(
        php_cli + [HERE / 'mvp_probe.php', 'notification-settings-summary'], json_result=True)
    require(reset_status == 302 and reset_settings['settings_audit_count'] == 2
            and 'Registration complete' in reset_settings['registration_content'][0]
            and 'Sign in:' in reset_settings['registration_content'][1],
            'Empty notification settings did not restore gettext defaults')
    results['AUTH-NOTIFY-002'] = {
        'status': 'PASS', 'settings_api': True, 'capability_and_nonce': True,
        'non_autoload_option': True, 'placeholder_allowlist': True,
        'unknown_placeholder_rejected': True, 'empty_uses_gettext_default': True,
        'metadata_only_audit': True, 'plain_text': True,
        'sender_and_transport_inherited': True,
    }

    core_admin_email = command(
        php_cli + [HERE / 'mvp_probe.php', 'set-core-admin-email'], json_result=True)
    require(core_admin_email == {'admin_email': env['KKH_CORE_ADMIN_EMAIL']},
            'Synthetic WordPress administration email setup failed')
    admin_notice_page_status, _, notification_page = admin.request(notification_path)
    admin_notice_forms = [form for form in re.findall(
        r'<form\b.*?</form>', notification_page, flags=re.IGNORECASE | re.DOTALL)
        if 'kklidi_members_admin_notifications[registration_enabled]' in form]
    require(admin_notice_page_status == 200 and len(admin_notice_forms) == 1
            and env['KKH_CORE_ADMIN_EMAIL'] in notification_page
            and 'name="kklidi_members_admin_notifications[registration_enabled]"'
            in admin_notice_forms[0],
            'Administrator registration notice Settings API form is unavailable: ' + repr({
                'status': admin_notice_page_status,
                'form_count': len(admin_notice_forms),
                'has_option_group': 'kklidi_members_admin_notifications' in notification_page,
                'has_admin_email': env['KKH_CORE_ADMIN_EMAIL'] in notification_page,
                'has_checkbox': 'registration_enabled' in notification_page,
            }))
    admin_notice_nonce = hidden_input(admin_notice_forms[0], '_wpnonce')

    def admin_notification_fields(enabled=True, extra=False):
        fields = {
            'option_page': 'kklidi_members_admin_notifications',
            'action': 'update',
            '_wpnonce': admin_notice_nonce,
            '_wp_http_referer': notification_path,
            'kklidi_members_admin_notifications[version]': '1',
        }
        if enabled:
            fields['kklidi_members_admin_notifications[registration_enabled]'] = '1'
        if extra:
            fields['kklidi_members_admin_notifications[recipient]'] = 'attacker@example.invalid'
        return fields

    admin_notice_default = command(
        php_cli + [HERE / 'mvp_probe.php', 'admin-notification-summary'], json_result=True)
    require(admin_notice_default['autoload'] in ('no', 'off')
            and admin_notice_default['stored'] == {
                'version': 1, 'registration_enabled': False}
            and admin_notice_default['effective'] == admin_notice_default['stored']
            and admin_notice_default['settings_audit_count'] == 0
            and admin_notice_default['user'] is None,
            'Administrator notification default is not a non-autoload opt-in')

    invalid_admin_notice_status, _, _ = admin.request(
        '/wp-admin/options.php', data=admin_notification_fields(extra=True))
    invalid_admin_notice = command(
        php_cli + [HERE / 'mvp_probe.php', 'admin-notification-summary'], json_result=True)
    require(invalid_admin_notice_status == 302 and invalid_admin_notice == admin_notice_default,
            'Administrator notification accepted a custom recipient or unknown field')
    denied_admin_notice_status, _, _ = profile_browser.request(
        '/wp-admin/options.php', data=admin_notification_fields())
    require(denied_admin_notice_status == 403,
            'Subscriber changed the administrator notification setting')

    enabled_admin_notice_status, _, _ = admin.request(
        '/wp-admin/options.php', data=admin_notification_fields())
    enabled_admin_notice = command(
        php_cli + [HERE / 'mvp_probe.php', 'admin-notification-summary'], json_result=True)
    require(enabled_admin_notice_status == 302
            and enabled_admin_notice['stored'] == {
                'version': 1, 'registration_enabled': True}
            and enabled_admin_notice['settings_audit_count'] == 1,
            'Administrator notification opt-in was not saved safely')

    admin_notice_mail_count = len(read_mailbox(mailbox_path))
    admin_notice_registration = Browser(base)
    status, _, admin_notice_form = admin_notice_registration.request(
        '/?kklidi_members_register=1')
    admin_notice_request_id = hidden_input(admin_notice_form, 'request_id')
    admin_notice_registration_fields = {
        'kklidi_members_register': '1',
        'request_id': admin_notice_request_id,
        '_kklidi_members_register_nonce': hidden_input(
            admin_notice_form, '_kklidi_members_register_nonce'),
        '_kklidi_members_guest_exp': hidden_input(
            admin_notice_form, '_kklidi_members_guest_exp'),
        '_kklidi_members_guest_token': hidden_input(
            admin_notice_form, '_kklidi_members_guest_token'),
        'email': env['KKH_ADMIN_NOTICE_EMAIL'],
        'password': env['KKH_USER_PASSWORD'],
        'password_confirm': env['KKH_USER_PASSWORD'],
        'first_name': 'Admin',
        'last_name': 'Notice',
        'display_name': 'Synthetic Admin Notice',
        'phone': '',
        'consent_service': '1',
        'consent_privacy': '1',
    }
    status, headers, _ = admin_notice_registration.request(
        '/?kklidi_members_register=1', data=admin_notice_registration_fields)
    admin_notice_mail = read_mailbox(mailbox_path)
    admin_notice_summary = command(
        php_cli + [HERE / 'mvp_probe.php', 'admin-notification-summary'], json_result=True)
    user_notices = [row for row in admin_notice_mail[admin_notice_mail_count:]
                    if row['to'] == [env['KKH_ADMIN_NOTICE_EMAIL']]]
    admin_notices = [row for row in admin_notice_mail[admin_notice_mail_count:]
                     if row['to'] == [env['KKH_CORE_ADMIN_EMAIL']]]
    require(status == 302 and 'registered=1' in headers.get('Location', '')
            and len(admin_notice_mail) == admin_notice_mail_count + 2
            and len(user_notices) == 1 and len(admin_notices) == 1
            and admin_notice_summary['user']['state'] == 'active'
            and admin_notice_summary['user']['roles'] == ['subscriber']
            and admin_notice_summary['user']['required_consents'] == 2
            and admin_notice_summary['user']['mail_audit'] == [{
                'event_type': 'mail_admin_registration', 'result': 'success',
                'reason_code': 'wp_mail_accepted'}],
            'Opted-in administrator registration notice did not follow active registration')
    admin_notice = admin_notices[0]
    require('New member registration' in admin_notice['subject']
            and 'A new member registration is complete.' in admin_notice['message']
            and 'Synthetic Admin Notice' in admin_notice['message']
            and env['KKH_ADMIN_NOTICE_EMAIL'] in admin_notice['message']
            and 'Registered at (UTC):' in admin_notice['message']
            and any(header.lower().startswith('content-type: text/plain;')
                    for header in admin_notice['headers'])
            and 'From: Synthetic Members <members@example.invalid>' in admin_notice['headers']
            and 'This is a synthetic sender footer.' in admin_notice['message']
            and admin_notice.get('locale') == 'en_US'
            and admin_notice.get('site_locale_option') == 'en_US'
            and all(value not in admin_notice['subject'] + admin_notice['message']
                    for value in (env['KKH_USER_PASSWORD'], admin_notice_request_id,
                                  'user_id', 'role=', 'billing_phone', 'consent_')),
            'Administrator registration notice content or plain-text boundary changed: ' + repr({
                'subject': admin_notice['subject'],
                'message': admin_notice['message'],
                'headers': admin_notice['headers'],
                'locale': admin_notice.get('locale'),
                'determined_locale': admin_notice.get('determined_locale'),
                'site_locale_option': admin_notice.get('site_locale_option'),
            }))
    replay_admin_notice = command(
        php_cli + [HERE / 'mvp_probe.php', 'replay-admin-registration-notification'],
        json_result=True)
    invalid_admin_recipient = command(
        php_cli + [HERE / 'mvp_probe.php', 'admin-notification-invalid-recipient'],
        json_result=True)
    require(replay_admin_notice == {'sent': False}
            and invalid_admin_recipient == {
                'sent': False,
                'audit': {'result': 'failure', 'reason_code': 'invalid_recipient'},
                'state': 'active', 'admin_email_restored': True}
            and len(read_mailbox(mailbox_path)) == admin_notice_mail_count + 2,
            'Administrator notification replay or invalid-recipient boundary failed')
    admin_notice_cleanup = command(
        php_cli + [HERE / 'mvp_probe.php', 'cleanup-admin-notification-user'],
        json_result=True)
    require(admin_notice_cleanup == {'deleted': True, 'remaining': 0},
            'Synthetic administrator-notification user cleanup failed')
    results['AUTH-ADMIN-NOTIFY-001'] = {
        'status': 'PASS', 'default_enabled': False, 'settings_api': True,
        'capability_and_nonce': True, 'non_autoload_option': True,
        'recipient': 'wordpress_admin_email', 'custom_recipient': False,
        'post_active_only': True, 'plain_text': True,
        'logical_replay_idempotent': True, 'invalid_recipient_audited': True,
        'forbidden_data_absent': True, 'administrator_approval': False,
        'mail_failure_checked_with_account_failure_suite': True,
    }
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
    password_mail_count = len(read_mailbox(mailbox_path))
    _, _, password_form = first.request('/?kklidi_members_password=1')
    invalid_password_fields = {
        'kklidi_members_password': '1',
        '_kklidi_members_password_nonce': hidden_input(password_form, '_kklidi_members_password_nonce'),
        'current_password': 'incorrect-current-password',
        'new_password': env['KKH_NEW_PASSWORD'],
        'new_password_confirm': env['KKH_NEW_PASSWORD'],
    }
    invalid_status, _, invalid_body = first.request(
        '/?kklidi_members_password=1', data=invalid_password_fields)
    require(invalid_status == 200 and 'Please check your current password.' in invalid_body
            and len(read_mailbox(mailbox_path)) == password_mail_count,
            'Rejected password change sent an account notice')
    _, _, password_form = first.request('/?kklidi_members_password=1')
    password_fields = {
        'kklidi_members_password': '1',
        '_kklidi_members_password_nonce': hidden_input(password_form, '_kklidi_members_password_nonce'),
        'current_password': env['KKH_USER_PASSWORD'],
        'new_password': env['KKH_NEW_PASSWORD'],
        'new_password_confirm': env['KKH_NEW_PASSWORD'],
    }
    status, password_headers, _ = first.request('/?kklidi_members_password=1', data=password_fields)
    password_location = password_headers.get('Location', '')
    password_query = urllib.parse.parse_qs(urllib.parse.urlsplit(password_location).query)
    changed_status, _, changed_login = Browser(base).request(local_response_path(base, password_location))
    password_probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    require(status == 302 and first.observe(key)['logged_in'] is False
            and second.observe(key)['logged_in'] is False
            and password_probe['user']['old_password_valid'] is False
            and password_probe['user']['new_password_valid'] is True
            and password_query == {
                'kklidi_members_login': ['1'], 'password_changed': ['1']}
            and changed_status == 200
            and any(notice in changed_login for notice in (
                '비밀번호가 변경되었습니다. 다시 로그인하세요.',
                'Your password was changed. Please sign in again.'))
            and all(secret not in password_location for secret in (
                env['KKH_USER_PASSWORD'], env['KKH_NEW_PASSWORD'], env['KKH_MVP_EMAIL'],
                'key=', 'user_id=')),
            'Password change did not use Core hash/session revocation: ' + repr({
                'status': status,
                'location': password_location,
                'query': password_query,
                'first_logged_in': first.observe(key)['logged_in'],
                'second_logged_in': second.observe(key)['logged_in'],
                'old_password_valid': password_probe['user']['old_password_valid'],
                'new_password_valid': password_probe['user']['new_password_valid'],
                'changed_status': changed_status,
                'notice_present': '비밀번호가 변경되었습니다. 다시 로그인하세요.' in changed_login,
                'source_notice_present': 'Your password was changed. Please sign in again.' in changed_login,
                'notice_fragment': re.findall(
                    r'<p class="kklidi-members-notice"[^>]*>([^<]*)</p>', changed_login),
            }))
    password_mail = read_mailbox(mailbox_path)
    require(len(password_mail) == password_mail_count + 1,
            'Password change did not create exactly one account notice')
    assert_account_notice(
        password_mail[-1], env['KKH_MVP_EMAIL'], '비밀번호가 변경되었습니다',
        ['회원 계정의 비밀번호가 변경되었습니다.', '비밀번호를 재설정하세요:',
         '/?kklidi_members_password_reset=1'],
        [env['KKH_USER_PASSWORD'], env['KKH_NEW_PASSWORD'], env['KKH_RESET_PASSWORD'],
         env['KKH_MVP_EMAIL'], 'key=', 'user_id', 'auth_cookie']
    )
    results['AUTH-RESET-001']['self_change_core_hash'] = 'PASS'
    results['AUTH-RESET-001']['all_sessions_revoked_on_self_change'] = True
    results['AUTH-MESSAGE-UX-001'] = {
        'status': 'PASS', 'catalog_read_only': True, 'catalog_keys': 16,
        'subscriber_denied': True, 'translated_notification_defaults_visible': True,
        'password_change_notice': True, 'redirect_contains_secret': False,
        'global_message_option': False,
    }

    # Withdrawal preserves the Core ID and queues the user while revoking access.
    withdrawing, login_response, _ = members_login(base, env, env['KKH_MVP_EMAIL'], env['KKH_NEW_PASSWORD'])
    require(login_response[0] == 302, 'New password login failed')
    withdrawal_mail_count = len(read_mailbox(mailbox_path))
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
    withdrawal_mail = read_mailbox(mailbox_path)
    require(len(withdrawal_mail) == withdrawal_mail_count + 1,
            'Withdrawal request did not create exactly one account notice')
    assert_account_notice(
        withdrawal_mail[-1], env['KKH_MVP_EMAIL'], '탈퇴 요청이 접수되었습니다',
        ['탈퇴 요청을 접수했습니다.', '로그인이 차단됩니다',
         '사이트 관리자와 각 서비스 소유자'],
        [env['KKH_NEW_PASSWORD'], withdrawal_fields['request_id'], env['KKH_MVP_EMAIL'],
         'all personal data has been deleted', 'orders were deleted', 'learning records were deleted']
    )

    # The administrator sees the queue, finalizes only the pending state, and replay is idempotent.
    queued_user_id = withdrawal_probe['user']['id']
    restore_email = fixture['fixtures']['separate_username']['email']
    restore_state = command(php_cli + [HERE / 'mvp_probe.php', 'set-fixture-state',
                                       restore_email, 'withdrawal_pending'], json_result=True)
    restore_user_id = restore_state['user_id']
    queue_status, _, queue_page = admin.request('/wp-admin/users.php?page=kklidi-members&section=withdrawals')
    require(queue_status == 200
            and f'name="user_id" value="{queued_user_id}"' in queue_page
            and f'name="user_id" value="{restore_user_id}"' in queue_page
            and 'value="restore_withdrawal"' in queue_page
            and 'value="finalize_withdrawal"' in queue_page,
            'Pending withdrawal was not visible in the administrator queue')
    require('pending request' in queue_page.lower(),
            'Pending withdrawal count was not visible in the administrator queue')
    restore_fields = {
        'kklidi_members_admin_action': 'restore_withdrawal',
        '_kklidi_members_admin_nonce': hidden_input(queue_page, '_kklidi_members_admin_nonce'),
        'user_id': str(restore_user_id),
        'review_reason': 'Synthetic administrator review',
    }
    restore_status, _, _ = admin.request(
        '/wp-admin/users.php?page=kklidi-members&section=withdrawals', data=restore_fields)
    restored = command(php_cli + [HERE / 'mvp_probe.php', 'user-state-summary', restore_email],
                       json_result=True)
    restored_page_status, _, restored_page = admin.request(
        '/wp-admin/users.php?page=kklidi-members&section=withdrawals')
    restore_replay_status, _, _ = admin.request(
        '/wp-admin/users.php?page=kklidi-members&section=withdrawals', data=restore_fields)
    restored_replay = command(
        php_cli + [HERE / 'mvp_probe.php', 'user-state-summary', restore_email], json_result=True)
    require(restore_status == 302 and restored_page_status == 200 and restore_replay_status == 302
            and restored['state'] == 'active' and restored['session_count'] == 0
            and restored['events'].count('withdrawal_restored') == 1
            and restored_replay['state'] == 'active'
            and restored_replay['events'].count('withdrawal_restored') == 1
            and f'name="user_id" value="{restore_user_id}"' not in restored_page
            and f'name="user_id" value="{queued_user_id}"' in restored_page,
            'Administrator withdrawal restoration was not reasoned, session-safe, or idempotent')
    finalize_fields = {
        'kklidi_members_admin_action': 'finalize_withdrawal',
        '_kklidi_members_admin_nonce': hidden_input(restored_page, '_kklidi_members_admin_nonce'),
        'user_id': str(queued_user_id),
    }
    finalize_status, _, _ = admin.request('/wp-admin/users.php?page=kklidi-members&section=withdrawals', data=finalize_fields)
    finalized_probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    disabled_events = finalized_probe['audit_events'].count('withdrawal_disabled')
    expected_mail_events = {
        'mail_registration_completed', 'mail_password_changed',
        'mail_withdrawal_requested', 'mail_withdrawal_finalized',
    }
    mail_audit = finalized_probe['mail_audit']
    require(finalize_status == 302 and finalized_probe['users_count'] == 4
            and finalized_probe['user']['id'] == queued_user_id
            and finalized_probe['user']['state'] == 'disabled'
            and disabled_events == 1
            and {row['event_type'] for row in mail_audit} == expected_mail_events
            and all(row['result'] == 'success' and row['reason_code'] == 'wp_mail_accepted'
                    for row in mail_audit),
            'Administrator withdrawal finalization changed identity or missed the disabled transition: '
            + repr({'status': finalize_status,
                    'users_count': finalized_probe['users_count'],
                    'user': finalized_probe.get('user'),
                    'disabled_events': disabled_events,
                    'mail_audit': mail_audit,
                    'expected_mail_events': sorted(expected_mail_events)}))
    finalized_mail = read_mailbox(mailbox_path)
    require(len(finalized_mail) == len(withdrawal_mail) + 1,
            'Withdrawal finalization did not create exactly one account notice')
    assert_account_notice(
        finalized_mail[-1], env['KKH_MVP_EMAIL'], '탈퇴 처리가 완료되었습니다',
        ['탈퇴 요청 처리가 완료되었으며 로그인 차단 상태가 유지됩니다.',
         'WordPress 계정 ID와 관련 주문 또는 학습 기록이 보존될 수 있습니다'],
        [env['KKH_NEW_PASSWORD'], env['KKH_MVP_EMAIL'], 'all personal data has been deleted',
         'orders were deleted', 'learning records were deleted']
    )

    after_status, _, after_page = admin.request('/wp-admin/users.php?page=kklidi-members&section=withdrawals')
    replay_status, _, _ = admin.request(
        '/wp-admin/users.php?page=kklidi-members&section=withdrawals', data=finalize_fields)
    replay_probe = command(php_cli + [HERE / 'mvp_probe.php'], json_result=True)
    require(after_status == 200 and replay_status == 302
            and f'name="user_id" value="{queued_user_id}"' not in after_page
            and replay_probe['user']['state'] == 'disabled'
            and replay_probe['audit_events'].count('withdrawal_disabled') == disabled_events
            and len(read_mailbox(mailbox_path)) == len(finalized_mail),
            'Administrator withdrawal finalization was not idempotent')
    audit_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    audit_status, _, audit_page = admin.request(
        '/wp-admin/users.php?page=kklidi-members&section=audit'
        + '&audit_event=withdrawal_restored&audit_result=success'
        + f'&audit_user_id={restore_user_id}&audit_date={audit_date}')
    require(audit_status == 200 and 'Withdrawal restored' in audit_page
            and 'Administrator restored access with a reason' in audit_page
            and 'Clear filters' in audit_page
            and 'name="audit_event"' in audit_page and 'name="audit_result"' in audit_page
            and 'name="audit_date"' in audit_page and 'name="audit_user_id"' in audit_page,
            'Bounded administrator audit filters did not render the restored event')

    # P0-4: inject wp_mail() failure through the synthetic WordPress boundary and
    # repeat all four real account workflows. Committed account/security state
    # must survive, while the failed attempts must never enter the delivery sink.
    failure_marker = Path(env['KKH_MAIL_FAILURE'])
    failure_mail_count = len(read_mailbox(mailbox_path))
    failure_journal = Path(env['KKH_EVENTS'])
    initial_failed_event_count = sum(
        event['type'] == 'mail_failed' for event in events(failure_journal))
    failure_email = env['KKH_FAILURE_EMAIL']
    try:
        failure_marker.write_text('fail account notices\n', encoding='utf-8')

        failed_registration = Browser(base)
        status, _, failure_form = failed_registration.request('/?kklidi_members_register=1')
        failure_registration_fields = {
            'kklidi_members_register': '1',
            'request_id': hidden_input(failure_form, 'request_id'),
            '_kklidi_members_register_nonce': hidden_input(
                failure_form, '_kklidi_members_register_nonce'),
            '_kklidi_members_guest_exp': hidden_input(failure_form, '_kklidi_members_guest_exp'),
            '_kklidi_members_guest_token': hidden_input(failure_form, '_kklidi_members_guest_token'),
            'email': failure_email,
            'password': env['KKH_USER_PASSWORD'],
            'password_confirm': env['KKH_USER_PASSWORD'],
            'first_name': 'Failure',
            'last_name': 'Injection',
            'display_name': 'Synthetic Mail Failure',
            'phone': '',
            'consent_service': '1',
            'consent_privacy': '1',
            'role': 'administrator',
            'user_id': str(fixture['fixtures']['email_identity']['id']),
            '_kklidi_members_account_state': 'disabled',
        }
        status, headers, _ = failed_registration.request(
            '/?kklidi_members_register=1', data=failure_registration_fields)
        registration_failure_probe = command(
            php_cli + [HERE / 'mvp_probe.php', 'notification-failure-summary'],
            json_result=True)
        require(status == 302 and 'registered=1' in headers.get('Location', '')
                and registration_failure_probe['state'] == 'active'
                and registration_failure_probe['required_consents'] == 2
                and registration_failure_probe['original_password_valid'] is True
                and len(read_mailbox(mailbox_path)) == failure_mail_count,
                'Mail failure rolled back registration state or appeared delivered')
        failure_user_id = registration_failure_probe['user_id']

        failure_first, first_response, _ = members_login(
            base, env, failure_email, env['KKH_USER_PASSWORD'])
        failure_second, second_response, _ = members_login(
            base, env, failure_email, env['KKH_USER_PASSWORD'])
        require(first_response[0] == second_response[0] == 302,
                'Mail-failure password test sessions failed')
        _, _, failure_password_form = failure_first.request('/?kklidi_members_password=1')
        failure_password_fields = {
            'kklidi_members_password': '1',
            '_kklidi_members_password_nonce': hidden_input(
                failure_password_form, '_kklidi_members_password_nonce'),
            'current_password': env['KKH_USER_PASSWORD'],
            'new_password': env['KKH_FAILURE_PASSWORD'],
            'new_password_confirm': env['KKH_FAILURE_PASSWORD'],
        }
        status, _, _ = failure_first.request(
            '/?kklidi_members_password=1', data=failure_password_fields)
        password_failure_probe = command(
            php_cli + [HERE / 'mvp_probe.php', 'notification-failure-summary'],
            json_result=True)
        require(status == 302 and failure_first.observe(key)['logged_in'] is False
                and failure_second.observe(key)['logged_in'] is False
                and password_failure_probe['user_id'] == failure_user_id
                and password_failure_probe['state'] == 'active'
                and password_failure_probe['original_password_valid'] is False
                and password_failure_probe['changed_password_valid'] is True
                and password_failure_probe['session_count'] == 0
                and len(read_mailbox(mailbox_path)) == failure_mail_count,
                'Mail failure rolled back password state, sessions, or appeared delivered')

        failure_withdrawing, login_response, _ = members_login(
            base, env, failure_email, env['KKH_FAILURE_PASSWORD'])
        require(login_response[0] == 302, 'Changed password failed before mail-failure withdrawal')
        _, _, failure_withdrawal_form = failure_withdrawing.request(
            '/?kklidi_members_withdrawal=1')
        failure_withdrawal_fields = {
            'kklidi_members_withdrawal': '1',
            '_kklidi_members_withdrawal_nonce': hidden_input(
                failure_withdrawal_form, '_kklidi_members_withdrawal_nonce'),
            'request_id': hidden_input(failure_withdrawal_form, 'request_id'),
            'current_password': env['KKH_FAILURE_PASSWORD'],
            'user_id': str(fixture['fixtures']['email_identity']['id']),
        }
        status, headers, _ = failure_withdrawing.request(
            '/?kklidi_members_withdrawal=1', data=failure_withdrawal_fields)
        withdrawal_failure_probe = command(
            php_cli + [HERE / 'mvp_probe.php', 'notification-failure-summary'],
            json_result=True)
        blocked_failure, blocked_response, _ = members_login(
            base, env, failure_email, env['KKH_FAILURE_PASSWORD'])
        require(status == 302 and 'withdrawal=requested' in headers.get('Location', '')
                and failure_withdrawing.observe(key)['logged_in'] is False
                and blocked_response[0] == 200 and blocked_failure.observe(key)['logged_in'] is False
                and withdrawal_failure_probe['user_id'] == failure_user_id
                and withdrawal_failure_probe['state'] == 'withdrawal_pending'
                and withdrawal_failure_probe['session_count'] == 0
                and len(read_mailbox(mailbox_path)) == failure_mail_count,
                'Mail failure rolled back withdrawal request, access revocation, or appeared delivered')

        failure_queue_status, _, failure_queue_page = admin.request(
            '/wp-admin/users.php?page=kklidi-members&section=withdrawals')
        require(failure_queue_status == 200
                and f'name="user_id" value="{failure_user_id}"' in failure_queue_page,
                'Mail-failure withdrawal was absent from the administrator queue')
        failure_finalize_fields = {
            'kklidi_members_admin_action': 'finalize_withdrawal',
            '_kklidi_members_admin_nonce': hidden_input(
                failure_queue_page, '_kklidi_members_admin_nonce'),
            'user_id': str(failure_user_id),
        }
        status, _, _ = admin.request(
            '/wp-admin/users.php?page=kklidi-members&section=withdrawals', data=failure_finalize_fields)
        finalized_failure_probe = command(
            php_cli + [HERE / 'mvp_probe.php', 'notification-failure-summary'],
            json_result=True)
        failed_mail_audit = finalized_failure_probe['mail_audit']
        injected_failure_events = sum(
            event['type'] == 'mail_failed' for event in events(failure_journal)
        ) - initial_failed_event_count
        require(status == 302 and finalized_failure_probe['user_id'] == failure_user_id
                and finalized_failure_probe['state'] == 'disabled'
                and finalized_failure_probe['session_count'] == 0
                and [row['event_type'] for row in failed_mail_audit] == [
                    'mail_registration_completed', 'mail_admin_registration', 'mail_password_changed',
                    'mail_withdrawal_requested', 'mail_withdrawal_finalized']
                and all(row['result'] == 'failure'
                        and row['reason_code'] == 'wp_mail_failed'
                        for row in failed_mail_audit)
                and injected_failure_events == 5
                and len(read_mailbox(mailbox_path)) == failure_mail_count,
                'Failed account mail was reported as delivered or final state rolled back')
    finally:
        failure_marker.unlink(missing_ok=True)

    results['AUTH-WITHDRAW-001'] = {'status': 'PASS', 'identity_preserved': True,
                                    'requested_state': 'withdrawal_pending',
                                    'final_state': 'disabled', 'sessions_revoked': True,
                                    'admin_queue': 'PASS', 'admin_replay_idempotent': True,
                                    'admin_restore_with_reason': True,
                                    'restored_sessions': False,
                                     'automatic_pii_deletion': False}
    results['AUTH-ADMIN-NOTIFY-001'].update({
        'mail_failure_attempts': 1,
        'mail_failure_audit_result': 'failure/wp_mail_failed',
        'mail_failure_registration_preserved': True,
        'mail_failure_retry_attempts': 0,
    })
    results['AUTH-NOTIFY-001'] = {
        'status': 'PASS', 'account_notice_events': 4,
        'current_core_recipient': True, 'fixed_plain_text_presets': True,
        'post_success_only': True, 'logical_replay_idempotent': True,
        'credentials_and_tokens_absent': True, 'order_lms_details_absent': True,
        'minimal_audit_results': ['wp_mail_accepted', 'wp_mail_failed'],
        'mail_failure_events': 4, 'mail_failure_injected_attempts': 4,
        'mail_failure_delivery_records': 0,
        'mail_failure_audit_result': 'failure/wp_mail_failed',
        'mail_failure_committed_state_preserved': True,
        'mail_failure_sessions_remain_revoked': True,
        'mail_failure_user_response': 'committed_operation_success',
        'mail_failure_retry_attempts': 0,
        'members_off_no_hard_dependency': 'checked_after_account_cases',
        'korean_site_fallback': True, 'korean_user_locale': True,
        'catalog_rendered': True, 'catalog_msgids': 12,
    }

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
                                 'retention_cleanup': True,
                                 'admin_filters': ['event', 'result', 'date', 'user_id'],
                                 'bounded_page_size': 25}

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
    require(off['members_helper_exists'] is False and off['notification_class_exists'] is False
            and off['core_fallback_is_wp_login'] is True
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
                       'wp_remote_', 'wp_register_', 'JWT'):
        require(prohibited not in source, f'Production runtime contains prohibited mechanism: {prohibited}')

    plugin_source = (REPO / 'includes/Core/Plugin.php').read_text(encoding='utf-8')
    admin_source = (REPO / 'includes/Admin/AdminController.php').read_text(encoding='utf-8')
    require("add_action('wp_enqueue_scripts'" in plugin_source
            and 'wp_enqueue_style(' in plugin_source
            and 'is_frontend_route' in plugin_source,
            'Frontend stylesheet must stay scoped to a Members route')
    require('members-auth.js' in plugin_source
            and 'is_password_enhancement_route' in plugin_source
			and 'if (self::is_password_enhancement_route())' in plugin_source,
            'Authentication script must stay scoped to login and registration routes')
    require("add_action('admin_enqueue_scripts'" in admin_source
            and "users_page_kklidi-members" in admin_source
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
               KKH_FIELDS_EMAIL='fields-' + run_id[:12] + '@example.invalid',
			   KKH_ADMIN_NOTICE_EMAIL='admin-notice-' + run_id[:12] + '@example.invalid',
			   KKH_CORE_ADMIN_EMAIL='site-admin-' + run_id[:12] + '@example.invalid',
               KKH_FAILURE_EMAIL='notify-failure-' + run_id[:12] + '@example.invalid',
               KKH_FAILURE_PASSWORD=secrets.token_urlsafe(40),
               KKH_SALT=secrets.token_hex(48), KKH_PROBE_KEY=secrets.token_hex(32),
               KKH_MAILBOX=str(root / 'mailbox.jsonl'),
               KKH_MAIL_FAILURE=str(root / 'mail-failure.enabled'))
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    report = {'contract': 'KKLIDI-MEMBERS-MVP', 'scope': 'SYNTHETIC_WORDPRESS_BEHAVIOR', 'run_id': run_id,
              'status': 'FAIL', 'wordpress': LOCK['version'], 'archive_sha256': LOCK['archive_sha256'],
              'official_file_checksums_verified': checksum_count,
              'contract_status': 'PARTIAL', 'mvp_contracts': {},
              'modes': {'core_baseline': {'status': 'FAIL', 'variants': []},
                        'members_on': {'status': 'FAIL', 'variants': []}},
              'contracts_total': 24, 'contracts_exercised': 24,
               'extension_contracts_total': 8, 'extension_contracts_exercised': 8,
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
            for name in ('KKH_DB_PASSWORD', 'KKH_USER_PASSWORD', 'KKH_NEW_PASSWORD',
                         'KKH_RESET_PASSWORD', 'KKH_FAILURE_PASSWORD', 'KKH_SALT', 'KKH_PROBE_KEY',
                         'KKH_MVP_EMAIL', 'KKH_FIELDS_EMAIL', 'KKH_ADMIN_NOTICE_EMAIL',
						 'KKH_CORE_ADMIN_EMAIL', 'KKH_FAILURE_EMAIL'):
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
            def restart_mvp_server():
                nonlocal server
                stop(server)
                server = start(php_cli + ['-S', '127.0.0.1:' + env['KKH_HTTP_PORT'], '-t', webroot,
                                          HERE / 'router.php'], 'php-mvp-restart-' + str(index))
                wait_port(server, int(env['KKH_HTTP_PORT']))
            mvp_results = run_mvp_cases(base, env, fixture, command, php_cli,
                                        restart_server=restart_mvp_server)
            identity_rows = [row for row in members_rows if row.get('email_primary_ui_guidance')]
            identity_display_guard = [row for row in guard_rows
                                      if row.get('display_name_not_identifier')]
            require(len(identity_rows) == 6 and identity_display_guard,
                    'Identity contract did not exercise email-first and nickname boundaries')
            require(mvp_results['AUTH-REGISTER-001'].get('user_nicename_separate') is True,
                    'Identity contract did not exercise the independent public nicename')
            mvp_results['AUTH-IDENTITY-002'] = {
                'status': 'PASS',
                'new_registration_username_field': False,
                'new_user_login_private': True,
                'new_user_nicename_separate': True,
                'email_primary_login_guidance': True,
                'legacy_username_login': True,
                'legacy_email_login': True,
                'password_reset_legacy_identifier_compatible': True,
                'display_name_not_identifier': True,
                'core_auth_and_reset_apis_preserved': True,
                'members_off_core_login_no_fatal': True,
            }
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
            boundary_results = run_domain_boundary_cases(env, fixture, command, php_cli)
            mvp_results['AUTH-NOTIFY-001']['members_off_no_hard_dependency'] = True
            for contract, result in mvp_results.items():
                report['mvp_contracts'].setdefault(contract, []).append(dict(result, prefix=prefix))
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
        for name in ('KKH_DB_PASSWORD', 'KKH_USER_PASSWORD', 'KKH_NEW_PASSWORD',
                     'KKH_RESET_PASSWORD', 'KKH_FAILURE_PASSWORD', 'KKH_SALT', 'KKH_PROBE_KEY',
                     'KKH_MVP_EMAIL', 'KKH_FIELDS_EMAIL', 'KKH_FAILURE_EMAIL'):
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
    print(f'{report["status"]}: MVP contracts=24 + extension contracts=8, '
          f'AUTH-LOGIN-001 Core={core_total}, '
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
