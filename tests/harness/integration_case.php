<?php
// Synthetic domain ownership fixture: no production order/LMS/community data is touched.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) { exit('Invalid root.'); }
require $root . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
global $wpdb;
$user = get_user_by('email', 'learner-b@example.invalid');
if (!$user) { exit('Fixture identity missing.'); }
$tables = array(
    'woo' => $wpdb->prefix . 'kkh_woo_orders',
    'lms' => $wpdb->prefix . 'kkh_lms_enrollments',
    'kboard' => $wpdb->prefix . 'kkh_kboard_content',
);
foreach ($tables as $table) {
    $wpdb->query("CREATE TABLE {$table} (id bigint unsigned NOT NULL, user_id bigint unsigned NOT NULL, payload varchar(40) NOT NULL, PRIMARY KEY (id))");
    $wpdb->insert($table, array('id' => 1, 'user_id' => $user->ID, 'payload' => 'synthetic-owned-domain'));
}
$fingerprints = array();
foreach ($tables as $domain => $table) {
    $fingerprints[$domain] = hash('sha256', wp_json_encode($wpdb->get_results("SELECT * FROM {$table} ORDER BY id", ARRAY_A)));
}
$destinations = array(
    'woo' => home_url('/checkout/?cart=synthetic'),
    'lms' => home_url('/classroom/?tab=courses'),
    'kboard' => home_url('/board/?mod=list'),
);
$urls = array();
foreach ($destinations as $domain => $destination) {
    $urls[$domain] = kklidi_members_login_url($destination);
}
deactivate_plugins('kklidi-members/kklidi-members.php', true, false);
echo wp_json_encode(array('user_id' => (int) $user->ID, 'fingerprints' => $fingerprints,
    'destinations' => $destinations, 'login_urls' => $urls,
    'members_active_after' => is_plugin_active('kklidi-members/kklidi-members.php')));
