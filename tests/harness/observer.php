<?php
// Test-only MU observer. Does not authenticate users, set cookies, or replace login.
if (!defined('ABSPATH') || realpath(ABSPATH) !== realpath(getenv('KKH_ROOT') ?: '')
    || @file_get_contents(dirname(ABSPATH) . '/owner') !== getenv('KKH_RUN')
    || !str_starts_with(basename(dirname(ABSPATH)), 'kklidi-members-harness-')) {
    http_response_code(403);
    exit('Harness observer is not enabled here.');
}
function kkh_record(array $event): void {
    $file = getenv('KKH_EVENTS');
    if (dirname($file) !== dirname(rtrim(ABSPATH, '/\\'))) { exit('Invalid event sink.'); }
    if (file_put_contents($file, json_encode($event) . "\n", FILE_APPEND | LOCK_EX) === false) {
        exit('Event sink failed.');
    }
}
add_filter('pre_wp_mail', function ($return, $attributes) {
    kkh_record(['type' => 'mail_sunk']);
    $mailbox = getenv('KKH_MAILBOX');
    if ($mailbox && dirname($mailbox) === dirname(rtrim(ABSPATH, '/\\')) && is_array($attributes)) {
        file_put_contents($mailbox, wp_json_encode(array(
            'subject' => (string) ($attributes['subject'] ?? ''),
            'message' => (string) ($attributes['message'] ?? ''),
        )) . "\n", FILE_APPEND | LOCK_EX);
    }
    return true;
}, 10, 2);
add_filter('pre_http_request', function () {
    kkh_record(['type' => 'http_blocked']);
    return new WP_Error('harness_egress_blocked', 'Network disabled inside synthetic WordPress.');
}, PHP_INT_MAX);
add_action('wp_login', function ($login, $user) {
    kkh_record(['type' => 'wp_login', 'user_id' => $user->ID]);
}, PHP_INT_MAX, 2);
add_action('init', function () {
    if (PHP_SAPI === 'cli' || !isset($_GET['kkh_observe'])) { return; }
    if (!hash_equals(getenv('KKH_PROBE_KEY'), $_SERVER['HTTP_X_KKH_PROBE'] ?? '')
        || ($_SERVER['REMOTE_ADDR'] ?? '') !== '127.0.0.1') {
        status_header(403);
        exit;
    }
    global $wpdb;
    $user = wp_get_current_user();
    $plugin_root = trailingslashit(wp_normalize_path(WP_PLUGIN_DIR . '/kklidi-members'));
    $members_files = [];
    foreach (get_included_files() as $included_file) {
        $included_file = wp_normalize_path($included_file);
        if (str_starts_with($included_file, $plugin_root)) {
            $members_files[] = substr($included_file, strlen($plugin_root));
        }
    }
    sort($members_files);
    $kklidi_cookies = array_values(array_filter(array_keys($_COOKIE), function ($name) {
        return str_starts_with(strtolower($name), 'kklidi');
    }));
    sort($kklidi_cookies);
    nocache_headers();
    $consent_count = 0;
    $audit_count = 0;
    if (is_user_logged_in()) {
        $consent_table = $wpdb->prefix . 'kklidi_mem_consents';
        $audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
        if ($wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s', $consent_table)) === $consent_table) {
            $consent_count = (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$consent_table} WHERE user_id = %d", $user->ID));
        }
        if ($wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s', $audit_table)) === $audit_table) {
            $audit_count = (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$audit_table} WHERE user_id = %d", $user->ID));
        }
    }
    wp_send_json(['user_id' => get_current_user_id(), 'logged_in' => is_user_logged_in(),
        'roles' => array_values($user->roles), 'can_read' => current_user_can('read'),
        'can_manage_options' => current_user_can('manage_options'),
        'display_name' => $user->display_name, 'first_name' => $user->first_name,
        'last_name' => $user->last_name, 'description' => $user->description,
        'email' => $user->user_email, 'login' => $user->user_login,
        'billing_phone' => is_user_logged_in() ? (string) get_user_meta($user->ID, 'billing_phone', true) : '',
        'account_state' => is_user_logged_in() ? (string) get_user_meta($user->ID, '_kklidi_members_account_state', true) : '',
        'consent_count' => $consent_count, 'audit_count' => $audit_count, 'prefix' => $wpdb->prefix,
        'users_count' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->users}"),
        'plugins' => get_option('active_plugins'), 'members_files' => $members_files,
        'kklidi_cookies' => $kklidi_cookies,
        'php_session_active' => session_status() === PHP_SESSION_ACTIVE,
        'query_count' => get_num_queries(), 'memory_peak_bytes' => memory_get_peak_usage(true),
        'run_id' => getenv('KKH_RUN')]);
}, PHP_INT_MAX);
