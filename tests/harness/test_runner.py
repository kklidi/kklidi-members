"""Small safety tests for a harness that provisions and destroys temporary data."""
import json
import gettext
import re
import unittest
from pathlib import Path
import os
import stat
import tempfile
from unittest.mock import patch

from run import (Browser, HarnessError, LOCK, PACKAGE_FILES, archive_name, assert_identity,
                 assert_production_shape, hidden_input, owned_cleanup, verified_archive)
from compile_catalog import read_po
from validate_deployment_manifest import inspect as inspect_deployment_manifest


class HarnessGuards(unittest.TestCase):
    def test_dependency_tampering_fails_before_execution(self):
        with tempfile.TemporaryDirectory(prefix='kkh-cache-test-') as directory:
            cache = Path(directory)
            (cache / f'wordpress-{LOCK["version"]}.zip').write_bytes(b'tampered')
            with patch('run.CACHE', cache), self.assertRaisesRegex(HarnessError, 'checksum mismatch'):
                verified_archive()

    def test_archive_rejects_path_escape(self):
        for name in ('../x', '/wordpress/x', 'wordpress/../../x', 'wordpress/C:/x',
                     'wordpress\\x', 'other/wp-config.php'):
            with self.subTest(name=name), self.assertRaises(HarnessError):
                archive_name(name)

    def test_archive_allows_core_paths(self):
        self.assertEqual(archive_name('wordpress/wp-includes/user.php').parts[0], 'wordpress')

    def test_cannot_target_existing_or_remote_sites(self):
        for base in ('http://127.0.0.1:8888', 'http://localhost:25000', 'https://example.com',
                     'http://127.0.0.1:25000/ns_0727', 'http://user@127.0.0.1:25000'):
            with self.subTest(base=base), self.assertRaises(HarnessError):
                Browser(base)

    def test_request_cannot_change_origin(self):
        browser = Browser('http://127.0.0.1:25000')
        for path in ('//example.com', 'https://example.com', '/\\example.com', '/x\r\nHost: x'):
            with self.subTest(path=path), self.assertRaises(HarnessError):
                browser.request(path)

    def test_cleanup_rejects_unowned_directory(self):
        with self.assertRaises(HarnessError):
            owned_cleanup(Path(__file__).resolve().parent, 'not-an-owner')

    def test_cleanup_handles_read_only_content_inside_owned_root(self):
        root = Path(tempfile.mkdtemp(prefix='kklidi-members-harness-')).resolve()
        run_id = 'owned-read-only-test'
        (root / 'owner').write_text(run_id)
        child = root / 'copied-source'
        child.mkdir()
        item = child / 'file.php'
        item.write_text('<?php')
        os.chmod(item, stat.S_IREAD)
        os.chmod(child, stat.S_IREAD)
        owned_cleanup(root, run_id)
        self.assertFalse(root.exists())

    def test_identity_oracle_rejects_wrong_identity_and_privilege(self):
        expected = {'id': 2, 'roles': ['subscriber'], 'display_name': '합성 회원'}
        observed = {'run_id': 'run', 'prefix': 'kkh_', 'logged_in': True, 'user_id': 2,
                    'roles': ['subscriber'], 'can_read': True, 'can_manage_options': False,
                    'display_name': '합성 회원', 'users_count': 3, 'plugins': [],
                    'members_files': [], 'kklidi_cookies': [], 'php_session_active': False}
        assert_identity(observed, expected, 'kkh_', 'run')
        for changes in ({'user_id': 3}, {'logged_in': False}, {'roles': ['administrator']},
                        {'can_manage_options': True}, {'run_id': 'other'}, {'users_count': 4}):
            with self.subTest(changes=changes), self.assertRaises(HarnessError):
                assert_identity(dict(observed, **changes), expected, 'kkh_', 'run')

    def test_hidden_input_is_required_and_html_decoded(self):
        document = '<input type="hidden" name="redirect_to" value="/?a=1&amp;b=2">'
        self.assertEqual(hidden_input(document, 'redirect_to'), '/?a=1&b=2')
        with self.assertRaises(HarnessError):
            hidden_input(document, 'nonce')

    def test_production_runtime_stays_bounded(self):
        assert_production_shape()

    def test_release_package_includes_translation_catalogs(self):
        self.assertTrue({
            'languages/kklidi-members.pot',
            'languages/kklidi-members-ko_KR.po',
            'languages/kklidi-members-ko_KR.mo',
        }.issubset(PACKAGE_FILES))
        repository = Path(__file__).resolve().parents[2]
        builder = (repository / 'tests/harness/build_release.py').read_text(encoding='utf-8')
        self.assertIn("not path.startswith('docs/evidence/')", builder)
        self.assertNotIn('evidence_doc', builder)
        self.assertIn("'docs/NOTIFICATIONS.md'", builder)
        exporter = (repository / 'tests/harness/export_release_evidence.py').read_text(encoding='utf-8')
        self.assertIn("package_manifest['archive_sha256'] == package_sha256", exporter)
        self.assertIn("lifecycle['new_archive_sha256'] == package_sha256", exporter)
        self.assertIn("'strategy_contract': ux_strategy", exporter)

    def test_auth_ui_001_covers_every_runtime_surface(self):
        repository = Path(__file__).resolve().parents[2]
        contract = json.loads((repository / 'tests/harness/ui_contract.json').read_text(encoding='utf-8'))
        routes = {
            'login': ('kklidi_members_login', 'templates/login.php'),
            'register': ('kklidi_members_register', 'templates/register.php'),
            'account': ('kklidi_members_account', 'templates/account.php'),
            'profile': ('kklidi_members_profile', 'templates/profile.php'),
            'password': ('kklidi_members_password', 'templates/password.php'),
            'password_reset': ('kklidi_members_password_reset', 'templates/password-reset.php'),
            'consent': ('kklidi_members_consent', 'templates/consent.php'),
            'withdrawal': ('kklidi_members_withdrawal', 'templates/withdrawal.php'),
            'logout': ('kklidi_members_logout', 'templates/logout.php'),
        }

        self.assertEqual(contract['contract'], 'AUTH-UI-001')
        self.assertEqual(contract['version'], 2)
        self.assertEqual(contract['status'], 'SPECIFIED')
        self.assertEqual(contract['implementation_contract'], 'AUTH-UI-002')
        self.assertEqual(contract['strategy_contract'], 'AUTH-UX-003')
        self.assertEqual(contract['strategy_manifest'], 'tests/harness/ux_strategy_contract.json')
        self.assertEqual(set(contract['screens']), set(routes) | {'admin'})

        plugin_source = (repository / 'includes/Core/Plugin.php').read_text(encoding='utf-8')
        for screen_name, (route, template) in routes.items():
            with self.subTest(screen=screen_name):
                screen = contract['screens'][screen_name]
                self.assertEqual(screen['route'], route)
                self.assertEqual(screen['template'], template)
                self.assertTrue((repository / template).is_file())
                self.assertIn("'" + route + "'", plugin_source)
                self.assertTrue(screen['audiences'])
                self.assertTrue(screen['states'])
                self.assertEqual(len(screen['states']), len(set(screen['states'])))
                self.assertTrue(screen['requirements'])

        admin = contract['screens']['admin']
        self.assertEqual(admin['template'], 'templates/admin.php')
        self.assertTrue((repository / admin['template']).is_file())
        self.assertIn('manage_kklidi_members', admin['requirements'])

        required_global = {
            'wordpress_core_auth', 'server_rendered', 'gettext',
            'route_scoped_assets', 'keyboard_accessible', 'responsive',
            'no_external_assets', 'no_php_session',
        }
        self.assertTrue(required_global.issubset(set(contract['global_requirements'])))
        required_exclusions = {
            'theme_redesign', 'woocommerce_lms_ui',
            'email_verification_2fa_social', 'kboard_permission_engine',
        }
        self.assertTrue(required_exclusions.issubset(set(contract['out_of_scope'])))

    def test_auth_ux_003_tracks_implemented_runtime_slices(self):
        repository = Path(__file__).resolve().parents[2]
        contract = json.loads(
            (repository / 'tests/harness/ux_strategy_contract.json').read_text(encoding='utf-8')
        )
        ui_ux = (repository / 'docs/UI_UX.md').read_text(encoding='utf-8')
        product = (repository / 'docs/PRODUCT.md').read_text(encoding='utf-8')

        self.assertEqual(contract['contract'], 'AUTH-UX-003')
        self.assertEqual(contract['version'], 4)
        self.assertEqual(contract['status'], 'IMPLEMENTED_THROUGH_0.7.8')
        self.assertIn('`AUTH-UX-003` 상태: **0.7.8_WITHDRAWAL_AUDIT_OPERATIONS_IMPLEMENTED**', ui_ux)
        self.assertNotIn('email을 Core `user_login`으로 사용하는 신규 회원', ui_ux)
        self.assertIn('비공개 후보', ui_ux)
        self.assertIn('D09 | **DECIDED FOR 0.7.4', product)

        frontend = contract['frontend']
        self.assertEqual(frontend['surface'], 'standalone_branded_members_shell')
        self.assertFalse(frontend['theme_markup_dependency'])
        self.assertEqual(frontend['routes']['canonical_family'], '/members/')
        self.assertTrue(frontend['routes']['activation_requires_collision_preflight'])
        self.assertTrue(frontend['routes']['existing_query_routes_remain_fallback'])
        registration = frontend['registration']
        self.assertEqual(registration['wordpress_user_login'], 'opaque_private_candidate')
        self.assertEqual(registration['supported_login_identifiers'], ['email', 'legacy_username'])
        self.assertTrue(registration['duplicate_display_name_allowed'])
        self.assertFalse(registration['automatic_login'])
        self.assertFalse(registration['email_verification'])
        self.assertEqual(set(frontend['validation_recovery']['always_cleared']),
                         {'password', 'password_confirm', 'nonce', 'guest_token'})
        self.assertTrue(frontend['password_reset']['wordpress_core_keys_and_apis_only'])
        self.assertTrue(frontend['password_reset']['branded_wrapper_implemented'])
        self.assertFalse(frontend['password_reset']['custom_token_or_auth_system'])
        self.assertFalse(frontend['account_navigation']['members_queries_woocommerce_or_lms_domain_data'])
        self.assertTrue(frontend['account_navigation']['integrations_optional'])
        self.assertEqual(frontend['account_navigation']['slot_hook'],
                         'kklidi_members_account_navigation_links')

        admin = contract['admin']
        self.assertEqual(admin['menu_parent'], 'users')
        self.assertEqual(admin['sections'], ['overview', 'documents', 'withdrawals', 'audit'])
        self.assertEqual(admin['withdrawals']['allowed_transitions'],
                         ['withdrawal_pending_to_disabled',
                          'withdrawal_pending_to_active_with_reason'])
        self.assertTrue(admin['withdrawals']['wordpress_user_id_preserved'])
        self.assertTrue(admin['withdrawals']['external_domain_rows_preserved'])
        self.assertFalse(admin['notifications']['editable_templates'])
        self.assertFalse(admin['notifications']['retry_queue'])
        self.assertFalse(admin['core_users']['separate_user_registry'])
        self.assertFalse(admin['retention']['editable_before_legal_policy'])
        self.assertEqual(admin['capability'], 'manage_kklidi_members')

        boundaries = contract['boundaries']
        self.assertTrue(boundaries['wordpress_core_identity_and_auth'])
        self.assertTrue(boundaries['wordpress_user_ids_preserved'])
        self.assertFalse(boundaries['php_session_auth'])
        self.assertFalse(boundaries['global_frontend_assets'])
        self.assertTrue(boundaries['members_remains_optional_dependency'])
        self.assertFalse(boundaries['future_features_implemented'])
        self.assertEqual(list(contract['implementation_order']),
                         ['0.7.5', '0.7.6', '0.7.7', '0.7.8', '0.7.9'])
        self.assertEqual(contract['implementation']['completed'], ['0.7.5', '0.7.6', '0.7.7', '0.7.8'])

    def test_auth_ui_002_uses_scoped_styles_and_accessible_shells(self):
        repository = Path(__file__).resolve().parents[2]
        frontend_css = (repository / 'assets/css/members.css').read_text(encoding='utf-8')
        admin_css = (repository / 'assets/css/admin.css').read_text(encoding='utf-8')
        template_names = ('login', 'register', 'account', 'profile', 'password', 'password-reset',
                          'consent', 'withdrawal', 'logout')

        self.assertIn('@media (max-width: 480px)', frontend_css)
        self.assertIn(':focus-visible', frontend_css)
        self.assertNotIn('url(http', frontend_css.lower())
        self.assertNotIn('url(http', admin_css.lower())
        for name in template_names:
            with self.subTest(template=name):
                source = (repository / 'templates' / f'{name}.php').read_text(encoding='utf-8')
                self.assertIn('wp_head();', source)
                self.assertIn('wp_footer();', source)
                self.assertIn('kklidi-members-page', source)
                self.assertIn('kklidi-members-main', source)

        plugin_source = (repository / 'includes/Core/Plugin.php').read_text(encoding='utf-8')
        admin_source = (repository / 'includes/Admin/AdminController.php').read_text(encoding='utf-8')
        self.assertIn("add_action('wp_enqueue_scripts'", plugin_source)
        self.assertIn('is_frontend_route', plugin_source)
        self.assertIn('is_password_enhancement_route', plugin_source)
        self.assertIn('members-auth.js', plugin_source)
        self.assertIn("if (self::is_password_enhancement_route())", plugin_source)
        self.assertIn('cleanRoutePreflight',
                      (repository / 'includes/Core/Url.php').read_text(encoding='utf-8'))

        self.assertIn("add_action('admin_enqueue_scripts'", admin_source)
        self.assertIn("users_page_kklidi-members", admin_source)
        production_source = '\n'.join(path.read_text(encoding='utf-8') for path in (
            repository / 'kklidi-members.php',
            repository / 'includes/Core/Plugin.php',
            repository / 'includes/Admin/AdminController.php',
        ))
        self.assertIn('wp_enqueue_script(', production_source)
        self.assertNotIn('wp_enqueue_script(', admin_source)
        self.assertIn('data-kklidi-members-password-toggle',
                      (repository / 'templates/login.php').read_text(encoding='utf-8'))
        register_template = (repository / 'templates/register.php').read_text(encoding='utf-8')
        self.assertIn('<details', register_template)
        self.assertIn('data-kklidi-members-password-toggle', register_template)
        self.assertIn('aria-describedby', register_template)
        self.assertIn('.kklidi-members-password-toggle {\n\talign-items: center;\n\tdisplay: none;',
                      frontend_css)
        self.assertIn('.kklidi-members-has-js .kklidi-members-password-toggle {',
                      frontend_css)
        self.assertIn('display: inline-flex;', frontend_css)

        entry = (repository / 'kklidi-members.php').read_text(encoding='utf-8')
        version = re.search(r'\* Version: (\d+\.\d+\.\d+)', entry).group(1)
        plugin_readme = (repository / 'readme.txt').read_text(encoding='utf-8')
        self.assertIn('Stable tag: ' + version, plugin_readme)
        self.assertIn('= ' + version + ' =', plugin_readme)
        self.assertIn('docs/RELEASE-' + version + '.md', plugin_readme)

    def test_auth_ux_004_typography_contract_is_scoped_and_bounded(self):
        repository = Path(__file__).resolve().parents[2]
        contract = (repository / 'docs/TYPOGRAPHY.md').read_text(encoding='utf-8')
        css = (repository / 'assets/css/members.css').read_text(encoding='utf-8')

        self.assertIn('`AUTH-UX-004`', contract)
        self.assertIn('IMPLEMENTED_AND_UNIT_VERIFIED', contract)
        self.assertIn('0.7.9', contract)
        for token in (
            '--kklidi-members-font-body', '--kklidi-members-font-title',
            '--kklidi-members-font-section', '--kklidi-members-font-control',
            '--kklidi-members-font-meta', '--kklidi-members-font-legal',
            '--kklidi-members-line-body',
        ):
            with self.subTest(token=token):
                self.assertIn(token, css)
        self.assertIn('clamp(1.75rem, 3.6vw, 2rem)', css)
        self.assertIn('font-size: var(--kklidi-members-font-body)', css)
        self.assertIn('font-size: var(--kklidi-members-font-legal)', css)
        self.assertIn('line-height: 1.7', css)
        self.assertNotIn('font-size: clamp(1.75rem, 5vw, 2.35rem)', css)
        self.assertNotIn('url(http', css.lower())

    def test_auth_ux_003_076_core_reset_and_link_slots_are_bounded(self):
        repository = Path(__file__).resolve().parents[2]
        reset = (repository / 'includes/Auth/PasswordResetController.php').read_text(encoding='utf-8')
        account = (repository / 'includes/Frontend/AccountController.php').read_text(encoding='utf-8')
        plugin = (repository / 'includes/Core/Plugin.php').read_text(encoding='utf-8')
        limiter = (repository / 'includes/Security/RateLimiter.php').read_text(encoding='utf-8')
        package = (repository / 'tests/harness/run.py').read_text(encoding='utf-8')

        for core_api in ('retrieve_password(', 'check_password_reset_key(', 'reset_password('):
            self.assertIn(core_api, reset)
        self.assertIn("add_filter('retrieve_password_notification_email'", reset)
        self.assertIn("$email['message']", reset)
        for preserved in ("$email['subject']", "$email['headers']", "$email['from']"):
            self.assertNotIn(preserved, reset)
        self.assertIn("header('Referrer-Policy: no-referrer')", reset)
        self.assertIn("header('Cache-Control: no-store", reset)
        self.assertIn('kklidi_members_rate_limited', reset)
        self.assertIn('get_error_codes()', reset)
        self.assertIn('If an account matches that information', reset)
        self.assertIn("add_filter('lostpassword_errors'", limiter)
        self.assertIn('reset_subject', limiter)
        self.assertIn('reset_network', limiter)
        for forbidden in ('session_start(', 'setcookie(', 'wp_set_auth_cookie(', 'wp_insert_user(',
                          'random_bytes(', 'hash_hmac(', 'add_option(', 'update_option('):
            self.assertNotIn(forbidden, reset)

        self.assertIn("apply_filters('kklidi_members_account_navigation_links'", account)
        self.assertIn('Url::optionalLocal', account)
        self.assertNotRegex(account, r'WC_|WooCommerce|kklidi_lms|enrollment|progress|order')
        self.assertIn("'kklidi_members_password_reset'", plugin)
        self.assertIn("'includes/Auth/PasswordResetController.php'", package)
        self.assertIn("'templates/password-reset.php'", package)

    def test_auth_ux_003_077_admin_information_architecture_is_bounded(self):
        repository = Path(__file__).resolve().parents[2]
        admin = (repository / 'includes/Admin/AdminController.php').read_text(encoding='utf-8')
        documents = (repository / 'includes/Consent/Documents.php').read_text(encoding='utf-8')
        consent = (repository / 'includes/Consent/Repository.php').read_text(encoding='utf-8')
        template = (repository / 'templates/admin.php').read_text(encoding='utf-8')

        self.assertIn('add_users_page(', admin)
        self.assertIn("admin_url('users.php')", admin)
        self.assertIn("$pagenow === 'tools.php'", admin)
        self.assertIn("users_page_kklidi-members", admin)
        for section in ('overview', 'documents', 'notifications', 'withdrawals', 'audit'):
            self.assertIn("'" + section + "'", admin)
        for check in ('users_can_register', 'cleanRoutePreflight',
                      'kklidi_mem_login_audit', 'kklidi_mem_consents',
                      'kklidi_members_daily_cleanup'):
            self.assertIn(check, admin)
        self.assertIn('Documents::preview(', admin)
        self.assertIn('Documents::history(', admin)
        self.assertIn('public static function preview(', documents)
        self.assertIn('public static function history(', documents)
        self.assertIn("add_option($name, $snapshot, '', 'no')", documents)
        self.assertIn('public static function has_current_required(', consent)
        self.assertIn("manage_users_columns", admin)
        self.assertIn("manage_users_custom_column", admin)
        self.assertIn("restrict_manage_users", admin)
        self.assertIn("pre_get_users", admin)
        self.assertIn("pre_user_query", admin)
        self.assertIn('manage_kklidi_members', admin)
        self.assertIn('nav-tab-wrapper', template)
        self.assertIn('Unpublished preview', template)
        self.assertIn('Published history', template)
        self.assertNotIn('wp_delete_user(', admin)
        self.assertNotRegex(admin, r'WC_|WooCommerce|kklidi_lms|enrollment|progress')

    def test_auth_admin_ux_001_keeps_route_canonical_and_admin_setup_bounded(self):
        repository = Path(__file__).resolve().parents[2]
        contract = json.loads((repository / 'tests/harness/admin_ux_contract.json').read_text(encoding='utf-8'))
        self.assertEqual(contract['contract'], 'AUTH-ADMIN-UX-001')
        self.assertEqual(contract['target_release'], '0.7.17')
        self.assertFalse(contract['overview']['automatic_page_creation'])
        self.assertFalse(contract['overview']['automatic_menu_mutation'])
        self.assertEqual(len(contract['overview']['route_links']), 9)
        self.assertEqual(contract['notifications']['approved_events'], 4)
        self.assertFalse(contract['notifications']['html'])
        self.assertFalse(contract['notifications']['test_send'])
        admin_source = (repository / 'includes/Admin/AdminController.php').read_text(encoding='utf-8')
        admin_template = (repository / 'templates/admin.php').read_text(encoding='utf-8')
        admin_css = (repository / 'assets/css/admin.css').read_text(encoding='utf-8')
        for marker in ('$quick_links', '$route_urls', 'WordPress registration settings', 'Member route links'):
            self.assertIn(marker, admin_source + admin_template)
        for marker in ('kklidi-members-quick-links', 'kklidi-members-quick-link', 'kklidi-members-queue-count'):
            self.assertIn(marker, admin_css + admin_template)
        self.assertIn('get_edit_user_link(', admin_template)
        self.assertIn("current_user_can('edit_user'", admin_template)
        self.assertIn("current_user_can('manage_options')", admin_source)
        self.assertIn('Clear filters', admin_template)
        self.assertIn('Leave a field empty to restore its translated default.', admin_template)

    def test_auth_ux_003_078_withdrawal_and_audit_operations_are_bounded(self):
        repository = Path(__file__).resolve().parents[2]
        admin = (repository / 'includes/Admin/AdminController.php').read_text(encoding='utf-8')
        template = (repository / 'templates/admin.php').read_text(encoding='utf-8')
        harness = (repository / 'tests/harness/run.py').read_text(encoding='utf-8')

        self.assertIn("review_withdrawal('disabled')", admin)
        self.assertIn("review_withdrawal('active')", admin)
        self.assertIn("$target_state === 'active' && ($reason === '' || self::text_length($reason) > 500)", admin)
        self.assertIn("function_exists('mb_strlen') ? mb_strlen($value, 'UTF-8') : strlen($value)", admin)
        self.assertIn("AccountState::get($user_id) !== 'withdrawal_pending'", admin)
        self.assertIn("AccountState::revoke_access($user_id)", admin)
        self.assertIn("'withdrawal_restored'", admin)
        self.assertIn("'withdrawal_disabled'", admin)
        self.assertIn("Recorder::record($event, 'success'", admin)
        self.assertIn("if ($target_state === 'disabled')", admin)
        self.assertIn("AccountMailer::send('withdrawal_finalized'", admin)
        self.assertIn("'event' => self::requested_filter('audit_event')", admin)
        self.assertIn("'result' => self::requested_filter('audit_result')", admin)
        self.assertIn("'date' => self::requested_text('audit_date')", admin)
        self.assertIn("'user_id' => isset($_GET['audit_user_id'])", admin)
        self.assertIn('$per_page = 25;', admin)
        self.assertIn('min(100,', admin)
        self.assertNotIn('subject_digest', template)
        self.assertNotIn('network_digest', template)
        self.assertIn('value="restore_withdrawal"', template)
        self.assertIn('name="review_reason"', template)
        self.assertIn('name="audit_event"', template)
        self.assertIn('name="audit_result"', template)
        self.assertIn('name="audit_date"', template)
        self.assertIn('name="audit_user_id"', template)
        self.assertIn("'admin_restore_with_reason': True", harness)
        self.assertIn("'bounded_page_size': 25", harness)
        for forbidden in ('wp_delete_user(', 'wp_set_auth_cookie(', 'session_start('):
            self.assertNotIn(forbidden, admin)

    def test_phase_zero_documents_do_not_report_completed_ui_as_pending(self):
        repository = Path(__file__).resolve().parents[2]
        product = (repository / 'docs/PRODUCT.md').read_text(encoding='utf-8')
        ui_ux = (repository / 'docs/UI_UX.md').read_text(encoding='utf-8')
        harness = (repository / 'docs/HARNESS_PLAN.md').read_text(encoding='utf-8')

        self.assertNotIn('AUTH-UI-002` 구현·브라우저 검증 대기', product)
        self.assertIn('AUTH-UI-002` 상태: **IMPLEMENTED_AND_VERIFIED**', ui_ux)
        self.assertIn('현재 판정은 최신 릴리스 문서', harness)
        self.assertNotIn('현재 실행 결과는 §5와 0.5.0 릴리스 문서', harness)

    def test_auth_notify_001_runtime_is_bounded(self):
        repository = Path(__file__).resolve().parents[2]
        contract = json.loads(
            (repository / 'tests/harness/notification_contract.json').read_text(encoding='utf-8')
        )

        self.assertEqual(contract['contract'], 'AUTH-NOTIFY-001')
        self.assertEqual(contract['version'], 2)
        self.assertEqual(contract['status'], 'SPECIFIED')
        self.assertEqual(contract['implementation_status'], 'IMPLEMENTED_AND_SYNTHETIC_VERIFIED')
        self.assertEqual(contract['implementation_phase'], 'P0-4')
        self.assertEqual(contract['verification'], {
            'status': 'PASS',
            'scope': 'synthetic_wordpress',
            'prefixes': ['wp_', 'non_default'],
            'mail_failure_injection': 'PASS',
            'evidence_id': '5886351d4d39439993fae700b0cb610a',
            'report': '.harness/reports/latest.json',
        })
        self.assertEqual(contract['transport'], {
            'api': 'wp_mail',
            'format': 'text/plain',
            'sender': 'wordpress_default',
            'smtp_owned_by_members': False,
        })
        self.assertEqual(contract['localization']['verification'], {
            'status': 'PASS', 'site_fallback': 'ko_KR', 'user_locale': 'ko_KR',
            'catalog_msgids': 12, 'report': '.harness/reports/latest.json',
        })

        events = contract['events']
        self.assertEqual(set(events), {
            'registration_completed',
            'password_changed',
            'withdrawal_requested',
            'withdrawal_finalized',
        })
        self.assertEqual(events['registration_completed']['transition'],
                         ['registration_pending', 'active'])
        self.assertEqual(events['withdrawal_requested']['transition'],
                         ['active', 'withdrawal_pending'])
        self.assertEqual(events['withdrawal_finalized']['transition'],
                         ['withdrawal_pending', 'disabled'])
        self.assertEqual(events['password_changed']['trigger'],
                         'core_password_changed_and_sessions_revoked')

        secrets = {'password', 'reset_key', 'auth_cookie', 'nonce'}
        for event_name, event in events.items():
            with self.subTest(event=event_name):
                self.assertEqual(event['recipient'], 'wordpress_user_email')
                self.assertTrue(event['after'])
                self.assertTrue(event['required_content'])
                self.assertTrue(secrets.issubset(set(event['forbidden_content'])))

        delivery = contract['delivery']
        self.assertTrue(delivery['after_state_commit'])
        self.assertEqual(delivery['logical_idempotency'], 'event_type_plus_event_id')
        self.assertTrue(delivery['duplicate_request_must_not_duplicate_logical_notification'])
        self.assertFalse(delivery['exactly_once_delivery_claimed'])
        self.assertTrue(delivery['mail_failure_must_not_rollback_security_state'])
        self.assertTrue(delivery['mail_failure_must_not_be_reported_as_delivered'])
        self.assertEqual(delivery['mail_failure_behavior'], {
            'events': [
                'registration_completed', 'password_changed',
                'withdrawal_requested', 'withdrawal_finalized',
            ],
            'injected_wp_mail_return': False,
            'committed_operation_response': 'success',
            'audit_result': 'failure',
            'audit_reason_code': 'wp_mail_failed',
            'delivery_records': 0,
            'retry_attempts': 0,
        })

        boundaries = contract['boundaries']
        self.assertTrue(boundaries['wordpress_core_auth_preserved'])
        self.assertTrue(boundaries['wordpress_user_ids_preserved'])
        self.assertEqual(boundaries['woocommerce_order_mail_owned_by'], 'woocommerce')
        self.assertEqual(boundaries['lms_learning_mail_owned_by'], 'lms')
        self.assertTrue(boundaries['members_optional_dependency'])
        self.assertFalse(boundaries['global_frontend_bootstrap'])

        required_exclusions = {
            'email_verification', 'email_change_verification', 'otp', 'two_factor',
            'marketing_campaigns', 'admin_notification_recipients',
            'editable_templates', 'template_preview', 'test_send', 'retry_queue',
            'delivery_log', 'smtp_provider', 'woocommerce_order_mail',
            'lms_learning_mail', 'kboard_mail',
        }
        self.assertTrue(required_exclusions.issubset(set(contract['out_of_scope'])))

        notification_doc = (repository / 'docs/NOTIFICATIONS.md').read_text(encoding='utf-8')
        product_doc = (repository / 'docs/PRODUCT.md').read_text(encoding='utf-8')
        self.assertIn('AUTH-NOTIFY-001', notification_doc)
        self.assertIn('Runtime 상태 | **IMPLEMENTED_AND_SYNTHETIC_VERIFIED**', notification_doc)
        self.assertIn('| D08 | **DECIDED 2026-09-09**', product_doc)

        mailer = (repository / 'includes/Notifications/AccountMailer.php').read_text(encoding='utf-8')
        self.assertEqual(mailer.count('wp_mail('), 1)
        self.assertIn("Content-Type: text/plain; charset=", mailer)
        self.assertIn('switch_to_user_locale($user_id)', mailer)
        self.assertIn("get_user_by('id', $user_id)", mailer)
        self.assertIn("Recorder::claim_notification($event, $user_id, $event_id)", mailer)

        plugin = (repository / 'includes/Core/Plugin.php').read_text(encoding='utf-8')
        self.assertNotIn('Notifications/AccountMailer.php', plugin)
        self.assertNotIn('wp_mail(', plugin)
        for path, event in {
            'includes/Registration/RegistrationController.php': 'registration_completed',
            'includes/Auth/PasswordController.php': 'password_changed',
            'includes/Withdrawal/WithdrawalController.php': 'withdrawal_requested',
            'includes/Admin/AdminController.php': 'withdrawal_finalized',
        }.items():
            with self.subTest(path=path):
                source = (repository / path).read_text(encoding='utf-8')
                self.assertIn('includes/Notifications/AccountMailer.php', source)
                self.assertIn("AccountMailer::send('" + event + "'", source)

        registration = (repository / 'includes/Registration/RegistrationController.php').read_text(
            encoding='utf-8'
        )
        self.assertLess(registration.index('SELECT RELEASE_LOCK'),
                        registration.index("AccountMailer::send('registration_completed'"))

        harness = (repository / 'tests/harness/run.py').read_text(encoding='utf-8')
        self.assertIn("'includes/Notifications/AccountMailer.php'", harness)
        self.assertIn("results['AUTH-NOTIFY-001']", harness)
        self.assertIn("KKH_MAIL_FAILURE=str(root / 'mail-failure.enabled')", harness)
        self.assertIn("'mail_failure_events': 4", harness)
        self.assertIn("'mail_failure_injected_attempts': 4", harness)
        self.assertIn("'mail_failure_delivery_records': 0", harness)
        self.assertIn("'mail_failure_retry_attempts': 0", harness)
        observer = (repository / 'tests/harness/observer.php').read_text(encoding='utf-8')
        self.assertIn("kkh_record(['type' => 'mail_failed'])", observer)
        self.assertIn('return false;', observer)

    def test_auth_notify_002_core_first_design_is_bounded(self):
        repository = Path(__file__).resolve().parents[2]
        contract = json.loads(
            (repository / 'tests/harness/notification_settings_contract.json').read_text(
                encoding='utf-8'
            )
        )

        self.assertEqual(contract['contract'], 'AUTH-NOTIFY-002')
        self.assertEqual(contract['version'], 1)
        self.assertEqual(contract['status'], 'IMPLEMENTED_AND_SYNTHETIC_VERIFIED')
        self.assertEqual(contract['target_release'], '0.7.10')
        self.assertEqual(contract['depends_on'], 'AUTH-NOTIFY-001')
        self.assertEqual(contract['principle'], 'wordpress_core_first')
        self.assertEqual(contract['verification'], {
            'status': 'PASS',
            'scope': 'synthetic_wordpress',
            'prefixes': ['wp_', 'non_default'],
            'evidence_id': 'd28853b554c5497eb50df18d7f24dffe',
            'report': '.harness/reports/latest.json',
        })

        admin = contract['admin']
        self.assertEqual(admin['menu_parent'], 'users')
        self.assertEqual(admin['section'], 'notifications')
        self.assertEqual(admin['api'], 'wordpress_settings_api')
        self.assertEqual(admin['capability'], 'manage_kklidi_members')
        self.assertTrue(admin['server_nonce_required'])
        self.assertEqual(admin['editable_fields'], ['subject', 'body'])
        self.assertFalse(admin['per_event_disable'])
        self.assertEqual(admin['sender_policy_display'], 'read_only')

        storage = contract['storage']
        self.assertEqual(storage['api'], 'wordpress_options')
        self.assertEqual(storage['option_name'], 'kklidi_members_notification_templates')
        self.assertEqual(storage['schema_version'], 1)
        self.assertFalse(storage['autoload'])
        self.assertFalse(storage['custom_table'])
        self.assertEqual(storage['fallback'], 'gettext_defaults')

        self.assertEqual(contract['transport'], {
            'api': 'wp_mail',
            'format': 'text/plain',
            'sender': 'wordpress_or_site_transport_default',
            'members_registers_global_sender_filters': False,
            'smtp_owned_by_members': False,
            'provider_credentials_stored': False,
        })

        expected_placeholders = {
            'registration_completed': ['site_name', 'login_url'],
            'password_changed': ['site_name', 'password_reset_url'],
            'withdrawal_requested': ['site_name'],
            'withdrawal_finalized': ['site_name'],
        }
        self.assertEqual(set(contract['events']), set(expected_placeholders))
        for event, placeholders in expected_placeholders.items():
            with self.subTest(event=event):
                self.assertEqual(contract['events'][event]['editable'], ['subject', 'body'])
                self.assertEqual(contract['events'][event]['allowed_placeholders'], placeholders)

        validation = contract['validation']
        self.assertEqual(validation['subject_max_chars'], 200)
        self.assertEqual(validation['body_max_chars'], 5000)
        self.assertFalse(validation['raw_html'])
        self.assertFalse(validation['shortcodes'])
        self.assertFalse(validation['php'])
        self.assertEqual(validation['unknown_placeholders'], 'reject')
        self.assertEqual(validation['empty_or_invalid'], 'use_gettext_default')

        forbidden = set(contract['security']['forbidden_values'])
        self.assertTrue({
            'password', 'reset_key', 'auth_cookie', 'nonce', 'wordpress_user_id',
            'role', 'order_data', 'lms_data',
        }.issubset(forbidden))
        self.assertEqual(
            contract['security']['settings_update_audit'],
            'metadata_only_no_template_content',
        )
        self.assertEqual(
            contract['security']['mail_failure_behavior'], 'preserve_auth_notify_001'
        )

        boundaries = contract['boundaries']
        self.assertTrue(boundaries['wordpress_core_auth_preserved'])
        self.assertTrue(boundaries['wordpress_user_ids_preserved'])
        self.assertEqual(
            boundaries['wordpress_core_password_reset_mail_owned_by'], 'wordpress_core'
        )
        self.assertEqual(boundaries['woocommerce_order_mail_owned_by'], 'woocommerce')
        self.assertEqual(boundaries['lms_learning_mail_owned_by'], 'lms')
        self.assertEqual(boundaries['kboard_mail_owned_by'], 'kboard')
        self.assertTrue(boundaries['members_optional_dependency'])
        self.assertFalse(boundaries['global_frontend_bootstrap'])

        required_exclusions = {
            'wordpress_core_password_reset_mail_template', 'admin_notification_recipients',
            'per_event_disable', 'html_email', 'wysiwyg_editor', 'template_preview',
            'test_send', 'retry_queue', 'delivery_webhooks', 'delivery_log',
            'smtp_settings', 'provider_api', 'provider_credentials',
            'global_sender_override', 'woocommerce_order_mail', 'lms_learning_mail',
            'kboard_mail',
        }
        self.assertTrue(required_exclusions.issubset(set(contract['out_of_scope'])))

        notification_doc = (repository / 'docs/NOTIFICATIONS.md').read_text(encoding='utf-8')
        product_doc = (repository / 'docs/PRODUCT.md').read_text(encoding='utf-8')
        architecture_doc = (repository / 'docs/ARCHITECTURE.md').read_text(encoding='utf-8')
        self.assertIn('AUTH-NOTIFY-002', notification_doc)
        self.assertIn('IMPLEMENTED_AND_SYNTHETIC_VERIFIED', notification_doc)
        self.assertIn('| D10 | **DECIDED FOR 0.7.10 2026-09-09**', product_doc)
        self.assertIn('Settings API', architecture_doc)
        self.assertNotIn('wp_mail_from', architecture_doc)

        settings = (repository / 'includes/Notifications/NotificationTemplates.php').read_text(
            encoding='utf-8'
        )
        admin_source = (repository / 'includes/Admin/AdminController.php').read_text(
            encoding='utf-8'
        )
        admin_template = (repository / 'templates/admin.php').read_text(encoding='utf-8')
        installer = (repository / 'includes/Core/Installer.php').read_text(encoding='utf-8')
        mailer = (repository / 'includes/Notifications/AccountMailer.php').read_text(
            encoding='utf-8'
        )
        package = (repository / 'tests/harness/run.py').read_text(encoding='utf-8')

        self.assertIn("register_setting(self::OPTION_GROUP, self::OPTION_NAME", settings)
        self.assertIn("'sanitize_callback' => array(__CLASS__, 'sanitize')", settings)
        self.assertIn("'show_in_rest' => false", settings)
        self.assertIn("return 'manage_kklidi_members';", settings)
        self.assertIn("sanitize_text_field($raw)", settings)
        self.assertIn("sanitize_textarea_field($raw)", settings)
        self.assertIn("wp_strip_all_tags($raw)", settings)
        self.assertIn("strtr($value, self::placeholder_values($event))", settings)
        self.assertIn("'notification_settings_update'", settings)
        self.assertIn("'admin_settings'", settings)
        self.assertNotRegex(settings, r'(?m)^\s*(?:return\s+)?wp_mail\(')
        self.assertNotIn("add_filter('wp_mail_from", settings)
        self.assertNotIn('WC_', settings)
        self.assertNotIn('kklidi_lms', settings)
        self.assertIn("add_option(self::OPTION_NAME, self::empty_settings(), '', false)", settings)
        self.assertIn('Empty fields use the translated default at send time for the recipient locale.', settings)
        self.assertIn('placeholder="<?php echo esc_attr__(\'Leave empty to use the translated default subject.', settings)
        self.assertIn('placeholder="<?php echo esc_attr__(\'Leave empty to use the translated default message for the recipient locale.', settings)
        self.assertIn("add_option('kklidi_members_notification_templates'", installer)
        self.assertIn("), '', false);", installer)
        self.assertIn("'notifications'", admin_source)
        self.assertIn('option_page_capability_kklidi_members_notifications', admin_source)
        self.assertIn('update_option_kklidi_members_notification_templates', admin_source)
        self.assertIn(
            "settings_fields(\\KKLIDI\\Members\\Notifications\\NotificationTemplates::OPTION_GROUP)",
            admin_template,
        )
        self.assertIn(
            "do_settings_sections(\\KKLIDI\\Members\\Notifications\\NotificationTemplates::SETTINGS_PAGE)",
            admin_template,
        )
        self.assertIn("NotificationTemplates::content($event)", mailer)
        self.assertIn('A request blocks sign-in immediately. Finalization records review completion', admin_template)
        withdrawal_template = (repository / 'templates/withdrawal.php').read_text(encoding='utf-8')
        self.assertIn('Submitting this request blocks sign-in immediately.', withdrawal_template)
        self.assertIn('Submit request and block sign-in', withdrawal_template)
        login_controller = (repository / 'includes/Auth/LoginController.php').read_text(encoding='utf-8')
        register_template = (repository / 'templates/register.php').read_text(encoding='utf-8')
        self.assertIn('Please sign in with the email address you registered.', login_controller)
        self.assertIn('sign in with the email address you registered;', register_template)
        self.assertIn('registration does not sign you in automatically.', register_template)
        reset_template = (repository / 'templates/password-reset.php').read_text(encoding='utf-8')
        self.assertIn('If an account matches, WordPress will send a password reset link.', reset_template)
        self.assertIn("'includes/Notifications/NotificationTemplates.php'", package)
        self.assertIn("results['AUTH-NOTIFY-002']", package)
        self.assertIn("'extension_contracts_total': 2", package)

    def test_auth_notify_001_catalog_covers_mail_presets(self):
        repository = Path(__file__).resolve().parents[2]
        templates = (repository / 'includes/Notifications/NotificationTemplates.php').read_text(
            encoding='utf-8'
        )
        defaults = templates.split('private static function default_content', 1)[1].split(
            'private static function placeholder_values', 1
        )[0]
        msgids = re.findall(r"__\(\s*'([^']*)'\s*,\s*'kklidi-members'\s*\)", defaults)
        self.assertEqual(len(msgids), 12)
        self.assertEqual(len(set(msgids)), len(msgids))

        pot = read_po(repository / 'languages/kklidi-members.pot')
        catalog = read_po(repository / 'languages/kklidi-members-ko_KR.po')
        with (repository / 'languages/kklidi-members-ko_KR.mo').open('rb') as stream:
            translations = gettext.GNUTranslations(stream)
        for msgid in msgids:
            with self.subTest(msgid=msgid):
                self.assertIn(msgid, pot)
                self.assertIn(msgid, catalog)
                self.assertTrue(catalog[msgid])
                self.assertNotEqual(catalog[msgid], msgid)
                self.assertNotEqual(translations.gettext(msgid), msgid)

        harness = (repository / 'tests/harness/run.py').read_text(encoding='utf-8')
        self.assertIn("'set-site-locale', 'ko_KR'", harness)
        self.assertIn("'set-user-locale', 'ko_KR'", harness)
        self.assertIn("languages/kklidi-members-ko_KR.mo", harness)

    def test_tls_runner_confines_openssl_random_state_to_run_directory(self):
        repository = Path(__file__).resolve().parents[2]
        source = (repository / 'tests/harness/mamp_https_run.py').read_text(encoding='utf-8')

        self.assertIn("openssl_env = dict(os.environ, RANDFILE=str(directory / '.rnd'))", source)
        self.assertEqual(source.count('env=openssl_env'), 3)
        self.assertEqual(source.count('cwd=directory'), 3)
        self.assertIn("report['certificate_root_removed'] = not https_root.exists()", source)

    def test_mamp_woo_fixture_is_pinned_and_self_cleaning(self):
        repository = Path(__file__).resolve().parents[2]
        source = (repository / 'tests/harness/mamp_woo_case.php').read_text(encoding='utf-8')
        self.assertIn("$sandbox_root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';", source)
        self.assertNotIn('$argv[3]', source)
        self.assertNotIn('$action =', source)
        self.assertIn('$fixture_action =', source)
        self.assertIn("preg_match('/^[a-f0-9]{12}$/', $run_token)", source)
        self.assertIn("untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox'", source)
        self.assertIn("'_kklidi_members_test_run'", source)
        self.assertIn("$order->delete(true);", source)
        self.assertIn("wp_delete_user((int) $state['user_id']);", source)
        self.assertIn("$restore_option($name, $snapshot);", source)
        self.assertIn("deactivate_plugins($wci_plugin, true);", source)
        self.assertIn("$fixture_action === 'members-off'", source)
        self.assertIn("$fixture_action === 'members-on'", source)
        self.assertIn("'members_was_active' => is_plugin_active($members_plugin)", source)

    def test_mamp_lms_fixture_is_pinned_and_self_cleaning(self):
        repository = Path(__file__).resolve().parents[2]
        source = (repository / 'tests/harness/mamp_lms_case.php').read_text(encoding='utf-8')
        harness = (repository / 'tests/harness/run.py').read_text(encoding='utf-8')
        self.assertIn("DEVICE_REFERENCE = Path('C:/MAMP/htdocs/kklidi-members-mamp-sandbox/wp-content/plugins/kklidi-device-limit')", harness)
        self.assertIn("DEVICE_REFERENCE_VERSION = '1.1.3'", harness)
        self.assertIn("DEVICE_REFERENCE_MANIFEST_SHA256 = '2549b2ecf89008d5719526882c82a46c1978f129ce9225f41d446544db935168'", harness)
        self.assertIn("$sandbox_root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';", source)
        self.assertNotIn('$argv[3]', source)
        self.assertNotIn('$action =', source)
        self.assertIn('$fixture_action =', source)
        self.assertIn("preg_match('/^[a-f0-9]{12}$/', $run_token)", source)
        self.assertIn("untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox'", source)
        self.assertIn("'_kklidi_members_lms_test_run'", source)
        self.assertIn("'pre_wp_mail'", source)
        self.assertIn("$wpdb->delete(kklidi_lms_table('private_questions')", source)
        self.assertIn('wp_delete_post($post_id, true);', source)
        self.assertIn('wp_delete_user($user_id);', source)
        self.assertIn('$restore_option($name, $snapshot);', source)
        self.assertIn("$fixture_action === 'members-off'", source)
        self.assertIn("$fixture_action === 'members-on'", source)
        self.assertIn("$fixture_action === 'student-cookie'", source)
        self.assertIn("$fixture_action === 'outsider-cookie'", source)
        self.assertIn('wp_generate_auth_cookie(', source)
        self.assertIn('kklidi_dl_register_device(', source)
        self.assertIn("'kklidi_dl_fp'", source)
        self.assertIn('kklidi_dl_sign_fingerprint(', source)
        self.assertIn("$wpdb->prefix . KKLIDI_DL_TABLE", source)
        self.assertIn('KKLIDI_LMS_WooCommerce::capture_order_item_entitlement(', source)
        self.assertIn('KKLIDI_LMS_WooCommerce::reconcile_order(', source)
        self.assertIn('KKLIDI_LMS_Enrollments::get_by_order(', source)
        self.assertIn("$order->delete(true);", source)
        self.assertIn("$product->delete(true);", source)
        self.assertIn("'kklidi_lms_allow_hard_delete'", source)
        self.assertIn("'_kklidi_members_lms_test_run'", source)

        runner = (repository / 'tests/harness/mamp_lms_run.py').read_text(encoding='utf-8')
        self.assertIn("BASE = 'http://localhost:8888/kklidi-members-mamp-sandbox/'", runner)
        self.assertNotIn('argparse', runner)
        self.assertIn("call('cleanup')", runner)
        self.assertIn("'.harness/reports'", runner)
        self.assertIn('wordpress_user_id_preserved=True', runner)

        lifecycle = (repository / 'tests/harness/mamp_lifecycle_run.py').read_text(encoding='utf-8')
        self.assertIn("SANDBOX = Path('C:/MAMP/htdocs/kklidi-members-mamp-sandbox')", lifecycle)
        self.assertIn("PREVIOUS_VERSION = '0.7.12'", lifecycle)
        self.assertIn("ALLOWED_INITIAL_VERSIONS = ('0.7.0', PREVIOUS_VERSION, CURRENT_VERSION)", lifecycle)
        self.assertIn("CURRENT_VERSION = re.search(", lifecycle)
        self.assertIn("OLD_ARCHIVE = ROOT / ('dist/kklidi-members-' + PREVIOUS_VERSION + '.zip')", lifecycle)
        self.assertIn("NEW_ARCHIVE = ROOT / ('dist/kklidi-members-' + CURRENT_VERSION + '.zip')", lifecycle)
        self.assertIn('not in ALLOWED_INITIAL_VERSIONS', lifecycle)
        self.assertNotIn('argparse', lifecycle)
        self.assertIn('assert_plugin_parent_writable(token)', lifecycle)
        self.assertIn('os.replace(source, destination)', lifecycle)
        self.assertNotIn('shutil.move(', lifecycle)
        self.assertIn('move_same_volume(original, PLUGIN)', lifecycle)
        self.assertIn('domain_fingerprint_preserved=True', lifecycle)
        self.assertIn('protected_table_count=', lifecycle)
        self.assertIn('woocommerce_sessions', lifecycle)
        self.assertIn("'.harness/reports'", lifecycle)

    def test_lms_profile_delegation_is_route_scoped(self):
        repository = Path(__file__).resolve().parents[2]
        source = (repository / 'includes/Core/Plugin.php').read_text(encoding='utf-8')
        self.assertIn("shortcode_exists('kklidi_lms_my_classroom')", source)
        self.assertIn("has_shortcode((string) $page->post_content, 'kklidi_lms_my_classroom')", source)
        self.assertIn("is_singular('page')", source)
        self.assertIn("wp_safe_redirect(Url::profile());", source)
        self.assertNotIn('KKLIDI_LMS_Enrollments', source)
        self.assertNotIn("kklidi_lms_table(", source)

    def test_registration_uses_core_gate_and_ignores_legacy_toggle(self):
        repository = Path(__file__).resolve().parents[2]
        registration = (repository / 'includes/Registration/RegistrationController.php').read_text(encoding='utf-8')
        admin = (repository / 'includes/Admin/AdminController.php').read_text(encoding='utf-8')
        installer = (repository / 'includes/Core/Installer.php').read_text(encoding='utf-8')
        template = (repository / 'templates/admin.php').read_text(encoding='utf-8')
        setup = (repository / 'tests/harness/mvp_setup.php').read_text(encoding='utf-8')

        self.assertIn("get_option('users_can_register', false)", registration)
        self.assertIn('Documents::required_ready()', registration)
        self.assertNotIn("get_option('kklidi_members_registration_enabled'", registration)
        self.assertNotIn("update_option('kklidi_members_registration_enabled'", admin)
        self.assertIn("delete_option('kklidi_members_registration_enabled');", admin)
        self.assertIn("delete_option('kklidi_members_registration_enabled');", installer)
        self.assertNotIn('name="registration_enabled"', template)
        self.assertIn('Public registration remains controlled by the WordPress General Settings screen.', template)
        self.assertIn("$mode === 'core-on-no-documents'", setup)
        self.assertIn("$mode === 'documents-ready-core-off'", setup)
        self.assertIn("$mode === 'core-on'", setup)
        self.assertIn("update_option('kklidi_members_registration_enabled', '0'", setup)

    def test_post_050_gates_have_bounded_executable_checks(self):
        repository = Path(__file__).resolve().parents[2]
        template = (repository / 'templates/register.php').read_text(encoding='utf-8')
        self.assertRegex(template, r'name="phone"[^>]*>')
        self.assertNotRegex(template, r'name="phone"[^>]*required')

        d06 = (repository / 'tests/harness/reference_d06_audit.php').read_text(encoding='utf-8')
        self.assertIn("$root = 'C:/MAMP/htdocs/ns_0727';", d06)
        self.assertIn('SET SESSION TRANSACTION READ ONLY', d06)
        self.assertIn('$db->rollback();', d06)
        self.assertNotIn("require $root . '/wp-load.php'", d06)

        for name in ('mamp_race_case.php', 'mamp_timing_case.php', 'mamp_environment_case.php'):
            source = (repository / 'tests/harness' / name).read_text(encoding='utf-8')
            self.assertIn("C:/MAMP/htdocs/kklidi-members-mamp-sandbox", source)
            self.assertNotIn('$argv[3]', source)

        preflight = (repository / 'tests/harness/deployment_preflight.py').read_text(encoding='utf-8')
        self.assertIn("parsed.scheme != 'https'", preflight)
        self.assertIn("'network_request_sent': False", preflight)
        self.assertIn("'__Host-kklidi_members_guest'", preflight)
        self.assertIn("'guest_cookie_host_only'", preflight)
        self.assertNotIn('password', preflight.split('def inspect', 1)[0])

        https_runner = (repository / 'tests/harness/mamp_https_run.py').read_text(encoding='utf-8')
        https_fixture = (repository / 'tests/harness/mamp_https_case.php').read_text(encoding='utf-8')
        tls_proxy = (repository / 'tests/harness/local_tls_proxy.py').read_text(encoding='utf-8')
        self.assertIn("BASE = 'https://localhost:9443/kklidi-members-mamp-sandbox/'", https_runner)
        self.assertIn("'core_cookies_secure'", https_runner)
        self.assertIn("'core_cookies_httponly'", https_runner)
        self.assertIn("'php_session_absent'", https_runner)
        self.assertIn("$sandbox_root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';", https_fixture)
        self.assertIn("'_kklidi_members_https_test_run'", https_fixture)
        self.assertIn("Strict-Transport-Security", tls_proxy)
        self.assertIn("context.minimum_version = ssl.TLSVersion.TLSv1_2", tls_proxy)

    def test_limiter_storage_bypasses_object_cache_and_fails_closed(self):
        repository = Path(__file__).resolve().parents[2]
        limiter = (repository / 'includes/Security/RateLimiter.php').read_text(encoding='utf-8')
        fixture = (repository / 'tests/harness/rate_storage_case.php').read_text(encoding='utf-8')

        self.assertIn('SELECT option_value FROM {$wpdb->options}', limiter)
        self.assertIn('ON DUPLICATE KEY UPDATE option_value=VALUES(option_value)', limiter)
        self.assertNotIn('get_option($option', limiter)
        self.assertNotIn('update_option($option', limiter)
        self.assertIn("$wpdb->options = $wpdb->prefix . 'missing_limiter_storage';", fixture)
        self.assertIn("'storage_failure_denied'", fixture)
        self.assertIn("'cache_adapter_unavailable_allowed'", fixture)

    def test_deployment_manifest_requires_real_owners_backup_and_bounded_rollback(self):
        repository = Path(__file__).resolve().parents[2]
        example = json.loads((repository / 'tests/harness/deployment_manifest.example.json')
                             .read_text(encoding='utf-8'))
        self.assertEqual(inspect_deployment_manifest(example)['status'], 'BLOCKED')

        ready = json.loads(json.dumps(example))
        ready['environment']['base_url'] = 'https://staging.kklidi.com'
        ready['versions'].update(
            wordpress='7.1', php='8.3', members='0.7.17', woocommerce='11.1.0')
        ready['owners'] = {key: 'approved-' + key for key in ready['owners']}
        ready['backup'].update(
            artifact_sha256='a' * 64,
            created_at_utc='2026-09-08T00:00:00Z',
            restore_tested=True,
            restore_test_evidence='staging-restore-run-001',
        )
        report = inspect_deployment_manifest(ready)
        self.assertEqual(report['status'], 'READY')
        self.assertEqual(report['failed'], [])

        wrong_release = json.loads(json.dumps(ready))
        wrong_release['versions']['members'] = '0.7.4'
        self.assertIn('current_members_version',
                      inspect_deployment_manifest(wrong_release)['failed'])

        unsupported_runtime = json.loads(json.dumps(ready))
        unsupported_runtime['versions']['php'] = '8.2'
        self.assertIn('supported_runtime',
                      inspect_deployment_manifest(unsupported_runtime)['failed'])

        ready['database_password'] = 'must-never-be-accepted'
        report = inspect_deployment_manifest(ready)
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertIn('no_credentials', report['failed'])


if __name__ == '__main__':
    unittest.main()
