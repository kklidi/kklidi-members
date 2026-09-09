<?php
// PHP development server only: expose exactly the Core front controller and login entry point.
if (PHP_SAPI !== 'cli-server' || ($_SERVER['REMOTE_ADDR'] ?? '') !== '127.0.0.1'
    || ($_SERVER['HTTP_HOST'] ?? '') !== '127.0.0.1:' . getenv('KKH_HTTP_PORT')) {
    http_response_code(403);
    exit;
}
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if (!in_array($path, ['/', '/wp-login.php', '/index.php', '/wp-admin/tools.php', '/wp-admin/users.php'], true)) {
    http_response_code(404);
    exit;
}
require getenv('KKH_ROOT') . ($path === '/' ? '/index.php' : $path);
