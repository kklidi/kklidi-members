<?php
// New process after Members deactivation proves Core/domain fallback has no hard dependency.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) { exit('Invalid root.'); }
require $root . '/wp-load.php';
global $wpdb;
$tables = array(
    'woo' => $wpdb->prefix . 'kkh_woo_orders',
    'lms' => $wpdb->prefix . 'kkh_lms_enrollments',
    'kboard' => $wpdb->prefix . 'kkh_kboard_content',
);
$fingerprints = array();
$user_ids = array();
foreach ($tables as $domain => $table) {
    $rows = $wpdb->get_results("SELECT * FROM {$table} ORDER BY id", ARRAY_A);
    $fingerprints[$domain] = hash('sha256', wp_json_encode($rows));
    $user_ids[$domain] = array_map('intval', wp_list_pluck($rows, 'user_id'));
}
echo wp_json_encode(array(
    'members_helper_exists' => function_exists('kklidi_members_login_url'),
    'core_fallback_is_wp_login' => str_contains(wp_login_url('/synthetic'), 'wp-login.php'),
    'fingerprints' => $fingerprints, 'user_ids' => $user_ids,
));
