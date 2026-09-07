<?php
/**
 * CLI-only AUTH-WOO-001 fixture for the dedicated MAMP sandbox.
 *
 * This is intentionally unable to accept another WordPress root or URL.
 */

if (PHP_SAPI !== 'cli') {
	exit(1);
}

$sandbox_root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';
$resolved_root = realpath($sandbox_root);
if ($resolved_root === false
	|| str_replace('\\', '/', $resolved_root) !== $sandbox_root
	|| !is_file($resolved_root . '/wp-load.php')) {
	exit('The dedicated MAMP sandbox is unavailable.');
}

$fixture_action = $argv[1] ?? '';
$run_token = $argv[2] ?? '';
if (!in_array($fixture_action, array('setup', 'probe', 'members-off', 'members-on', 'cleanup'), true)
	|| !preg_match('/^[a-f0-9]{12}$/', $run_token)) {
	exit('Invalid AUTH-WOO-001 fixture command.');
}

define('WP_USE_THEMES', false);
require $resolved_root . '/wp-load.php';

if (untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox') {
	exit('Refusing a non-sandbox WordPress site.');
}
if (!class_exists('WooCommerce') || !function_exists('wc_create_order')) {
	exit('WooCommerce is not active.');
}
require_once ABSPATH . 'wp-admin/includes/plugin.php';
add_filter('pre_wp_mail', '__return_true');

$state_key = '_kklidi_members_woo_case_' . $run_token;
$login = 'woo_case_' . $run_token;
$email = $login . '@example.invalid';
$sku = 'auth-woo-001-' . $run_token;
$wci_plugin = 'kklidi-woocommerce-integration/kklidi-woocommerce-integration.php';
$members_plugin = 'kklidi-members/kklidi-members.php';

$option_snapshot = static function (string $name): array {
	$missing = new stdClass();
	$value = get_option($name, $missing);
	return array('exists' => $value !== $missing, 'value' => $value !== $missing ? $value : null);
};

$restore_option = static function (string $name, array $snapshot): void {
	if (!empty($snapshot['exists'])) {
		update_option($name, $snapshot['value'], false);
	} else {
		delete_option($name);
	}
};

if ($fixture_action === 'setup') {
	if (get_option($state_key, false) !== false || username_exists($login) || wc_get_product_id_by_sku($sku)) {
		exit('Fixture token already exists.');
	}

	$password = getenv('KKLIDI_WOO_PASSWORD');
	if (!is_string($password) || strlen($password) < 20) {
		exit('A synthetic fixture password is required.');
	}

	$state = array(
		'run_token' => $run_token,
		'user_id' => 0,
		'product_id' => 0,
		'customer_order_id' => 0,
		'guest_order_id' => 0,
		'wci_was_active' => is_plugin_active($wci_plugin),
		'members_was_active' => is_plugin_active($members_plugin),
		'options' => array(
			'kklidi_dl_max_devices' => $option_snapshot('kklidi_dl_max_devices'),
			'woocommerce_enable_guest_checkout' => $option_snapshot('woocommerce_enable_guest_checkout'),
			'woocommerce_enable_signup_and_login_from_checkout' => $option_snapshot('woocommerce_enable_signup_and_login_from_checkout'),
			'woocommerce_enable_myaccount_registration' => $option_snapshot('woocommerce_enable_myaccount_registration'),
			'kklidi_wci_settings' => $option_snapshot('kklidi_wci_settings'),
			'kklidi_members_own_login_url' => $option_snapshot('kklidi_members_own_login_url'),
		),
	);
	add_option($state_key, $state, '', false);

	if (!$state['wci_was_active']) {
		$activated = activate_plugin($wci_plugin);
		if (is_wp_error($activated)) {
			exit('WCI activation failed.');
		}
	}

	update_option('woocommerce_enable_guest_checkout', 'no', false);
	update_option('kklidi_dl_max_devices', 1, false);
	update_option('woocommerce_enable_signup_and_login_from_checkout', 'no', false);
	update_option('woocommerce_enable_myaccount_registration', 'no', false);
	update_option('kklidi_members_own_login_url', '1', false);
	$wci_settings = get_option('kklidi_wci_settings', array());
	$wci_settings = is_array($wci_settings) ? $wci_settings : array();
	$wci_settings['enable_checkout_login_redirect'] = 1;
	update_option('kklidi_wci_settings', $wci_settings, false);

	$user_id = wp_insert_user(array(
		'user_login' => $login,
		'user_email' => $email,
		'user_pass' => $password,
		'display_name' => 'AUTH-WOO-001',
		'role' => 'subscriber',
	));
	if (is_wp_error($user_id)) {
		exit('Synthetic Woo user creation failed.');
	}
	$state['user_id'] = (int) $user_id;
	update_option($state_key, $state, false);

	$product = new WC_Product_Simple();
	$product->set_name('AUTH-WOO-001 ' . $run_token);
	$product->set_status('publish');
	$product->set_catalog_visibility('visible');
	$product->set_sku($sku);
	$product->set_regular_price('1000');
	$product->set_virtual(true);
	$product->set_sold_individually(true);
	$product_id = $product->save();
	if (!$product_id) {
		exit('Synthetic Woo product creation failed.');
	}
	$state['product_id'] = (int) $product_id;
	update_option($state_key, $state, false);

	$customer_order = wc_create_order(array('customer_id' => $user_id, 'created_via' => 'auth-woo-001'));
	if (is_wp_error($customer_order)) {
		exit('Synthetic customer order creation failed.');
	}
	$customer_order->add_product($product, 1);
	$customer_order->set_billing_email($email);
	$customer_order->calculate_totals();
	$customer_order->set_status('completed');
	$customer_order->update_meta_data('_kklidi_members_test_run', $run_token);
	$customer_order->save();
	$state['customer_order_id'] = (int) $customer_order->get_id();
	update_option($state_key, $state, false);

	$guest_order = wc_create_order(array('customer_id' => 0, 'created_via' => 'auth-woo-001'));
	if (is_wp_error($guest_order)) {
		exit('Synthetic guest order creation failed.');
	}
	$guest_order->add_product($product, 1);
	$guest_order->set_billing_email($email);
	$guest_order->calculate_totals();
	$guest_order->set_status('completed');
	$guest_order->update_meta_data('_kklidi_members_test_run', $run_token);
	$guest_order->save();
	$state['guest_order_id'] = (int) $guest_order->get_id();
	update_option($state_key, $state, false);

	echo wp_json_encode(array(
		'run_token' => $run_token,
		'user_id' => $state['user_id'],
		'product_id' => $state['product_id'],
		'customer_order_id' => $state['customer_order_id'],
		'guest_order_id' => $state['guest_order_id'],
		'email' => $email,
		'checkout_url' => wc_get_checkout_url(),
		'myaccount_url' => wc_get_page_permalink('myaccount'),
	), JSON_UNESCAPED_SLASHES);
	exit;
}

