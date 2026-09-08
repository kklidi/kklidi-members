<?php
/** Synthetic user fixture for the fixed MAMP HTTPS harness. */
if (PHP_SAPI !== 'cli') { exit(1); }
$sandbox_root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';
if (str_replace('\\', '/', (string) realpath($sandbox_root)) !== $sandbox_root) { exit(1); }
require $sandbox_root . '/wp-load.php';
if (untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox') { exit(1); }
require_once ABSPATH . 'wp-admin/includes/plugin.php';
require_once ABSPATH . 'wp-admin/includes/user.php';

$fixture_action = $argv[1] ?? '';
$run_token = $argv[2] ?? '';
if (!in_array($fixture_action, array('setup', 'cleanup'), true)
	|| !preg_match('/^[a-f0-9]{12}$/', $run_token)) {
	exit(1);
}
$state_option = '_kklidi_members_https_test_state';
global $wpdb;

if ($fixture_action === 'setup') {
	if (get_option($state_option, false) !== false
		|| !is_plugin_active('kklidi-members/kklidi-members.php')) {
		exit(1);
	}
	$password = getenv('KKLIDI_HTTPS_PASSWORD');
	if (!is_string($password) || strlen($password) < 24) { exit(1); }
	$email = 'https-' . $run_token . '@example.invalid';
	$tracked_options = array('kklidi_members_own_login_url', 'kklidi_members_own_register_url');
	$option_state = array();
	foreach ($tracked_options as $name) {
		$exists = get_option($name, null);
		$option_state[$name] = array('exists' => $exists !== null, 'value' => $exists);
	}
	$rate_rows = $wpdb->get_results($wpdb->prepare(
		"SELECT option_name, option_value, autoload FROM {$wpdb->options} WHERE option_name LIKE %s",
		$wpdb->esc_like('_kklidi_members_rate_') . '%'
	), ARRAY_A);
	$active_plugins = get_option('active_plugins', array());
	$user_id = wp_insert_user(array(
		'user_login' => $email,
		'user_email' => $email,
		'user_pass' => $password,
		'display_name' => 'HTTPS Synthetic Member',
		'role' => 'subscriber',
	));
	if (is_wp_error($user_id)) { exit(1); }
	update_user_meta($user_id, '_kklidi_members_https_test_run', $run_token);
	update_option('kklidi_members_own_login_url', '1', false);
	update_option($state_option, array(
		'run' => $run_token,
		'user_id' => (int) $user_id,
		'options' => $option_state,
		'rate_rows' => $rate_rows,
		'active_plugins' => $active_plugins,
	), false);
	update_option('active_plugins', array_values(array_diff($active_plugins, array(
		'kboard/index.php',
		'kboard-comments/index.php',
	))), false);
	echo wp_json_encode(array('user_id' => (int) $user_id, 'email' => $email));
	exit;
}

$state = get_option($state_option, array());
if (!is_array($state) || ($state['run'] ?? '') !== $run_token) { exit(1); }
$user_id = (int) ($state['user_id'] ?? 0);
$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
$wpdb->delete($audit_table, array('user_id' => $user_id), array('%d'));
if (defined('KKLIDI_DL_TABLE')) {
	$device_table = $wpdb->prefix . KKLIDI_DL_TABLE;
	if ($wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s', $device_table)) === $device_table) {
		$wpdb->delete($device_table, array('user_id' => $user_id), array('%d'));
	}
}
if ($user_id > 0 && get_user_meta($user_id, '_kklidi_members_https_test_run', true) === $run_token) {
	wp_delete_user($user_id);
}
foreach (($state['options'] ?? array()) as $name => $snapshot) {
	if (!empty($snapshot['exists'])) {
		update_option($name, $snapshot['value'], false);
	} else {
		delete_option($name);
	}
}
$wpdb->query($wpdb->prepare(
	"DELETE FROM {$wpdb->options} WHERE option_name LIKE %s",
	$wpdb->esc_like('_kklidi_members_rate_') . '%'
));
foreach (($state['rate_rows'] ?? array()) as $row) {
	$wpdb->replace($wpdb->options, $row, array('%s', '%s', '%s'));
}
if (isset($state['active_plugins']) && is_array($state['active_plugins'])) {
	update_option('active_plugins', $state['active_plugins'], false);
}
delete_option($state_option);
echo wp_json_encode(array(
	'user_remaining' => get_user_by('id', $user_id) ? 1 : 0,
	'audit_remaining' => (int) $wpdb->get_var($wpdb->prepare(
		"SELECT COUNT(*) FROM {$audit_table} WHERE user_id=%d",
		$user_id
	)),
	'state_remaining' => get_option($state_option, false) !== false,
	'plugins_restored' => get_option('active_plugins', array()) === ($state['active_plugins'] ?? array()),
));
