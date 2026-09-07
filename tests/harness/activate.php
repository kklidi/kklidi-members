<?php
// CLI-only activation of the production plugin inside the owned synthetic site.
if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit;
}
require getenv('KKH_ROOT') . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';

$result = activate_plugin('kklidi-members/kklidi-members.php');
if (is_wp_error($result)) {
    fwrite(STDERR, $result->get_error_code());
    exit(1);
}

echo wp_json_encode([
    'plugins' => get_option('active_plugins'),
    'login_helper_exists' => function_exists('kklidi_members_login_url'),
    'login_url' => kklidi_members_login_url('/synthetic-destination'),
]);
