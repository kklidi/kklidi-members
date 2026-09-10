<?php
/**
 * Plugin Name: KKLIDI Members
 * Plugin URI: https://kklidi.com/
 * Description: KKLIDI member and account experience on top of WordPress Core Auth.
 * Version: 0.7.23
 * Author: KKLIDI
 * Text Domain: kklidi-members
 * Requires PHP: 8.3
 * Requires at least: 7.1
 */

if (!defined('ABSPATH')) {
	exit;
}

define('KKLIDI_MEMBERS_VERSION', '0.7.23');
define('KKLIDI_MEMBERS_FILE', __FILE__);
define('KKLIDI_MEMBERS_DIR', plugin_dir_path(__FILE__));

require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Plugin.php';

/**
 * Return the Members login URL with an optional local destination.
 */
function kklidi_members_login_url(string $redirect_to = ''): string {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';

	return \KKLIDI\Members\Core\Url::login($redirect_to);
}

function kklidi_members_register_url(string $redirect_to = ''): string {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';

	return \KKLIDI\Members\Core\Url::register($redirect_to);
}

function kklidi_members_account_url(): string {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';

	return \KKLIDI\Members\Core\Url::account();
}

function kklidi_members_profile_url(): string {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';

	return \KKLIDI\Members\Core\Url::profile();
}

function kklidi_members_password_reset_url(string $redirect_to = ''): string {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';

	return \KKLIDI\Members\Core\Url::passwordReset($redirect_to);
}

function kklidi_members_clean_route_preflight(): array {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';

	return \KKLIDI\Members\Core\Url::cleanRoutePreflight();
}

/**
 * Reduce an untrusted redirect candidate to an allowed local URL.
 */
function kklidi_members_safe_redirect_url(string $candidate, string $fallback = ''): string {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';

	return \KKLIDI\Members\Core\Url::local($candidate, $fallback);
}

register_activation_hook(__FILE__, function (): void {
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Installer.php';
	\KKLIDI\Members\Core\Installer::activate();
});

register_deactivation_hook(__FILE__, function (): void {
	wp_clear_scheduled_hook('kklidi_members_daily_cleanup');
	require_once KKLIDI_MEMBERS_DIR . 'includes/Core/RouteMap.php';
	\KKLIDI\Members\Core\RouteMap::deactivate();
});

\KKLIDI\Members\Core\Plugin::boot();
