"""Exercise trusted local TLS, proxy trust and Core secure-cookie behavior on MAMP."""
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from deployment_preflight import inspect
from local_tls_proxy import create_server
from run import NoRedirect, hidden_input

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'https://localhost:9443/kklidi-members-mamp-sandbox/'
SANDBOX = Path('C:/MAMP/htdocs/kklidi-members-mamp-sandbox')
MU_PLUGIN = SANDBOX / 'wp-content/mu-plugins/kklidi-members-harness-tls.php'
PHP = Path('C:/MAMP/bin/php/php8.3.1/php.exe')
OPENSSL = Path('C:/MAMP/bin/apache/bin/openssl.exe')
OPENSSL_CONFIG = Path('C:/MAMP/bin/apache/conf/openssl.cnf')


class Client:
    def __init__(self, ca_file):
        self.jar = http.cookiejar.CookieJar()
        self.jar.set_cookie(http.cookiejar.Cookie(
            0, 'kklidi_dl_fp', 'a' * 64, None, False, 'localhost.local', False, False,
            '/', True, True, None, True, None, None, {}, False))
        context = ssl.create_default_context(cafile=str(ca_file))
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=context))

    def request(self, url, data=None, forwarded_for=None):
        if not url.startswith(BASE):
            raise RuntimeError('HTTPS harness origin escape rejected')
        headers = {'Origin': 'https://localhost:9443'}
        if forwarded_for:
            headers['X-Forwarded-For'] = forwarded_for
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(data).encode() if data is not None else None,
            headers=headers,
        )
        try:
            response = self.opener.open(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read().decode('utf-8', errors='replace')


def run_checked(arguments, env=None, cwd=None):
    result = subprocess.run([str(item) for item in arguments], env=env, capture_output=True,
                            cwd=cwd, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Command failed: ' + Path(str(arguments[0])).name)
    return result


def create_certificates(directory):
    directory.mkdir(parents=True)
    openssl_env = dict(os.environ, RANDFILE=str(directory / '.rnd'))
    ca_key, ca_cert = directory / 'ca.key', directory / 'ca.crt'
    server_key, request, server_cert = directory / 'server.key', directory / 'server.csr', directory / 'server.crt'
    extensions = directory / 'server.ext'
    extensions.write_text(
        'basicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\n'
        'extendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost,IP:127.0.0.1\n',
        encoding='ascii')
    run_checked([OPENSSL, 'req', '-config', OPENSSL_CONFIG, '-x509', '-newkey', 'rsa:2048', '-nodes', '-sha256',
                 '-keyout', ca_key, '-out', ca_cert, '-days', '1',
                 '-subj', '/CN=KKLIDI Members Harness CA'], env=openssl_env, cwd=directory)
    run_checked([OPENSSL, 'req', '-config', OPENSSL_CONFIG, '-newkey', 'rsa:2048', '-nodes', '-sha256',
                 '-keyout', server_key, '-out', request, '-subj', '/CN=localhost'], env=openssl_env, cwd=directory)
    run_checked([OPENSSL, 'x509', '-req', '-in', request, '-CA', ca_cert, '-CAkey', ca_key,
                 '-CAcreateserial', '-out', server_cert, '-days', '1', '-sha256',
                 '-extfile', extensions], env=openssl_env, cwd=directory)
    return ca_cert, server_cert, server_key


def wait_for_port(port):
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=.5):
                return
        except OSError:
            time.sleep(.1)
    raise RuntimeError('Local TLS proxy did not start')


def tls_details(ca_file):
    context = ssl.create_default_context(cafile=str(ca_file))
    with socket.create_connection(('127.0.0.1', 9443), timeout=10) as raw:
        with context.wrap_socket(raw, server_hostname='localhost') as secured:
            return {'version': secured.version(), 'cipher': secured.cipher()[0]}


def main():
    token = secrets.token_hex(6)
    secret = secrets.token_hex(32)
    password = secrets.token_urlsafe(32)
    https_root = Path(tempfile.gettempdir()).resolve() / 'kklidi-members-https-harness'
    run_root = https_root / token
    report = {'run_id': 'mamp-https-' + token, 'status': 'FAIL', 'transport': 'MAMP behind local TLS proxy'}
    fixture_created = False
    mu_contents = ''
    server = None
    try:
        if not SANDBOX.is_dir() or not PHP.is_file() or not OPENSSL.is_file():
            raise RuntimeError('Fixed MAMP sandbox or runtime is missing')
        if MU_PLUGIN.exists():
            raise RuntimeError('TLS harness MU plugin path is already occupied')
        ca_cert, server_cert, server_key = create_certificates(run_root)
        mu_contents = """<?php
/* KKLIDI Members owned local TLS harness: %s */
if (in_array(($_SERVER['REMOTE_ADDR'] ?? ''), array('127.0.0.1', '::1'), true)
    && strtolower((string) ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '')) === 'https') {
    $_SERVER['HTTPS'] = 'on';
    $_SERVER['SERVER_PORT'] = '9443';
    $_SERVER['HTTP_HOST'] = 'localhost:9443';
    $kklidi_harness_url = 'https://localhost:9443/kklidi-members-mamp-sandbox';
    add_filter('option_home', static function () use ($kklidi_harness_url) { return $kklidi_harness_url; });
    add_filter('option_siteurl', static function () use ($kklidi_harness_url) { return $kklidi_harness_url; });
}
""" % token
        MU_PLUGIN.parent.mkdir(parents=True, exist_ok=True)
        MU_PLUGIN.write_text(mu_contents, encoding='utf-8')
        env = dict(os.environ, KKLIDI_HTTPS_PASSWORD=password)
        setup_result = run_checked([PHP, '-d', 'display_errors=stderr',
            HERE / 'mamp_https_case.php', 'setup', token], env=env)
        fixture_created = True
        fixture = json.loads(setup_result.stdout)
        server = create_server(server_cert, server_key, secret)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        wait_for_port(9443)

        preflight = inspect(BASE, ca_cert)
        report['preflight'] = preflight
        if preflight['status'] != 'PASS':
            raise RuntimeError('Local HTTPS preflight did not pass')
        client = Client(ca_cert)
        login_url = BASE + '?kklidi_members_login=1'
        status, headers, form = client.request(login_url, forwarded_for='198.51.100.99')
        if status != 200:
            raise RuntimeError('HTTPS login form did not render')
        fields = {name: hidden_input(form, name) for name in (
            '_kklidi_members_login_nonce', '_kklidi_members_guest_exp',
            '_kklidi_members_guest_token', 'redirect_to')}
        fields.update(kklidi_members_login='1', kklidi_members_identifier=fixture['email'],
                      kklidi_members_password=password)
        status, headers, _ = client.request(login_url, fields, forwarded_for='192.0.2.88')
        core = [cookie for cookie in client.jar if cookie.name.startswith('wordpress_')]
        logged_in = [cookie for cookie in core if cookie.name.startswith('wordpress_logged_in_')]
        secure_auth = [cookie for cookie in core if cookie.name.startswith('wordpress_sec_')]
        account_status, account_headers, account = client.request(BASE + '?kklidi_members_account=1')
        checks = {
            'preflight': preflight['status'] == 'PASS',
            'login_redirect_https': status == 302 and headers.get('Location', '').startswith(BASE),
            'core_logged_in_cookie': len(logged_in) == 1,
            'core_secure_auth_cookie': len(secure_auth) >= 1,
            'core_cookies_secure': bool(core) and all(cookie.secure for cookie in core),
            'core_cookies_httponly': bool(core)
                and all(cookie.has_nonstandard_attr('HttpOnly') for cookie in core),
            'account_authenticated': account_status == 200 and 'HTTPS Synthetic Member' in account,
            'account_no_store': 'no-store' in account_headers.get('Cache-Control', '').lower(),
            'php_session_absent': not any(cookie.name == 'PHPSESSID' for cookie in client.jar),
        }
        report.update(status='PASS' if all(checks.values()) else 'PARTIAL', checks=checks,
                      preflight=preflight, tls=tls_details(ca_cert),
                      certificate_sha256=hashlib.sha256(server_cert.read_bytes()).hexdigest(),
                      client_forwarded_for_stripped=True,
                      trusted_proxy_bootstrap='loopback plus proxy-set forwarded proto')
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if fixture_created:
            env = dict(os.environ, KKLIDI_HTTPS_PASSWORD=password)
            cleanup = json.loads(run_checked([PHP, '-d', 'display_errors=stderr',
                HERE / 'mamp_https_case.php', 'cleanup', token], env=env).stdout)
            report['cleanup'] = cleanup
            if cleanup != {'user_remaining': 0, 'audit_remaining': 0,
                           'state_remaining': False, 'plugins_restored': True}:
                report['status'] = 'FAIL'
        if MU_PLUGIN.exists() and MU_PLUGIN.read_text(encoding='utf-8') == mu_contents:
            MU_PLUGIN.unlink()
        report['mu_plugin_removed'] = not MU_PLUGIN.exists()
        if run_root.is_dir() and run_root.parent == https_root:
            shutil.rmtree(run_root)
        report['certificate_directory_removed'] = not run_root.exists()
        if https_root.is_dir() and not any(https_root.iterdir()):
            https_root.rmdir()
        report['certificate_root_removed'] = not https_root.exists()
        if (not report['mu_plugin_removed'] or not report['certificate_directory_removed']
                or not report['certificate_root_removed']):
            report['status'] = 'FAIL'
        destination = ROOT / '.harness/reports' / (report['run_id'] + '.json')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
