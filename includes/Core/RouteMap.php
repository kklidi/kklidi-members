<?php

namespace KKLIDI\Members\Core;

if (!defined('ABSPATH')) {
	exit;
}

final class RouteMap {
	public const OPTION_NAME = 'kklidi_members_route_map';
	private const SCHEMA_VERSION = 1;
	private const ROUTES = array(
		'login'          => array('path' => 'members/login', 'query' => 'kklidi_members_login'),
		'register'       => array('path' => 'members/register', 'query' => 'kklidi_members_register'),
		'account'        => array('path' => 'members/account', 'query' => 'kklidi_members_account'),
		'profile'        => array('path' => 'members/account/profile', 'query' => 'kklidi_members_profile'),
		'password'       => array('path' => 'members/account/password', 'query' => 'kklidi_members_password'),
		'password_reset' => array('path' => 'members/password-reset', 'query' => 'kklidi_members_password_reset'),
		'consent'        => array('path' => 'members/account/consent', 'query' => 'kklidi_members_consent'),
		'withdrawal'     => array('path' => 'members/account/withdrawal', 'query' => 'kklidi_members_withdrawal'),
		'logout'         => array('path' => 'members/logout', 'query' => 'kklidi_members_logout'),
	);

	public static function defaults(): array {
		return array(
			'version' => self::SCHEMA_VERSION,
			'clean_routes_enabled' => false,
		);
	}

	public static function settings(): array {
		$stored = get_option(self::OPTION_NAME, null);
		if (!is_array($stored)
			|| array_keys($stored) !== array('version', 'clean_routes_enabled')
			|| (int) $stored['version'] !== self::SCHEMA_VERSION
			|| !is_bool($stored['clean_routes_enabled'])) {
			return self::defaults();
		}
		return array(
			'version' => self::SCHEMA_VERSION,
			'clean_routes_enabled' => $stored['clean_routes_enabled'],
		);
	}

	public static function enabled(): bool {
		return self::settings()['clean_routes_enabled'];
	}

	public static function boot(): void {
		add_filter('query_vars', array(__CLASS__, 'query_vars'));
		add_action('init', array(__CLASS__, 'register_rewrite_rules'), 1);
	}

	public static function install(): void {
		add_option(self::OPTION_NAME, self::defaults(), '', 'no');
		if (!self::refresh_rewrite_rules()) {
			update_option(self::OPTION_NAME, self::defaults(), false);
			self::remove_registered_rules();
			flush_rewrite_rules(false);
		}
	}

	public static function deactivate(): void {
		self::remove_registered_rules();
		flush_rewrite_rules(false);
	}

	public static function query_vars(array $vars): array {
		if (!self::enabled()) {
			return $vars;
		}
		foreach (self::ROUTES as $route) {
			$vars[] = $route['query'];
		}
		return array_values(array_unique($vars));
	}

	public static function register_rewrite_rules(): void {
		if (!self::enabled()) {
			return;
		}
		foreach (self::rewrite_rule_map() as $regex => $query) {
			add_rewrite_rule($regex, $query, 'top');
		}
	}

	public static function request_has(string $query_key): bool {
		if (isset($_GET[$query_key]) || isset($_POST[$query_key])) {
			return true;
		}
		return self::enabled() && (string) get_query_var($query_key, '') === '1';
	}

	public static function url_for_query(string $query_key): string {
		if (self::enabled()) {
			foreach (self::ROUTES as $route) {
				if ($route['query'] === $query_key) {
					return home_url('/' . $route['path'] . '/');
				}
			}
		}
		return add_query_arg($query_key, '1', home_url('/'));
	}

	public static function preflight(): array {
		$collisions = array();
		if ((string) get_option('permalink_structure', '') === '') {
			$collisions[] = self::collision('/members/', 0, 'plain', 'permalink_structure');
		}

		if (function_exists('get_page_by_path')) {
			$paths = array('members');
			foreach (self::ROUTES as $route) {
				$paths[] = $route['path'];
			}
			foreach (array_unique($paths) as $path) {
				$page = get_page_by_path($path, OBJECT, 'page');
				if ($page instanceof \WP_Post) {
					$collisions[] = self::collision(
						'/' . trim($path, '/') . '/',
						(int) $page->ID,
						(string) $page->post_status,
						'wordpress_page'
					);
				}
			}
		}

		$stored_rules = get_option('rewrite_rules', array());
		if (is_array($stored_rules)) {
			$expected = self::rewrite_rule_map();
			foreach ($stored_rules as $regex => $query) {
				if (!is_string($regex) || !is_string($query)
					|| strpos(ltrim($regex, '^'), 'members') !== 0
					|| (isset($expected[$regex]) && $expected[$regex] === $query)) {
					continue;
				}
				foreach (self::ROUTES as $route) {
					if (self::regex_matches_path($regex, $route['path'])) {
						$collisions[] = self::collision(
							'/' . $route['path'] . '/', 0, 'registered', 'rewrite_rule'
						);
					}
				}
			}
		}

		global $wp_rewrite;
		if ($wp_rewrite instanceof \WP_Rewrite && is_array($wp_rewrite->endpoints)) {
			foreach ($wp_rewrite->endpoints as $endpoint) {
				if (is_array($endpoint) && isset($endpoint[1]) && $endpoint[1] === 'members') {
					$collisions[] = self::collision('/members/', 0, 'registered', 'reserved_endpoint');
				}
			}
		}

		$unique = array();
		foreach ($collisions as $collision) {
			$key = implode('|', array($collision['path'], $collision['page_id'],
				$collision['status'], $collision['owner_type']));
			$unique[$key] = $collision;
		}
		$collisions = array_values($unique);

		return array(
			'base' => '/members/',
			'paths' => self::paths(),
			'ready' => $collisions === array(),
			'collisions' => $collisions,
			'query_fallback' => true,
			'clean_routes_enabled' => self::enabled(),
		);
	}

