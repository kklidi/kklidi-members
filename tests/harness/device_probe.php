<?php
// Query/delete synthetic device records through the actual copied plugin API.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) { exit('Invalid root.'); }
require $root . '/wp-load.php';
global $wpdb;
$email = $argv[2] ?? '';
$user = get_user_by('email', $email);
if (!$user || !function_exists('kklidi_dl_delete_device')) { exit('Device probe unavailable.'); }
$table = $wpdb->prefix . KKLIDI_DL_TABLE;
$log = $wpdb->prefix . KKLIDI_DL_LOG;
$action = $argv[1] ?? 'summary';
$device_id = (int) $wpdb->get_var($wpdb->prepare("SELECT id FROM {$table} WHERE user_id=%d ORDER BY id LIMIT 1", $user->ID));
$deleted = null;
if ($action === 'delete-first' && $device_id) {
    $deleted = kklidi_dl_delete_device((int) $user->ID, $device_id, false, false);
}
echo wp_json_encode(array(
    'user_id' => (int) $user->ID,
    'device_count' => (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$table} WHERE user_id=%d", $user->ID)),
    'block_count' => (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$log} WHERE user_id=%d", $user->ID)),
    'deleted' => $deleted,
));
