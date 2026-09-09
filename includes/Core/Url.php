<?php

namespace KKLIDI\Members\Core;

if (!defined('ABSPATH')) {
	exit;
}

final class Url {
	public static function login(string $redirect_to = ''): string {
		return self::route('kklidi_members_login', $redirect_to);
	}

	public static function register(string $redirect_to = ''): string {
		return self::route('kklidi_members_register', $redirect_to);
	}

	public static function account(): string {
		return add_query_arg('kklidi_members_account', '1', home_url('/'));
	}

	public static function profile(): string {
		return add_query_arg('kklidi_members_profile', '1', home_url('/'));
	}

	public static function password(): string {
		return add_query_arg('kklidi_members_password', '1', home_url('/'));
	}

	public static function consent(): string {
		return add_query_arg('kklidi_members_consent', '1', home_url('/'));
	}

	public static function withdrawal(): string {
		return add_query_arg('kklidi_members_withdrawal', '1', home_url('/'));
	}

	public static function logout(): string {
		return add_query_arg('kklidi_members_logout', '1', home_url('/'));
	}

	public static function passwordReset(string $redirect_to = ''): string {
		$url = site_url('wp-login.php?action=lostpassword', 'login');
		if ($redirect_to !== '') {
			$url = add_query_arg('redirect_to', self::local($redirect_to), $url);
		}
		return $url;
	}

	/**
	 * Check whether the future /members/ route family can be activated safely.
	 * Existing query routes remain authoritative until this preflight is clear.
	 */
	public static function cleanRoutePreflight(): array {
		$paths = array(
			'login' => 'members/login',
			'register' => 'members/register',
			'account' => 'members/account',
			'profile' => 'members/account/profile',
			'password' => 'members/account/password',
			'consent' => 'members/account/consent',
			'withdrawal' => 'members/account/withdrawal',
			'logout' => 'members/logout',
		);
		$collisions = array();
		if (function_exists('get_page_by_path')) {
			foreach ($paths as $route => $path) {
				$page = get_page_by_path($path, OBJECT, 'page');
				if ($page instanceof \WP_Post) {
					$collisions[$route] = array(
						'path' => $path,
						'page_id' => (int) $page->ID,
						'status' => (string) $page->post_status,
					);
				}
			}
		}

		return array(
			'base' => '/members/',
			'paths' => $paths,
			'ready' => $collisions === array(),
			'collisions' => $collisions,
			'query_fallback' => true,
		);
	}

	private static function route(string $key, string $redirect_to = ''): string {
		$url = add_query_arg($key, '1', home_url('/'));

		if ($redirect_to !== '') {
			$url = add_query_arg('redirect_to', self::local($redirect_to), $url);
		}

		return $url;
	}

	public static function local(string $candidate, string $fallback = ''): string {
		$home = home_url('/');
		$safe_fallback = self::same_origin($fallback) && !self::is_auth_loop($fallback)
			? wp_validate_redirect($fallback, $home) : $home;

		if ($candidate === '' || self::dangerous_encoding($candidate)) {
			return $safe_fallback;
		}

		$validated = wp_validate_redirect(wp_sanitize_redirect($candidate), $safe_fallback);

		return self::same_origin($validated) && !self::is_auth_loop($validated)
			&& !self::has_nested_redirect($validated)
			? $validated
			: $safe_fallback;
	}

	private static function dangerous_encoding(string $candidate): bool {
		$value = $candidate;
		for ($i = 0; $i < 3; $i++) {
			if (preg_match('/[\x00-\x1F\x7F]/', $value) || strpos($value, '\\') !== false
				|| strpos($value, '//') === 0 || preg_match('/^[a-z][a-z0-9+.-]*:/i', $value)) {
				$parts = wp_parse_url($value);
				if ($value !== $candidate || !is_array($parts) || !isset($parts['host']) || !self::same_origin($value)) {
					return true;
				}
			}
			$decoded = rawurldecode($value);
			if ($decoded === $value) {
				break;
			}
			$value = $decoded;
		}
		return false;
	}

	private static function has_nested_redirect(string $url): bool {
		$parts = wp_parse_url($url);
		if (!is_array($parts) || empty($parts['query'])) {
			return false;
		}
		parse_str($parts['query'], $query);
		foreach (array('redirect', 'redirect_to', 'return', 'return_to', 'url') as $key) {
			if (!isset($query[$key]) || !is_string($query[$key])) {
				continue;
			}
			$value = trim($query[$key]);
			if (strpos($value, '//') === 0 || preg_match('/^[a-z][a-z0-9+.-]*:/i', $value)) {
				return true;
			}
		}
		return false;
	}

	private static function same_origin(string $url): bool {
		if ($url === '') {
			return false;
		}

		$parts = wp_parse_url($url);
		if (!is_array($parts)) {
			return false;
		}

		// A validated relative path stays on this WordPress origin.
		if (!isset($parts['host'])) {
			return isset($parts['path']) && strpos($parts['path'], '//') !== 0;
		}

		$home = wp_parse_url(home_url('/'));
		if (!is_array($home) || !isset($home['host'])) {
			return false;
		}

		return strtolower($parts['host']) === strtolower($home['host'])
			&& strtolower($parts['scheme'] ?? '') === strtolower($home['scheme'] ?? '')
			&& self::port($parts) === self::port($home)
			&& !isset($parts['user'])
			&& !isset($parts['pass']);
	}

	private static function port(array $parts): int {
		if (isset($parts['port'])) {
			return (int) $parts['port'];
		}

		return strtolower($parts['scheme'] ?? '') === 'https' ? 443 : 80;
	}

	private static function is_auth_loop(string $url): bool {
		$parts = wp_parse_url($url);
		if (!is_array($parts)) {
			return true;
		}

		parse_str($parts['query'] ?? '', $query);
		foreach (array('kklidi_members_login', 'kklidi_members_register',
			'kklidi_members_logout', 'kklidi_members_password') as $route) {
			if (isset($query[$route])) {
				return true;
			}
		}

		return false;
	}
}