	/**
	 * Change the clean-route state from the capability/nonce-protected admin flow.
	 *
	 * @return true|\WP_Error
	 */
	public static function transition(bool $enabled) {
		if (!current_user_can('manage_kklidi_members')) {
			return new \WP_Error('forbidden', __('You do not have permission to manage member routes.', 'kklidi-members'));
		}

		$previous_raw = get_option(self::OPTION_NAME, null);
		$previous = self::settings()['clean_routes_enabled'];
		if ($previous === $enabled) {
			return true;
		}
		if ($enabled) {
			$preflight = self::preflight();
			if (!$preflight['ready']) {
				return new \WP_Error('route_collision', __('Clean routes cannot be enabled until all route conflicts are resolved.', 'kklidi-members'));
			}
		}

		$next = array('version' => self::SCHEMA_VERSION, 'clean_routes_enabled' => $enabled);
		if (!update_option(self::OPTION_NAME, $next, false)) {
			return new \WP_Error('route_save_failed', __('The clean route setting could not be saved.', 'kklidi-members'));
		}

		self::remove_registered_rules();
		if ($enabled) {
			self::register_rewrite_rules();
		}
		flush_rewrite_rules(false);
		if (!self::verify_persisted_rules($enabled)) {
			self::restore_option($previous_raw);
			self::remove_registered_rules();
			if ($previous) {
				self::register_rewrite_rules();
			}
			flush_rewrite_rules(false);
			return new \WP_Error('route_flush_failed', __('WordPress could not persist the member route rules.', 'kklidi-members'));
		}

		require_once KKLIDI_MEMBERS_DIR . 'includes/Audit/Recorder.php';
		\KKLIDI\Members\Audit\Recorder::record(
			'route_settings_update',
			'success',
			$enabled ? 'clean_routes_enabled' : 'clean_routes_disabled',
			get_current_user_id(),
			'',
			wp_generate_uuid4()
		);
		return true;
	}

	private static function refresh_rewrite_rules(): bool {
		self::remove_registered_rules();
		if (self::enabled()) {
			self::register_rewrite_rules();
		}
		flush_rewrite_rules(false);
		return self::verify_persisted_rules(self::enabled());
	}

	private static function verify_persisted_rules(bool $enabled): bool {
		$rules = get_option('rewrite_rules', array());
		if (!is_array($rules)) {
			return false;
		}
		foreach (self::rewrite_rule_map() as $regex => $query) {
			if ($enabled && (!isset($rules[$regex]) || $rules[$regex] !== $query)) {
				return false;
			}
			if (!$enabled && isset($rules[$regex])) {
				return false;
			}
		}
		return true;
	}

	private static function remove_registered_rules(): void {
		global $wp_rewrite;
		if (!$wp_rewrite instanceof \WP_Rewrite) {
			return;
		}
		foreach (array_keys(self::rewrite_rule_map()) as $regex) {
			unset($wp_rewrite->extra_rules_top[$regex], $wp_rewrite->extra_rules[$regex]);
		}
	}

	private static function restore_option($previous_raw): void {
		if ($previous_raw === null) {
			delete_option(self::OPTION_NAME);
			return;
		}
		update_option(self::OPTION_NAME, $previous_raw, false);
	}

	private static function rewrite_rule_map(): array {
		$rules = array();
		foreach (self::ROUTES as $route) {
			$rules['^' . $route['path'] . '/?$'] = 'index.php?' . $route['query'] . '=1';
		}
		return $rules;
	}

	private static function paths(): array {
		$paths = array();
		foreach (self::ROUTES as $name => $route) {
			$paths[$name] = $route['path'];
		}
		return $paths;
	}

	private static function collision(string $path, int $page_id, string $status,
		string $owner_type): array {
		return array(
			'path' => $path,
			'page_id' => $page_id,
			'status' => $status,
			'owner_type' => $owner_type,
		);
	}

	private static function regex_matches_path(string $regex, string $path): bool {
		$delimiter_safe = str_replace('#', '\\#', $regex);
		return @preg_match('#' . $delimiter_safe . '#', $path) === 1;
	}
}
