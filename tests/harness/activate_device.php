<?php
// Activate the copied, pinned device-limit reference only in the owned fixture.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) { exit('Invalid root.'); }
require $root . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
$result = activate_plugin('kklidi-device-limit/kklidi-device-limit.php');
if (is_wp_error($result)) { exit('Device activation failed.'); }
update_option('kklidi_dl_max_devices', 1, false);
update_option('kklidi_dl_cooldown_hours', 0, false);
echo wp_json_encode(array('active' => in_array('kklidi-device-limit/kklidi-device-limit.php',
    get_option('active_plugins', array()), true), 'max' => kklidi_dl_max()));
