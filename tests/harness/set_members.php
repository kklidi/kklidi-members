<?php
// Toggle only Members in the owned fixture for paired performance measurement.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) { exit('Invalid root.'); }
require $root . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
$action = $argv[1] ?? '';
if ($action === 'on') {
    $result = activate_plugin('kklidi-members/kklidi-members.php');
    if (is_wp_error($result)) { exit('Activation failed.'); }
} elseif ($action === 'off') {
    deactivate_plugins('kklidi-members/kklidi-members.php', true, false);
} else {
    exit('Invalid action.');
}
echo wp_json_encode(array('active' => is_plugin_active('kklidi-members/kklidi-members.php')));
