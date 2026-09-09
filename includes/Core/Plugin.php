<?php

namespace KKLIDI\Members\Core;

if (!defined('ABSPATH')) {
	exit;
}

final class Plugin {
	private const ROUTES = array(
		'kklidi_members_login'      => array('includes/Auth/LoginController.php', '\\KKLIDI\\Members\\Auth\\LoginController'),
		'kklidi_members_logout'     => array('includes/Auth/LogoutController.php', '\\KKLIDI\\Members\\Auth\\LogoutController'),
		'kklidi_members_register'   => array('includes/Registration/RegistrationController.php', '\\KKLIDI\\Members\\Registration\\RegistrationController'),
		'kklidi_members_account'    => array('includes/Frontend/AccountController.php', '\\KKLIDI\\Members\\Frontend\\AccountController'),
		'kklidi_members_profile'    => array('includes/Profile/ProfileController.php', '\\KKLIDI\\Members\\Profile\\ProfileController'),
		'kklidi_members_password'   => array('includes/Auth/PasswordController.php', '\\KKLIDI\\Members\\Auth\\PasswordController'),
		'kklidi_members_consent'    => array('includes/Consent/ConsentController.php', '\\KKLIDI\\Members\\Consent\\ConsentController'),
		'kklidi_members_withdrawal' => array('includes/Withdrawal/WithdrawalController.php', '\\KKLIDI\\Members\\Withdrawal\\WithdrawalController'),
	);

	public static function boot(): void {
		self::load_textdomain();
		add_action('init', array(__CLASS__, 'load_textdomain'), 1);

		require_once KKLIDI_MEMBERS_DIR . 'includes/Security/AccountState.php';
		require_once KKLIDI_MEMBERS_DIR . 'includes/Security/RateLimiter.php';
		require_once KKLIDI_MEMBERS_DIR . 'includes/Audit/Recorder.php';

		\KKLIDI\Members\Security\AccountState::boot();
		\KKLIDI\Members\Security\RateLimiter::boot();
		\KKLIDI\Members\Audit\Recorder::boot();

		add_action('template_redirect', array(__CLASS__, 'maybe_handle_login'), 0);
		add_action('wp_enqueue_scripts', array(__CLASS__, 'enqueue_frontend_assets'));
		add_filter('login_url', array(__CLASS__, 'filter_login_url'), 10, 3);
		add_filter('register_url', array(__CLASS__, 'filter_register_url'));
		add_action('kklidi_members_daily_cleanup', array(__CLASS__, 'run_cleanup'));

		if (is_admin()) {
			require_once KKLIDI_MEMBERS_DIR . 'includes/Admin/AdminController.php';
			\KKLIDI\Members\Admin\AdminController::boot();
		}
	}

	/**
	 * Load plugin translations without changing WordPress Core authentication.
	 */
	public static function load_textdomain(): void {
		load_plugin_textdomain(
			'kklidi-members',
			false,
			dirname(plugin_basename(KKLIDI_MEMBERS_FILE)) . '/languages'
		);
	}

	public static function maybe_handle_login(): void {
		if (is_admin()) {
			return;
		}

		self::maybe_redirect_lms_profile();

		foreach (self::ROUTES as $route => $handler) {
			if (!isset($_GET[$route]) && !isset($_POST[$route])) {
				continue;
			}

			require_once KKLIDI_MEMBERS_DIR . $handler[0];
			call_user_func(array($handler[1], 'handle'));
			return;
		}
	}

	/**
	 * Delegate the LMS classroom profile tab without loading or querying LMS
	 * domain objects. When either plugin is unavailable, the LMS keeps its own
	 * profile fallback.
	 */
	private static function maybe_redirect_lms_profile(): void {
		$tab = isset($_GET['kklidi_lms_classroom_tab']) && is_string($_GET['kklidi_lms_classroom_tab'])
			? sanitize_key(wp_unslash($_GET['kklidi_lms_classroom_tab']))
			: '';
		if ($tab !== 'profile' || !is_user_logged_in() || !is_singular('page')
			|| !shortcode_exists('kklidi_lms_my_classroom')) {
			return;
		}

		$page = get_queried_object();
		if (!$page instanceof \WP_Post
			|| !has_shortcode((string) $page->post_content, 'kklidi_lms_my_classroom')) {
			return;
		}

		require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';
		wp_safe_redirect(Url::profile());
		exit;
	}

	/**
	 * Load the Members stylesheet only for a Members-owned frontend route.
	 */
	public static function enqueue_frontend_assets(): void {
		if (!self::is_frontend_route()) {
			return;
		}

		wp_enqueue_style(
			'kklidi-members-frontend',
			plugins_url('assets/css/members.css', KKLIDI_MEMBERS_FILE),
			array(),
			KKLIDI_MEMBERS_VERSION
		);

		if (self::is_auth_route()) {
			wp_enqueue_script(
				'kklidi-members-auth',
				plugins_url('assets/js/members-auth.js', KKLIDI_MEMBERS_FILE),
				array(),
				KKLIDI_MEMBERS_VERSION,
				true
			);
		}
	}

	private static function is_auth_route(): bool {
		return isset($_GET['kklidi_members_login']) || isset($_POST['kklidi_members_login'])
			|| isset($_GET['kklidi_members_register']) || isset($_POST['kklidi_members_register']);
	}

	private static function is_frontend_route(): bool {
		foreach (self::ROUTES as $route => $handler) {
			if (isset($_GET[$route]) || isset($_POST[$route])) {
				return true;
			}
		}

		return false;
	}

	public static function filter_login_url(string $url, string $redirect, bool $force_reauth): string {
		if ($force_reauth || get_option('kklidi_members_own_login_url', '0') !== '1') {
			return $url;
		}

		require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';
		return Url::login($redirect);
	}

	public static function filter_register_url(string $url): string {
		if (get_option('kklidi_members_own_register_url', '0') !== '1') {
			return $url;
		}

		require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';
		return Url::register();
	}

	public static function run_cleanup(): void {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Audit/Recorder.php';
		require_once KKLIDI_MEMBERS_DIR . 'includes/Security/RateLimiter.php';
		\KKLIDI\Members\Audit\Recorder::cleanup();
		\KKLIDI\Members\Security\RateLimiter::cleanup();
	}

	public static function routeKeys(): array {
		return self::ROUTES;
	}
}
