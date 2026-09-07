<?php
// CLI-only, value-redacted state fingerprint for activation and domain-write checks.
if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit;
}
require getenv('KKH_ROOT') . '/wp-load.php';

function kkh_digest_rows(array $rows): string {
    $encoded = [];
    foreach ($rows as $row) {
        ksort($row);
        $encoded[] = wp_json_encode($row);
    }
    sort($encoded, SORT_STRING);
    return hash('sha256', implode("\n", $encoded));
}

global $wpdb;
$like = $wpdb->esc_like($wpdb->prefix) . '%';
$tables = $wpdb->get_col($wpdb->prepare('SHOW TABLES LIKE %s', $like));
sort($tables, SORT_STRING);

$domain_tables = [];
foreach ($tables as $table) {
    if (in_array($table, [$wpdb->users, $wpdb->usermeta, $wpdb->options], true)) {
        continue;
    }
    if (str_starts_with($table, $wpdb->prefix . 'kklidi_mem_')) {
        continue;
    }
    $safe_table = str_replace('`', '``', $table);
    $domain_tables[$table] = kkh_digest_rows($wpdb->get_results("SELECT * FROM `{$safe_table}`", ARRAY_A));
}

$users = $wpdb->get_results(
    "SELECT ID, user_login, user_nicename, user_email, display_name, user_status FROM {$wpdb->users}",
    ARRAY_A
);
$role_rows = $wpdb->get_results($wpdb->prepare(
    "SELECT user_id, meta_key, meta_value FROM {$wpdb->usermeta} WHERE meta_key = %s",
    $wpdb->prefix . 'capabilities'
), ARRAY_A);
$meta_rows = $wpdb->get_results(
    "SELECT user_id, meta_key, meta_value FROM {$wpdb->usermeta}",
    ARRAY_A
);
$meta_by_key = [];
foreach ($meta_rows as $row) {
    $key = $row['meta_key'];
    $meta_by_key[$key][] = $row;
}
$meta_key_hashes = [];
foreach ($meta_by_key as $key => $rows) {
    $meta_key_hashes[$key] = kkh_digest_rows($rows);
}
ksort($meta_key_hashes, SORT_STRING);

$custom_prefix = $wpdb->prefix . 'kklidi_mem_';
$custom_tables = array_values(array_filter($tables, function ($table) use ($custom_prefix) {
    return str_starts_with($table, $custom_prefix);
}));

echo wp_json_encode([
    'users_count' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->users}"),
    'users_fingerprint' => kkh_digest_rows($users),
    'roles_fingerprint' => kkh_digest_rows($role_rows),
    'usermeta_fingerprint' => kkh_digest_rows($meta_rows),
    'usermeta_key_hashes' => $meta_key_hashes,
    'domain_fingerprint' => hash('sha256', wp_json_encode($domain_tables)),
    'tables' => $tables,
    'custom_tables' => $custom_tables,
    'plugin_option_count' => (int) $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name LIKE %s",
        $wpdb->esc_like('kklidi_members_') . '%'
    )),
    'plugins' => get_option('active_plugins'),
]);