$state = get_option($state_key, false);
if (!is_array($state) || ($state['run_token'] ?? '') !== $run_token) {
	exit('Fixture state is unavailable.');
}

if ($fixture_action === 'members-off') {
	deactivate_plugins($members_plugin, true);
	echo wp_json_encode(array('members_active' => is_plugin_active($members_plugin)));
	exit;
}

if ($fixture_action === 'members-on') {
	$activated = activate_plugin($members_plugin);
	if (is_wp_error($activated)) {
		exit('Members activation failed.');
	}
	echo wp_json_encode(array('members_active' => is_plugin_active($members_plugin)));
	exit;
}

if ($fixture_action === 'probe') {
	$user = get_user_by('id', (int) $state['user_id']);
	$customer_order = wc_get_order((int) $state['customer_order_id']);
	$guest_order = wc_get_order((int) $state['guest_order_id']);
	$product = wc_get_product((int) $state['product_id']);
	$account_order_ids = wc_get_orders(array(
		'customer_id' => (int) $state['user_id'],
		'limit' => -1,
		'return' => 'ids',
	));
	echo wp_json_encode(array(
		'user_id' => $user ? (int) $user->ID : 0,
		'user_login' => $user ? $user->user_login : '',
		'user_email' => $user ? $user->user_email : '',
		'product_exists' => $product instanceof WC_Product,
		'customer_order_id' => $customer_order ? (int) $customer_order->get_id() : 0,
		'customer_order_user_id' => $customer_order ? (int) $customer_order->get_user_id() : -1,
		'guest_order_id' => $guest_order ? (int) $guest_order->get_id() : 0,
		'guest_order_user_id' => $guest_order ? (int) $guest_order->get_user_id() : -1,
		'guest_email_matches' => $guest_order && $user
			? strtolower($guest_order->get_billing_email()) === strtolower($user->user_email) : false,
		'account_order_ids' => array_map('intval', $account_order_ids),
		'guest_checkout' => get_option('woocommerce_enable_guest_checkout'),
		'checkout_signup' => get_option('woocommerce_enable_signup_and_login_from_checkout'),
		'myaccount_registration' => get_option('woocommerce_enable_myaccount_registration'),
		'wci_active' => is_plugin_active($wci_plugin),
		'members_active' => is_plugin_active($members_plugin),
	), JSON_UNESCAPED_SLASHES);
	exit;
}

foreach (array('customer_order_id', 'guest_order_id') as $order_key) {
	$order = wc_get_order((int) ($state[$order_key] ?? 0));
	if ($order) {
		$order->delete(true);
	}
}
$product = wc_get_product((int) ($state['product_id'] ?? 0));
if ($product) {
	$product->delete(true);
}
if (!empty($state['user_id'])) {
	global $wpdb;
	foreach (array('KKLIDI_DL_TABLE', 'KKLIDI_DL_LOG') as $constant) {
		if (defined($constant)) {
			$wpdb->delete($wpdb->prefix . constant($constant), array('user_id' => (int) $state['user_id']), array('%d'));
		}
	}
	$wpdb->delete($wpdb->prefix . 'woocommerce_sessions', array('session_key' => (string) $state['user_id']), array('%s'));
	require_once ABSPATH . 'wp-admin/includes/user.php';
	wp_delete_user((int) $state['user_id']);
}
foreach ($state['options'] as $name => $snapshot) {
	$restore_option($name, $snapshot);
}
if (empty($state['wci_was_active']) && is_plugin_active($wci_plugin)) {
	deactivate_plugins($wci_plugin, true);
}
if (!empty($state['members_was_active']) && !is_plugin_active($members_plugin)) {
	$activated = activate_plugin($members_plugin);
	if (is_wp_error($activated)) {
		exit('Members restoration failed.');
	}
}
delete_option($state_key);
echo wp_json_encode(array('cleaned' => true, 'run_token' => $run_token));
