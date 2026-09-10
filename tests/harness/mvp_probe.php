<?php
// CLI-only state probe/mutator for the owned synthetic fixture.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || realpath(dirname($root)) !== realpath(dirname(getenv('KKH_DATA')))
    || @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) {
    exit('Invalid harness root.');
}
require $root . '/wp-load.php';
global $wpdb;
$action = $argv[1] ?? 'summary';
$email = getenv('KKH_MVP_EMAIL') ?: '';
$user = $email !== '' ? get_user_by('email', $email) : false;

if ($action === 'set-fixture-state') {
    $target = get_user_by('email', $argv[2] ?? '');
    $state = $argv[3] ?? '';
    if (!$target || !in_array($state, array('active', 'registration_pending', 'withdrawal_pending', 'disabled'), true)) {
        exit('Invalid state mutation.');
    }
    if ($state === 'active') {
        delete_user_meta($target->ID, '_kklidi_members_account_state');
    } else {
        update_user_meta($target->ID, '_kklidi_members_account_state', $state);
    }
    echo json_encode(array('user_id' => (int) $target->ID, 'state' => $state));
    exit;
}
if ($action === 'set-user-locale') {
    if (!$user || !isset($argv[2]) || !in_array($argv[2], array('en_US', 'ko_KR'), true)) {
        exit('Invalid synthetic user locale.');
    }
    update_user_meta($user->ID, 'locale', sanitize_text_field($argv[2]));
    echo wp_json_encode(array('user_id' => (int) $user->ID, 'locale' => get_user_locale($user)));
    exit;
}
if ($action === 'user-state-summary') {
    $target = get_user_by('email', $argv[2] ?? '');
    if (!$target) { exit('Missing synthetic state-summary user.'); }
    $audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
    echo wp_json_encode(array(
        'user_id' => (int) $target->ID,
        'state' => \KKLIDI\Members\Security\AccountState::get((int) $target->ID),
        'session_count' => count(\WP_Session_Tokens::get_instance($target->ID)->get_all()),
        'events' => $wpdb->get_col($wpdb->prepare(
            "SELECT event_type FROM {$audit_table} WHERE user_id = %d ORDER BY id",
            $target->ID
        )),
    ));
    exit;
}
if ($action === 'translation-check') {
    $catalog = WP_PLUGIN_DIR . '/kklidi-members/languages/kklidi-members-ko_KR.mo';
    echo wp_json_encode(array(
        'locale' => get_locale(),
        'determined_locale' => determine_locale(),
        'catalog_exists' => file_exists($catalog),
        'registration_subject' => sprintf(__('[%s] Registration complete', 'kklidi-members'), get_bloginfo('name')),
        'password_changed_notice' => __('Your password was changed. Please sign in again.', 'kklidi-members'),
		'admin_registration_subject' => sprintf(__('[%s] New member registration', 'kklidi-members'), get_bloginfo('name')),
    ));
    exit;
}
if ($action === 'route-summary') {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/RouteMap.php';
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';
	$option_name = \KKLIDI\Members\Core\RouteMap::OPTION_NAME;
	$stored = get_option($option_name, null);
	$autoload = $wpdb->get_var($wpdb->prepare(
		"SELECT autoload FROM {$wpdb->options} WHERE option_name = %s",
		$option_name
	));
	$preflight = \KKLIDI\Members\Core\RouteMap::preflight();
	$rules = get_option('rewrite_rules', array());
	$expected_rules = array(
		'^members/login/?$' => 'index.php?kklidi_members_login=1',
		'^members/register/?$' => 'index.php?kklidi_members_register=1',
		'^members/account/?$' => 'index.php?kklidi_members_account=1',
		'^members/account/profile/?$' => 'index.php?kklidi_members_profile=1',
		'^members/account/password/?$' => 'index.php?kklidi_members_password=1',
		'^members/password-reset/?$' => 'index.php?kklidi_members_password_reset=1',
		'^members/account/consent/?$' => 'index.php?kklidi_members_consent=1',
		'^members/account/withdrawal/?$' => 'index.php?kklidi_members_withdrawal=1',
		'^members/logout/?$' => 'index.php?kklidi_members_logout=1',
	);
	$present_rules = array();
	foreach ($expected_rules as $regex => $query) {
		$present_rules[$regex] = is_array($rules) && isset($rules[$regex]) && $rules[$regex] === $query;
	}
	$page_counts = wp_count_posts('page');
	$menu_counts = wp_count_posts('nav_menu_item');
	$count_posts = static function ($counts): int {
		return is_object($counts) ? array_sum(array_map('intval', get_object_vars($counts))) : 0;
	};
	$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
	echo wp_json_encode(array(
		'autoload' => $autoload,
		'stored' => $stored,
		'effective' => \KKLIDI\Members\Core\RouteMap::settings(),
		'preflight' => $preflight,
		'present_rules' => $present_rules,
		'rewrite_rules_hash' => hash('sha256', maybe_serialize($rules)),
		'page_count' => $count_posts($page_counts),
		'menu_item_count' => $count_posts($menu_counts),
		'helpers' => array(
			'login' => \KKLIDI\Members\Core\Url::login(),
			'register' => \KKLIDI\Members\Core\Url::register(),
			'account' => \KKLIDI\Members\Core\Url::account(),
			'profile' => \KKLIDI\Members\Core\Url::profile(),
			'password' => \KKLIDI\Members\Core\Url::password(),
			'password_reset' => \KKLIDI\Members\Core\Url::passwordReset(),
			'consent' => \KKLIDI\Members\Core\Url::consent(),
			'withdrawal' => \KKLIDI\Members\Core\Url::withdrawal(),
			'logout' => \KKLIDI\Members\Core\Url::logout(),
		),
		'core_urls' => array(
			'login' => wp_login_url(),
			'force_reauth' => wp_login_url('', true),
			'register' => wp_registration_url(),
		),
		'audit_count' => (int) $wpdb->get_var($wpdb->prepare(
			"SELECT COUNT(*) FROM {$audit_table} WHERE event_type = %s",
			'route_settings_update'
		)),
	));
	exit;
}
if ($action === 'set-pretty-permalinks') {
	global $wp_rewrite;
	$wp_rewrite->set_permalink_structure('/%postname%/');
	flush_rewrite_rules(false);
	echo wp_json_encode(array('permalink_structure' => get_option('permalink_structure')));
	exit;
}
if ($action === 'create-route-page-collision') {
	$page = get_page_by_path('members', OBJECT, 'page');
	if (!$page) {
		$page_id = wp_insert_post(array(
			'post_type' => 'page',
			'post_status' => 'publish',
			'post_title' => 'Synthetic Members Collision',
			'post_name' => 'members',
		));
	} else {
		$page_id = $page->ID;
	}
	if (is_wp_error($page_id) || (int) $page_id < 1) { exit('Route page collision setup failed.'); }
	echo wp_json_encode(array('page_id' => (int) $page_id));
	exit;
}
if ($action === 'remove-route-page-collision') {
	$page = get_page_by_path('members', OBJECT, 'page');
	$deleted = $page instanceof WP_Post ? wp_delete_post($page->ID, true) : false;
	flush_rewrite_rules(false);
	echo wp_json_encode(array('deleted' => $deleted instanceof WP_Post, 'remaining' => get_page_by_path('members', OBJECT, 'page') ? 1 : 0));
	exit;
}
if ($action === 'set-route-rewrite-collision') {
	$rules = get_option('rewrite_rules', array());
	$rules = is_array($rules) ? $rules : array();
	$rules = array('^members/(.+)/?$' => 'index.php?pagename=synthetic-conflict') + $rules;
	update_option('rewrite_rules', $rules, false);
	echo wp_json_encode(array('configured' => isset(get_option('rewrite_rules', array())['^members/(.+)/?$'])));
	exit;
}
if ($action === 'remove-route-rewrite-collision') {
	$rules = get_option('rewrite_rules', array());
	$rules = is_array($rules) ? $rules : array();
	unset($rules['^members/(.+)/?$']);
	update_option('rewrite_rules', $rules, false);
	echo wp_json_encode(array('remaining' => isset(get_option('rewrite_rules', array())['^members/(.+)/?$']) ? 1 : 0));
	exit;
}
if ($action === 'corrupt-route-option') {
	update_option('kklidi_members_route_map', array('version' => 1, 'clean_routes_enabled' => '1', 'custom_slug' => 'unsafe'), false);
	echo wp_json_encode(array('stored' => get_option('kklidi_members_route_map')));
	exit;
}
if ($action === 'reset-route-option') {
	update_option('kklidi_members_route_map', \KKLIDI\Members\Core\RouteMap::defaults(), false);
	flush_rewrite_rules(false);
	echo wp_json_encode(array('stored' => get_option('kklidi_members_route_map')));
	exit;
}
if ($action === 'notification-settings-summary') {
    require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/NotificationTemplates.php';
    $option_name = \KKLIDI\Members\Notifications\NotificationTemplates::OPTION_NAME;
    $stored = get_option($option_name, array());
    $autoload = $wpdb->get_var($wpdb->prepare(
        "SELECT autoload FROM {$wpdb->options} WHERE option_name = %s",
        $option_name
    ));
    $audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
    echo wp_json_encode(array(
        'autoload' => $autoload,
        'schema_version' => is_array($stored) ? (int) ($stored['version'] ?? 0) : 0,
        'registration_content' => \KKLIDI\Members\Notifications\NotificationTemplates::content(
            'registration_completed'
        ),
        'settings_audit_count' => (int) $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$audit_table} WHERE event_type = %s",
            'notification_settings_update'
        )),
        'settings_audit_has_subject' => (int) $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$audit_table}
             WHERE event_type = %s AND subject_digest IS NOT NULL",
            'notification_settings_update'
        )) > 0,
    ));
	exit;
}
if ($action === 'registration-fields-summary') {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Registration/RegistrationFields.php';
	$option_name = \KKLIDI\Members\Registration\RegistrationFields::OPTION_NAME;
	$stored = get_option($option_name, array());
	$autoload = $wpdb->get_var($wpdb->prepare(
		"SELECT autoload FROM {$wpdb->options} WHERE option_name = %s",
		$option_name
	));
	$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
	$field_email = getenv('KKH_FIELDS_EMAIL') ?: '';
	$field_user = $field_email !== '' ? get_user_by('email', $field_email) : false;
	$consent_table = $wpdb->prefix . 'kklidi_mem_consents';
	echo wp_json_encode(array(
		'autoload' => $autoload,
		'stored' => $stored,
		'effective' => \KKLIDI\Members\Registration\RegistrationFields::settings(),
		'settings_audit_count' => (int) $wpdb->get_var($wpdb->prepare(
			"SELECT COUNT(*) FROM {$audit_table} WHERE event_type = %s",
			'registration_fields_update'
		)),
		'settings_audit_has_digest' => (int) $wpdb->get_var($wpdb->prepare(
			"SELECT COUNT(*) FROM {$audit_table}
			 WHERE event_type = %s AND subject_digest IS NOT NULL",
			'registration_fields_update'
		)) > 0,
		'field_user' => $field_user ? array(
			'id' => (int) $field_user->ID,
			'roles' => array_values($field_user->roles),
			'first_name' => (string) $field_user->first_name,
			'last_name' => (string) $field_user->last_name,
			'phone' => (string) get_user_meta($field_user->ID, 'billing_phone', true),
			'required_consents' => (int) $wpdb->get_var($wpdb->prepare(
				"SELECT COUNT(*) FROM {$consent_table}
				 WHERE user_id = %d AND consent_type IN ('service', 'privacy') AND action = 'accept'",
				$field_user->ID
			)),
		) : null,
	));
	exit;
}
if ($action === 'cleanup-registration-fields-user') {
	$field_email = getenv('KKH_FIELDS_EMAIL') ?: '';
	$field_user = $field_email !== '' ? get_user_by('email', $field_email) : false;
	if (!$field_user) { exit('Missing synthetic registration-fields user.'); }
	$consent_table = $wpdb->prefix . 'kklidi_mem_consents';
	$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
	$wpdb->delete($consent_table, array('user_id' => $field_user->ID), array('%d'));
	$wpdb->delete($audit_table, array('user_id' => $field_user->ID), array('%d'));
	require_once ABSPATH . 'wp-admin/includes/user.php';
	$deleted = wp_delete_user($field_user->ID);
	echo wp_json_encode(array(
		'deleted' => (bool) $deleted,
		'remaining' => get_user_by('email', $field_email) ? 1 : 0,
	));
	exit;
}
if ($action === 'set-core-admin-email') {
	$admin_email = getenv('KKH_CORE_ADMIN_EMAIL') ?: '';
	if (!is_email($admin_email)) { exit('Invalid synthetic administrator email.'); }
	update_option('admin_email', $admin_email, false);
	echo wp_json_encode(array('admin_email' => get_option('admin_email')));
	exit;
}
if ($action === 'admin-notification-summary') {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AdminNotificationSettings.php';
	$option_name = \KKLIDI\Members\Notifications\AdminNotificationSettings::OPTION_NAME;
	$stored = get_option($option_name, array());
	$autoload = $wpdb->get_var($wpdb->prepare(
		"SELECT autoload FROM {$wpdb->options} WHERE option_name = %s",
		$option_name
	));
	$admin_notice_email = getenv('KKH_ADMIN_NOTICE_EMAIL') ?: '';
	$admin_notice_user = $admin_notice_email !== '' ? get_user_by('email', $admin_notice_email) : false;
	$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
	$consent_table = $wpdb->prefix . 'kklidi_mem_consents';
	echo wp_json_encode(array(
		'autoload' => $autoload,
		'stored' => $stored,
		'effective' => \KKLIDI\Members\Notifications\AdminNotificationSettings::settings(),
		'core_admin_email' => get_option('admin_email'),
		'settings_audit_count' => (int) $wpdb->get_var($wpdb->prepare(
			"SELECT COUNT(*) FROM {$audit_table} WHERE event_type = %s",
			'admin_notification_settings_update'
		)),
		'user' => $admin_notice_user ? array(
			'id' => (int) $admin_notice_user->ID,
			'state' => \KKLIDI\Members\Security\AccountState::get((int) $admin_notice_user->ID),
			'roles' => array_values($admin_notice_user->roles),
			'required_consents' => (int) $wpdb->get_var($wpdb->prepare(
				"SELECT COUNT(*) FROM {$consent_table} WHERE user_id = %d
				 AND consent_type IN ('service','privacy') AND action = 'accept'",
				$admin_notice_user->ID
			)),
			'mail_audit' => $wpdb->get_results($wpdb->prepare(
				"SELECT event_type, result, reason_code FROM {$audit_table}
				 WHERE user_id = %d AND event_type = 'mail_admin_registration' ORDER BY id",
				$admin_notice_user->ID
			), ARRAY_A),
		) : null,
	));
	exit;
}
if ($action === 'replay-admin-registration-notification') {
	$target = get_user_by('email', getenv('KKH_ADMIN_NOTICE_EMAIL') ?: '');
	if (!$target) { exit('Missing synthetic administrator-notice user.'); }
	$request_id = (string) get_user_meta($target->ID, '_kklidi_members_registration_request_id', true);
	require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AdminRegistrationMailer.php';
	echo wp_json_encode(array(
		'sent' => \KKLIDI\Members\Notifications\AdminRegistrationMailer::send(
			(int) $target->ID,
			$request_id
		),
	));
	exit;
}
if ($action === 'admin-notification-invalid-recipient') {
	$target = get_user_by('email', getenv('KKH_ADMIN_NOTICE_EMAIL') ?: '');
	if (!$target) { exit('Missing synthetic administrator-notice user.'); }
	$original = (string) get_option('admin_email', '');
	$request_id = wp_generate_uuid4();
	$wpdb->update($wpdb->options, array('option_value' => 'invalid-address'),
		array('option_name' => 'admin_email'), array('%s'), array('%s'));
	wp_cache_delete('admin_email', 'options');
	wp_cache_delete('alloptions', 'options');
	require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AdminRegistrationMailer.php';
	$sent = \KKLIDI\Members\Notifications\AdminRegistrationMailer::send(
		(int) $target->ID,
		$request_id
	);
	$invalid_audit = $wpdb->get_row($wpdb->prepare(
		"SELECT result, reason_code FROM {$wpdb->prefix}kklidi_mem_login_audit
		 WHERE request_id = %s AND event_type = 'mail_admin_registration'",
		$request_id
	), ARRAY_A);
	$wpdb->update($wpdb->options, array('option_value' => $original),
		array('option_name' => 'admin_email'), array('%s'), array('%s'));
	wp_cache_delete('admin_email', 'options');
	wp_cache_delete('alloptions', 'options');
	echo wp_json_encode(array('sent' => $sent, 'audit' => $invalid_audit,
		'state' => \KKLIDI\Members\Security\AccountState::get((int) $target->ID),
		'admin_email_restored' => get_option('admin_email') === $original));
	exit;
}
if ($action === 'cleanup-admin-notification-user') {
	$target = get_user_by('email', getenv('KKH_ADMIN_NOTICE_EMAIL') ?: '');
	if (!$target) { exit('Missing synthetic administrator-notice user.'); }
	$consent_table = $wpdb->prefix . 'kklidi_mem_consents';
	$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
	$wpdb->delete($consent_table, array('user_id' => $target->ID), array('%d'));
	$wpdb->delete($audit_table, array('user_id' => $target->ID), array('%d'));
	require_once ABSPATH . 'wp-admin/includes/user.php';
	$deleted = wp_delete_user($target->ID);
	echo wp_json_encode(array('deleted' => (bool) $deleted,
		'remaining' => get_user_by('email', getenv('KKH_ADMIN_NOTICE_EMAIL') ?: '') ? 1 : 0));
	exit;
}
if ($action === 'expire-audit') {
    $table = $wpdb->prefix . 'kklidi_mem_login_audit';
    $wpdb->query("UPDATE {$table} SET occurred_at_utc = '2000-01-01 00:00:00'");
    do_action('kklidi_members_daily_cleanup');
}
if ($action === 'replay-registration-notification') {
    if (!$user) { exit('Missing synthetic notification user.'); }
    $request_id = (string) get_user_meta($user->ID, '_kklidi_members_registration_request_id', true);
    require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AccountMailer.php';
    echo wp_json_encode(array(
        'sent' => \KKLIDI\Members\Notifications\AccountMailer::send(
            'registration_completed',
            (int) $user->ID,
            $request_id
        ),
    ));
    exit;
}
if ($action === 'notification-failure-summary') {
    $failure_email = getenv('KKH_FAILURE_EMAIL') ?: '';
    $failure_user = $failure_email !== '' ? get_user_by('email', $failure_email) : false;
    if (!$failure_user) { exit('Missing synthetic mail-failure user.'); }
    $audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
    $mail_audit = $wpdb->get_results($wpdb->prepare(
        "SELECT event_type, result, reason_code FROM {$audit_table}
         WHERE user_id = %d AND event_type LIKE 'mail_%%' ORDER BY id ASC",
        $failure_user->ID
    ), ARRAY_A);
    $consent_table = $wpdb->prefix . 'kklidi_mem_consents';
    echo wp_json_encode(array(
        'user_id' => (int) $failure_user->ID,
        'state' => \KKLIDI\Members\Security\AccountState::get((int) $failure_user->ID),
        'required_consents' => (int) $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$consent_table}
             WHERE user_id = %d AND consent_type IN ('service', 'privacy') AND action = 'accept'",
            $failure_user->ID
        )),
        'original_password_valid' => wp_check_password(
            getenv('KKH_USER_PASSWORD'), $failure_user->user_pass, $failure_user->ID
        ),
        'changed_password_valid' => wp_check_password(
            getenv('KKH_FAILURE_PASSWORD'), $failure_user->user_pass, $failure_user->ID
        ),
        'session_count' => count(\WP_Session_Tokens::get_instance($failure_user->ID)->get_all()),
        'mail_audit' => $mail_audit,
    ));
    exit;
}

