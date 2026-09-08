<?php
/** Fixed-sandbox setup/probe/cleanup for registration and Core reset races. */
if (PHP_SAPI !== 'cli') { exit(1); }
$root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';
$fixture_action = $argv[1] ?? '';
$token = $argv[2] ?? '';
if (str_replace('\\', '/', (string) realpath($root)) !== $root
	|| !in_array($fixture_action, array('setup', 'probe', 'cleanup'), true)
	|| !preg_match('/^[a-f0-9]{12}$/', $token)) { exit('Invalid race fixture command.'); }
require $root . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
if (untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox'
	|| !is_plugin_active('kklidi-members/kklidi-members.php')) { exit('Dedicated Members sandbox unavailable.'); }
add_filter('pre_wp_mail', '__return_true');
global $wpdb;
$key = '_kklidi_members_race_case_' . $token;
$registration_email = 'race_' . $token . '@example.invalid';
$reset_login = 'reset_' . $token;
$reset_email = $reset_login . '@example.invalid';
$state = get_option($key, false);
$snapshot = static function (string $name): array {
	$missing = new stdClass();
	$value = get_option($name, $missing);
	return array('exists' => $value !== $missing, 'value' => $value !== $missing ? $value : null);
};
$restore = static function (string $name, array $value): void {
	if (!empty($value['exists'])) { update_option($name, $value['value'], false); }
	else { delete_option($name); }
};

if ($fixture_action === 'setup') {
	if ($state !== false || email_exists($registration_email) || username_exists($reset_login)) { exit('Fixture already exists.'); }
	require_once WP_PLUGIN_DIR . '/kklidi-members/includes/Consent/Documents.php';
	$state = array('options' => array(), 'reset_user' => 0, 'registration_email' => $registration_email,
		'reset_email' => $reset_email, 'document_snapshots' => array());
	foreach (array('users_can_register', 'kklidi_members_own_register_url',
		'kklidi_members_document_service', 'kklidi_members_document_privacy') as $name) {
		$state['options'][$name] = $snapshot($name);
	}
	if (!add_option($key, $state, '', false)) { exit('Fixture state unavailable.'); }
	foreach (array('service', 'privacy') as $type) {
		$document = \KKLIDI\Members\Consent\Documents::save($type, 'race-' . $token,
			'<p>Synthetic ' . $type . ' document ' . $token . '</p>');
		if (is_wp_error($document)) { exit('Synthetic document failed.'); }
		$state['document_snapshots'][] = '_kklidi_members_document_snapshot_' . $type . '_' . $document['hash'];
	}
	update_option('users_can_register', 1, false);
	update_option('kklidi_members_own_register_url', '1', false);
	$password = getenv('KKLIDI_RACE_PASSWORD');
	if (!is_string($password) || strlen($password) < 20) { exit('Synthetic password required.'); }
	$user_id = wp_insert_user(array('user_login' => $reset_login, 'user_email' => $reset_email,
		'user_pass' => $password, 'display_name' => 'Synthetic reset race', 'role' => 'subscriber'));
	if (is_wp_error($user_id)) { exit('Synthetic reset user failed.'); }
	$state['reset_user'] = (int) $user_id;
	update_option($key, $state, false);
	$reset_key = get_password_reset_key(get_user_by('id', $user_id));
	if (is_wp_error($reset_key)) { exit('Core reset key failed.'); }
	echo wp_json_encode(array('registration_email' => $registration_email, 'reset_login' => $reset_login,
		'reset_key' => $reset_key, 'register_url' => kklidi_members_register_url(),
		'reset_url' => site_url('wp-login.php?action=rp', 'login')));
	exit;
}

if (!is_array($state)) { exit('Fixture state missing.'); }
if ($fixture_action === 'probe') {
	$registered = get_user_by('email', $registration_email);
	$reset_user = get_user_by('email', $reset_email);
	$candidates = json_decode((string) getenv('KKLIDI_RESET_CANDIDATES'), true);
	$matches = 0;
	if ($reset_user && is_array($candidates)) {
		foreach ($candidates as $candidate) {
			if (is_string($candidate) && wp_check_password($candidate, $reset_user->user_pass, $reset_user->ID)) { $matches++; }
		}
	}
	$consent_table = $wpdb->prefix . 'kklidi_mem_consents';
	echo wp_json_encode(array(
		'registration_users' => (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$wpdb->users} WHERE user_email=%s", $registration_email)),
		'registration_user_id' => $registered ? (int) $registered->ID : 0,
		'registration_state' => $registered ? (string) get_user_meta($registered->ID, '_kklidi_members_account_state', true) : '',
		'registration_roles' => $registered ? array_values($registered->roles) : array(),
		'required_consents' => $registered ? (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$consent_table} WHERE user_id=%d AND consent_type IN ('service','privacy') AND action='accept'", $registered->ID)) : 0,
		'reset_matching_passwords' => $matches,
	));
	exit;
}

$ids = $wpdb->get_col($wpdb->prepare("SELECT ID FROM {$wpdb->users} WHERE user_email IN (%s,%s)", $registration_email, $reset_email));
if ($ids) {
	$in = implode(',', array_map('intval', $ids));
	$wpdb->query("DELETE FROM {$wpdb->prefix}kklidi_mem_consents WHERE user_id IN ({$in})");
	$wpdb->query("DELETE FROM {$wpdb->prefix}kklidi_mem_login_audit WHERE user_id IN ({$in})");
	require_once ABSPATH . 'wp-admin/includes/user.php';
	foreach ($ids as $id) { wp_delete_user((int) $id); }
}
foreach ($state['options'] as $name => $value) { $restore($name, $value); }
foreach ($state['document_snapshots'] as $name) { delete_option($name); }
$wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '\\_kklidi\\_members\\_rate\\_%'");
delete_option($key);
echo wp_json_encode(array('cleaned' => !email_exists($registration_email) && !email_exists($reset_email), 'run_token' => $token));
