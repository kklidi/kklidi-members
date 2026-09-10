<?php
/**
 * CLI-only AUTH-MAIL-SENDER-001 fixture for the dedicated MAMP sandbox.
 *
 * The pre_wp_mail sink proves the WordPress mail API accepted the request and
 * captures the resulting Members-owned headers/body without contacting a real
 * recipient. It can target only the synthetic local MAMP site.
 */

if (PHP_SAPI !== 'cli') {
	exit(1);
}

$sandbox_root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';
$resolved_root = realpath($sandbox_root);
if ($resolved_root === false
	|| str_replace('\\', '/', $resolved_root) !== $sandbox_root
	|| !is_file($resolved_root . '/wp-load.php')) {
	exit('The dedicated MAMP sandbox is unavailable.');
}

$fixture_action = $argv[1] ?? '';
$run_token = $argv[2] ?? '';
if (!in_array($fixture_action, array('setup', 'probe', 'cleanup'), true)
	|| !preg_match('/^[a-f0-9]{12}$/', $run_token)) {
	exit('Invalid AUTH-MAIL-SENDER-001 fixture command.');
}

define('WP_USE_THEMES', false);
require $resolved_root . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
require_once ABSPATH . 'wp-admin/includes/user.php';
if (untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox') {
	exit('Refusing a non-sandbox WordPress site.');
}
if (!defined('KKLIDI_MEMBERS_VERSION') || KKLIDI_MEMBERS_VERSION !== '0.7.31'
	|| !is_plugin_active('kklidi-members/kklidi-members.php')) {
	exit('The expected Members candidate is not active.');
}

require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/MailSenderSettings.php';
require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AccountMailer.php';

global $wpdb;
$state_key = '_kklidi_members_mail_sender_case_' . $run_token;
$option_name = \KKLIDI\Members\Notifications\MailSenderSettings::OPTION_NAME;
$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
$login_prefix = 'mail_sender_case_' . $run_token;

$option_snapshot = static function (string $name): array {
	$missing = new stdClass();
	$value = get_option($name, $missing);
	return array(
		'exists' => $value !== $missing,
		'value' => $value !== $missing ? $value : null,
	);
};

if ($fixture_action === 'setup') {
	if (get_option($state_key, false) !== false || username_exists($login_prefix)) {
		exit('Fixture token already exists.');
	}
	$admins = get_users(array('role' => 'administrator', 'number' => 1, 'fields' => array('ID', 'user_email')));
	if (!$admins || !is_email($admins[0]->user_email)) {
		exit('A valid administrator is required.');
	}
	$user_id = wp_insert_user(array(
		'user_login' => $login_prefix,
		'user_email' => $login_prefix . '@example.invalid',
		'user_pass' => wp_generate_password(32, true, true),
		'display_name' => 'MAMP mail sender fixture',
		'role' => 'subscriber',
	));
	if (is_wp_error($user_id)) {
		exit('Synthetic mail sender user creation failed.');
	}
	$state = array(
		'run_token' => $run_token,
		'user_id' => (int) $user_id,
		'admin_id' => (int) $admins[0]->ID,
		'admin_email' => (string) $admins[0]->user_email,
		'option' => $option_snapshot($option_name),
		'audit_max_id' => (int) $wpdb->get_var("SELECT COALESCE(MAX(id), 0) FROM {$audit_table}"),
	);
	add_option($state_key, $state, '', false);
	update_option($option_name, array(
		'version' => 1,
		'sender_enabled' => true,
		'from_name' => 'MAMP Members',
		'from_email' => 'mamp-members@example.invalid',
		'footer_enabled' => true,
		'footer_text' => 'MAMP synthetic sender footer.',
	), false);
	echo wp_json_encode(array('ready' => true, 'user_id' => (int) $user_id));
	exit;
}

$state = get_option($state_key, false);
if (!is_array($state) || empty($state['user_id'])) {
	exit('Fixture state is missing.');
}

if ($fixture_action === 'probe') {
	$captured = array();
	add_filter('pre_wp_mail', static function ($return, $atts) use (&$captured) {
		$captured[] = $atts;
		return true;
	}, PHP_INT_MAX, 2);
	$request_id = wp_generate_uuid4();
	$sent = \KKLIDI\Members\Notifications\AccountMailer::send(
		'registration_completed', (int) $state['user_id'], $request_id
	);
	$attempt = $captured[0] ?? array();
	$headers = $attempt['headers'] ?? array();
	if (!is_array($headers)) {
		$headers = preg_split('/\r?\n/', (string) $headers, -1, PREG_SPLIT_NO_EMPTY);
	}
	$message = (string) ($attempt['message'] ?? '');
	$header_text = implode("\n", array_map('strval', $headers));
	$mail_audit = $wpdb->get_row($wpdb->prepare(
		"SELECT result, reason_code FROM {$audit_table} WHERE user_id = %d
		 AND event_type = %s ORDER BY id DESC LIMIT 1",
		(int) $state['user_id'], 'mail_registration_completed'
	), ARRAY_A);
	$valid = $sent === true
		&& count($captured) === 1
		&& ($attempt['to'] ?? '') === $login_prefix . '@example.invalid'
		&& str_contains($header_text, 'Content-Type: text/plain;')
		&& str_contains($header_text, 'From: MAMP Members <mamp-members@example.invalid>')
		&& str_contains($message, 'MAMP synthetic sender footer.')
		&& is_array($mail_audit)
		&& $mail_audit['result'] === 'success'
		&& $mail_audit['reason_code'] === 'wp_mail_accepted';
	echo wp_json_encode(array(
		'accepted' => $valid,
		'wp_mail_returned_true' => $sent === true,
		'sink_attempts' => count($captured),
		'plain_text' => str_contains($header_text, 'Content-Type: text/plain;'),
		'scoped_from' => str_contains($header_text, 'From: MAMP Members <mamp-members@example.invalid>'),
		'footer_applied' => str_contains($message, 'MAMP synthetic sender footer.'),
		'account_mail_audit' => $mail_audit,
		'external_mailbox_delivery' => false,
	));
	exit($valid ? 0 : 2);
}

$snapshot = $state['option'] ?? array('exists' => false);
if (!empty($snapshot['exists'])) {
	update_option($option_name, $snapshot['value'], false);
} else {
	delete_option($option_name);
}
wp_delete_user((int) $state['user_id']);
$wpdb->query($wpdb->prepare(
	"DELETE FROM {$audit_table} WHERE id > %d AND user_id = %d",
	(int) ($state['audit_max_id'] ?? 0), (int) $state['user_id']
));
$deleted = !get_user_by('id', (int) $state['user_id'])
	&& get_option($option_name, null) === ($snapshot['exists'] ?? false ? $snapshot['value'] : null);
delete_option($state_key);
echo wp_json_encode(array('cleaned' => $deleted, 'run_token' => $run_token));
exit($deleted ? 0 : 3);