$consent_table = $wpdb->prefix . 'kklidi_mem_consents';
$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
$audit_rows = $wpdb->get_results("SELECT event_type, result, reason_code, subject_digest, network_digest FROM {$audit_table} ORDER BY id ASC", ARRAY_A);
$serialized_audit = wp_json_encode($audit_rows);
$summary = array(
    'users_count' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->users}"),
    'consent_rows' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$consent_table}"),
    'audit_rows' => count($audit_rows),
    'audit_events' => array_values(array_map(static fn($row) => $row['event_type'], $audit_rows)),
    'mail_audit' => array_values(array_filter($audit_rows, static function ($row) {
        return str_starts_with($row['event_type'], 'mail_');
    })),
    'audit_contains_raw_email' => $email !== '' && stripos($serialized_audit, $email) !== false,
    'audit_contains_raw_ip' => stripos($serialized_audit, '127.0.0.1') !== false,
    'rate_option_count' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name LIKE '\\_kklidi\\_members\\_rate\\_%'"),
);
if ($user) {
    $summary['user'] = array(
        'id' => (int) $user->ID,
        'login_is_private' => str_starts_with($user->user_login, 'member_'),
        'email_matches' => strtolower($user->user_email) === strtolower($email),
        'roles' => array_values($user->roles),
        'state' => (string) get_user_meta($user->ID, '_kklidi_members_account_state', true),
        'email_state' => (string) get_user_meta($user->ID, '_kklidi_members_email_state', true),
        'phone' => (string) get_user_meta($user->ID, 'billing_phone', true),
        'service_consents' => (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$consent_table} WHERE user_id=%d AND consent_type='service'", $user->ID)),
        'privacy_consents' => (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$consent_table} WHERE user_id=%d AND consent_type='privacy'", $user->ID)),
        'marketing_actions' => $wpdb->get_col($wpdb->prepare("SELECT action FROM {$consent_table} WHERE user_id=%d AND consent_type='marketing' ORDER BY id", $user->ID)),
        'old_password_valid' => wp_check_password(getenv('KKH_USER_PASSWORD'), $user->user_pass, $user->ID),
        'new_password_valid' => wp_check_password(getenv('KKH_NEW_PASSWORD'), $user->user_pass, $user->ID),
    );
}
echo json_encode($summary, JSON_UNESCAPED_UNICODE);
