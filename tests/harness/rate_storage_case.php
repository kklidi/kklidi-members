<?php
// Verify the limiter stays independent from the WordPress object-cache adapter.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || realpath(dirname($root)) !== realpath(dirname(getenv('KKH_DATA')))
	|| @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) {
	exit(1);
}
require $root . '/wp-load.php';

use KKLIDI\Members\Security\RateLimiter;

global $wpdb, $wp_object_cache;
wp_salt('auth');
$original_cache = $wp_object_cache;
$wp_object_cache = new class {
	public function __call($name, $arguments) {
		throw new RuntimeException('Object cache access is unavailable.');
	}
};
try {
	$cache_result = RateLimiter::consume('cache_outage_fixture', 'same_subject', 1, 900);
} finally {
	$wp_object_cache = $original_cache;
}

$original_options = $wpdb->options;
$wpdb->options = $wpdb->prefix . 'missing_limiter_storage';
$previous_suppression = $wpdb->suppress_errors(true);
try {
	$failure_result = RateLimiter::consume('storage_failure_fixture', 'same_subject', 1, 900);
} finally {
	$wpdb->options = $original_options;
	$wpdb->suppress_errors($previous_suppression);
}

$option = '_kklidi_members_rate_' . hash_hmac(
	'sha256',
	'cache_outage_fixture|same_subject',
	wp_salt('auth')
);
$wpdb->delete($wpdb->options, array('option_name' => $option), array('%s'));

echo wp_json_encode(array(
	'cache_adapter_unavailable_allowed' => !is_wp_error($cache_result) && $cache_result['allowed'],
	'storage_failure_denied' => is_wp_error($failure_result)
		&& $failure_result->get_error_code() === 'kklidi_members_limiter_unavailable',
	'cleanup_rows' => (int) $wpdb->get_var($wpdb->prepare(
		"SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name=%s",
		$option
	)),
));
