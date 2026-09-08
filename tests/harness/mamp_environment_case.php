<?php
/** Read-only fixed-sandbox proxy/cache capability probe. */
if (PHP_SAPI !== 'cli') { exit(1); }
$root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';
if (str_replace('\\', '/', (string) realpath($root)) !== $root) { exit(1); }
require $root . '/wp-load.php';
if (untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox') { exit(1); }
$_SERVER['REMOTE_ADDR'] = '203.0.113.41';
$_SERVER['HTTP_X_FORWARDED_FOR'] = '198.51.100.1';
$first = \KKLIDI\Members\Security\RateLimiter::network();
$_SERVER['HTTP_X_FORWARDED_FOR'] = '192.0.2.99, 198.51.100.2';
$second = \KKLIDI\Members\Security\RateLimiter::network();
echo wp_json_encode(array(
	'forwarded_header_ignored' => hash_equals($first, $second),
	'external_object_cache' => (bool) wp_using_ext_object_cache(),
	'transport' => parse_url(home_url('/'), PHP_URL_SCHEME),
	'multisite' => is_multisite(),
));
