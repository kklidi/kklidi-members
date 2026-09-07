<?php
// Separate PHP workers share only the disposable harness database.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || realpath(dirname($root)) !== realpath(dirname(getenv('KKH_DATA')))
    || @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) {
    exit(1);
}
require $root . '/wp-load.php';
$result = \KKLIDI\Members\Security\RateLimiter::consume('parallel_fixture', 'same_subject', 10, 900);
echo wp_json_encode(array('allowed' => !is_wp_error($result) && $result['allowed'],
    'error' => is_wp_error($result)));
