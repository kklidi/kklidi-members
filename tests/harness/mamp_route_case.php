<?php
// CLI-only route fixture for the fixed Members MAMP sandbox.
$fail = static function (string $reason, int $code = 1): void {
	fwrite(STDERR, $reason);
	exit($code);
};
if (PHP_SAPI !== 'cli') { $fail('not_cli'); }
$sandbox_root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';
if (str_replace('\\', '/', (string) realpath($sandbox_root)) !== $sandbox_root) { $fail('sandbox_path'); }
$fixture_action = $argv[1] ?? '';
$token = $argv[2] ?? '';
$expected_version = $argv[3] ?? '';
if (!preg_match('/^[a-f0-9]{12}$/', $token)
	|| !preg_match('/^\d+\.\d+\.\d+$/', $expected_version)
	|| !in_array($fixture_action, array('setup', 'disable', 'cleanup'), true)) { $fail('arguments'); }

require $sandbox_root . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
if (untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox'
	|| !defined('KKLIDI_MEMBERS_VERSION') || KKLIDI_MEMBERS_VERSION !== $expected_version) {
	$fail('environment:' . untrailingslashit(home_url('/')) . ':'
		. (defined('KKLIDI_MEMBERS_VERSION') ? KKLIDI_MEMBERS_VERSION : 'undefined'));
}

$state_key = '_kklidi_members_route_case_' . $token;
$route_option = 'kklidi_members_route_map';
$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
$state = get_option($state_key, false);

if ($fixture_action === 'setup') {
	if ($state !== false) { $fail('state_exists'); }
	$admin_ids = get_users(array('role' => 'administrator', 'number' => 1, 'fields' => 'ids'));
	if (!$admin_ids) { $fail('admin_missing'); }
	$state = array(
		'admin_id' => (int) $admin_ids[0],
		'route_exists' => get_option($route_option, null) !== null,
		'route_value' => get_option($route_option, null),
		'permalink_structure' => get_option('permalink_structure', ''),
		'rewrite_exists' => get_option('rewrite_rules', null) !== null,
		'rewrite_rules' => get_option('rewrite_rules', null),
		'audit_max_id' => (int) $wpdb->get_var("SELECT COALESCE(MAX(id), 0) FROM {$audit_table}"),
		'page_count' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type='page'"),
		'menu_count' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type='nav_menu_item'"),
	);
	add_option($state_key, $state, '', false);
	global $wp_rewrite;
	$wp_rewrite->set_permalink_structure('/%postname%/');
	// The fixed sandbox starts with plain permalinks. Build its temporary Apache
	// front-controller rule; the Python runner restores the exact .htaccess bytes.
	flush_rewrite_rules(true);
	wp_set_current_user($state['admin_id']);
	$preflight = \KKLIDI\Members\Core\RouteMap::preflight();
	if (!$preflight['ready']) {
		fwrite(STDERR, wp_json_encode(array('preflight' => $preflight)));
		$fail('preflight', 2);
	}
	$result = \KKLIDI\Members\Core\RouteMap::transition(true);
	if (is_wp_error($result)) {
		fwrite(STDERR, wp_json_encode(array('transition_error' => $result->get_error_code())));
		$fail('transition', 3);
	}
	$rules = get_option('rewrite_rules', array());
	echo wp_json_encode(array(
		'version' => KKLIDI_MEMBERS_VERSION,
		'enabled' => \KKLIDI\Members\Core\RouteMap::enabled(),
		'rules' => is_array($rules) ? count(array_filter(array_keys($rules), static function ($key) {
			return strpos(ltrim((string) $key, '^'), 'members') === 0;
		})) : 0,
		'page_count' => $state['page_count'],
		'menu_count' => $state['menu_count'],
	));
	exit;
}

if (!is_array($state)) { $fail('state_missing'); }
if ($fixture_action === 'disable') {
	wp_set_current_user((int) $state['admin_id']);
	$result = \KKLIDI\Members\Core\RouteMap::transition(false);
	if (is_wp_error($result)) { $fail('disable:' . $result->get_error_code(), 2); }
	echo wp_json_encode(array('enabled' => \KKLIDI\Members\Core\RouteMap::enabled()));
	exit;
}

if ($state['route_exists']) {
	update_option($route_option, $state['route_value'], false);
} else {
	delete_option($route_option);
}
update_option('permalink_structure', $state['permalink_structure'], false);
if ($state['rewrite_exists']) {
	update_option('rewrite_rules', $state['rewrite_rules'], false);
} else {
	delete_option('rewrite_rules');
}
$wpdb->query($wpdb->prepare(
	"DELETE FROM {$audit_table} WHERE id > %d AND event_type = %s",
	(int) $state['audit_max_id'],
	'route_settings_update'
));
$page_count = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type='page'");
$menu_count = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type='nav_menu_item'");
delete_option($state_key);
echo wp_json_encode(array(
	'route_restored' => get_option($route_option, null) === ($state['route_exists'] ? $state['route_value'] : null),
	'permalink_restored' => get_option('permalink_structure', '') === $state['permalink_structure'],
	'rewrite_restored' => get_option('rewrite_rules', null) === ($state['rewrite_exists'] ? $state['rewrite_rules'] : null),
	'page_count_unchanged' => $page_count === (int) $state['page_count'],
	'menu_count_unchanged' => $menu_count === (int) $state['menu_count'],
	'audit_remaining' => (int) $wpdb->get_var($wpdb->prepare(
		"SELECT COUNT(*) FROM {$audit_table} WHERE id > %d AND event_type = %s",
		(int) $state['audit_max_id'],
		'route_settings_update'
	)),
));
