<?php
/** Fixed-sandbox synthetic identity for login enumeration timing measurement. */
if (PHP_SAPI !== 'cli') { exit(1); }
$root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';
$fixture_action = $argv[1] ?? '';
$token = $argv[2] ?? '';
if (str_replace('\\', '/', (string) realpath($root)) !== $root
	|| !in_array($fixture_action, array('setup', 'cleanup'), true)
	|| !preg_match('/^[a-f0-9]{12}$/', $token)) { exit('Invalid timing fixture command.'); }
require $root . '/wp-load.php';
if (untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox') { exit('Wrong site.'); }
global $wpdb;
$login = 'timing_' . $token;
$email = $login . '@example.invalid';
$key = '_kklidi_members_timing_case_' . $token;
if ($fixture_action === 'setup') {
	$password = getenv('KKLIDI_TIMING_PASSWORD');
	if (get_option($key, false) !== false || !is_string($password) || strlen($password) < 20) { exit('Fixture unavailable.'); }
	$user_id = wp_insert_user(array('user_login' => $login, 'user_email' => $email, 'user_pass' => $password,
		'display_name' => 'Synthetic timing identity', 'role' => 'subscriber'));
	if (is_wp_error($user_id) || !add_option($key, array('user_id' => (int) $user_id), '', false)) { exit('Fixture setup failed.'); }
	echo wp_json_encode(array('existing' => $email, 'missing' => 'missing_' . $token . '@example.invalid'));
	exit;
}
$state = get_option($key, false);
if (is_array($state) && !empty($state['user_id'])) {
	require_once ABSPATH . 'wp-admin/includes/user.php';
	wp_delete_user((int) $state['user_id']);
}
$wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '\\_kklidi\\_members\\_rate\\_%'");
delete_option($key);
echo wp_json_encode(array('cleaned' => !email_exists($email), 'run_token' => $token));
