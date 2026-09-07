"""Real HTTP form submission with a fixed dedicated MAMP sandbox and synthetic data."""
import http.cookiejar
import json
import os
import re
from pathlib import Path
import secrets
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from run import NoRedirect, hidden_input

HERE = Path(__file__).resolve().parent
BASE = 'http://localhost:8888/kklidi-members-mamp-sandbox/'

class Client:
    def __init__(self, fingerprint):
        self.jar = http.cookiejar.CookieJar()
        self.jar.set_cookie(http.cookiejar.Cookie(0, 'kklidi_dl_fp', fingerprint, None, False,
            'localhost.local', False, False, '/', True, False, None, True, None, None, {}, False))
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPCookieProcessor(self.jar))

    def get(self, url, data=None):
        assert url.startswith(BASE)
        request = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data is not None else None,
            headers={'Origin': 'http://localhost:8888'})
        try:
            response = self.opener.open(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read().decode('utf-8')

def main():
    token = secrets.token_hex(6)
    env = dict(os.environ, KKLIDI_WOO_PASSWORD=secrets.token_urlsafe(32))
    report = {'run_id': 'mamp-woo-' + token, 'status': 'FAIL', 'transport': 'HTTP forms, no JavaScript engine'}
    def call(action):
        result = subprocess.run(['C:/MAMP/bin/php/php8.3.1/php.exe', '-d', 'display_errors=stderr',
            str(HERE / 'mamp_woo_case.php'), action, token], env=env, capture_output=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode: raise RuntimeError('Woo fixture failed: ' + action)
        return json.loads(result.stdout)
    try:
        fixture = call('setup')
        client = Client('a' * 64)
        client.get(BASE + '?add-to-cart=' + str(fixture['product_id']))
        status, headers, _ = client.get(fixture['checkout_url'])
        assert status == 302 and 'kklidi_members_login=1' in headers['Location']
        login_url = headers['Location']
        status, _, form = client.get(login_url)
        assert status == 200
        fields = {name: hidden_input(form, name) for name in
            ('_kklidi_members_login_nonce', '_kklidi_members_guest_exp', '_kklidi_members_guest_token', 'redirect_to')}
        fields.update(kklidi_members_login='1', kklidi_members_identifier=fixture['email'],
            kklidi_members_password=env['KKLIDI_WOO_PASSWORD'])
        status, headers, _ = client.get(login_url, fields)
        assert status == 302 and headers['Location'] == fixture['checkout_url'], 'Login did not preserve checkout'
        status, _, checkout = client.get(headers['Location'])
        assert status == 200, 'Checkout response status: ' + str(status)
        cart_status, _, cart_body = client.get(BASE + '?rest_route=/wc/store/v1/cart')
        cart = json.loads(cart_body)
        assert cart_status == 200 and any(item['id'] == fixture['product_id'] for item in cart['items']), 'Cart item missing after login'
        orders_url = fixture['myaccount_url'] + '&orders=1' if '?' in fixture['myaccount_url'] else fixture['myaccount_url'] + 'orders/'
        status, _, orders = client.get(orders_url)
        assert status == 200 and re.search(r'(?:view-order/|view-order=)' + str(fixture['customer_order_id']) + r'(?:[\s/\"\'&<]|$)', orders)
        assert not re.search(r'(?:view-order/|view-order=)' + str(fixture['guest_order_id']) + r'(?:[\s/\"\'&<]|$)', orders)
        probe = call('probe')
        assert probe['customer_order_user_id'] == fixture['user_id'] and probe['guest_order_user_id'] == 0
        assert probe['account_order_ids'] == [fixture['customer_order_id']]
        # Exercise Woo's own username/password form, including the real device-limit filter.
        for fingerprint, allowed in (('a' * 64, True), ('b' * 64, False)):
            woo = Client(fingerprint)
            status, _, form = woo.get(fixture['myaccount_url'])
            nonce = hidden_input(form, 'woocommerce-login-nonce')
            status, _, result = woo.get(fixture['myaccount_url'], {
                'username': fixture['email'], 'password': env['KKLIDI_WOO_PASSWORD'],
                'woocommerce-login-nonce': nonce, 'login': 'Log in', '_wp_http_referer': fixture['myaccount_url']})
            has_auth = any(c.name.startswith('wordpress_logged_in_') for c in woo.jar)
            assert has_auth is allowed, 'Woo device authentication result changed'
            if allowed: assert status == 302
        report.update(status='PASS', checkout_login_post=True, cart_preserved=True,
            rendered_member_order=True, guest_order_not_claimed=True, woo_device_allowed=True,
            woo_device_blocked=True, browser_javascript='NOT_RUN')
    finally:
        report['cleanup'] = call('cleanup')
        (HERE.parents[1] / '.harness/reports' / (report['run_id'] + '.json')).write_text(
            json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report))

if __name__ == '__main__': main()
