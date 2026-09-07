<?php
// CLI fixture builder, never copied into the served document root.
if (PHP_SAPI !== 'cli') { exit(1); }
define('WP_INSTALLING', true);
require getenv('KKH_ROOT') . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/upgrade.php';
if (is_blog_installed()) { exit('Refusing to reuse an installed fixture.'); }
$install = wp_install('Synthetic Members Harness', 'fixture_admin', 'admin@example.invalid', false,
    '', getenv('KKH_USER_PASSWORD'), 'en_US');
if (is_wp_error($install)) { exit('Synthetic installation failed.'); }
foreach ([
    ['email_identity', 'learner-a@example.invalid', 'learner-a@example.invalid', '합성 회원 가'],
    ['separate_username', 'fixture_learner_b', 'learner-b@example.invalid', '합성 회원 나'],
] as [$label, $login, $email, $display]) {
    $id = wp_insert_user(['user_login' => $login, 'user_email' => $email,
        'display_name' => $display, 'user_pass' => getenv('KKH_USER_PASSWORD'), 'role' => 'subscriber']);
    if (is_wp_error($id)) { exit('Synthetic user creation failed.'); }
    $user = get_userdata($id);
    $fixtures[$label] = ['id' => $id, 'login' => $login, 'email' => $email,
        'display_name' => $user->display_name, 'roles' => array_values($user->roles)];
}
update_option('users_can_register', 0);
// Exercise the mail sink deliberately without retaining recipient/body.
if (wp_mail('sink@example.invalid', 'Synthetic sink probe', 'Synthetic content') !== true) {
    exit('Mail sink probe failed.');
}
$blocked = wp_remote_get('https://example.invalid/harness-egress-probe');
if (!is_wp_error($blocked) || $blocked->get_error_code() !== 'harness_egress_blocked') {
    exit('HTTP egress guard failed.');
}
global $wpdb, $wp_version;
echo json_encode(['fixtures' => $fixtures, 'wordpress' => $wp_version, 'php' => PHP_VERSION,
    'prefix' => $wpdb->prefix, 'users_count' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->users}"),
    'plugins' => get_option('active_plugins'), 'mail_sink' => true, 'http_blocked' => true], JSON_UNESCAPED_UNICODE);
