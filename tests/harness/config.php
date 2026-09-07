<?php
// Test-only wp-config template. Copied into a fresh, owned temporary installation.
$h_root = realpath(getenv('KKH_ROOT') ?: '');
$h_run = getenv('KKH_RUN');
if (!$h_root || realpath(__DIR__) !== $h_root || !preg_match('/^[a-f0-9]{32}$/D', $h_run ?: '')
    || @file_get_contents(dirname($h_root) . '/owner') !== $h_run
    || !str_starts_with(basename(dirname($h_root)), 'kklidi-members-harness-')) {
    http_response_code(403);
    exit('Harness isolation guard rejected configuration.');
}
$h_db = getenv('KKH_DB');
$h_port = (int) getenv('KKH_DB_PORT');
$h_http = (int) getenv('KKH_HTTP_PORT');
$table_prefix = getenv('KKH_PREFIX');
if ($h_db !== 'kklidi_harness_' . $h_run || $h_port < 20000 || $h_http < 20000
    || !preg_match('/^(wp_|kkh_[a-f0-9]{8}_)$/D', $table_prefix ?: '')) {
    exit('Harness database guard rejected configuration.');
}
define('DB_NAME', $h_db);
define('DB_USER', 'harness');
define('DB_PASSWORD', getenv('KKH_DB_PASSWORD'));
define('DB_HOST', '127.0.0.1:' . $h_port);
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', '');
foreach (['AUTH_KEY', 'SECURE_AUTH_KEY', 'LOGGED_IN_KEY', 'NONCE_KEY',
    'AUTH_SALT', 'SECURE_AUTH_SALT', 'LOGGED_IN_SALT', 'NONCE_SALT'] as $h_key) {
    define($h_key, hash_hmac('sha256', $h_key, getenv('KKH_SALT')));
}
define('WP_HOME', 'http://127.0.0.1:' . $h_http);
define('WP_SITEURL', WP_HOME);
define('WP_ENVIRONMENT_TYPE', 'local');
define('DISABLE_WP_CRON', true);
define('AUTOMATIC_UPDATER_DISABLED', true);
define('DISALLOW_FILE_MODS', true);
define('WP_HTTP_BLOCK_EXTERNAL', true);
define('WP_DEBUG', true);
define('WP_DEBUG_DISPLAY', false);
define('WP_DEBUG_LOG', false);
if (!defined('ABSPATH')) { define('ABSPATH', __DIR__ . '/'); }
require_once ABSPATH . 'wp-settings.php';
