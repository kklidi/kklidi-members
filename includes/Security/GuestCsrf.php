<?php

namespace KKLIDI\Members\Security;

if (!defined('ABSPATH')) {
	exit;
}

final class GuestCsrf {
	private const TTL = 1800;

	public static function fields(string $action): string {
		$browser = self::browser_token();
		$expires = time() + self::TTL;
		$token = hash_hmac('sha256', $action . '|' . $browser . '|' . $expires, wp_salt('nonce'));

		return '<input type="hidden" name="_kklidi_members_guest_exp" value="' . esc_attr((string) $expires) . '">'
			. '<input type="hidden" name="_kklidi_members_guest_token" value="' . esc_attr($token) . '">';
	}

	public static function verify(string $action): bool {
		$browser = self::read_cookie();
		$expires = isset($_POST['_kklidi_members_guest_exp']) && is_scalar($_POST['_kklidi_members_guest_exp'])
			? (int) wp_unslash($_POST['_kklidi_members_guest_exp']) : 0;
		$submitted = isset($_POST['_kklidi_members_guest_token']) && is_string($_POST['_kklidi_members_guest_token'])
			? wp_unslash($_POST['_kklidi_members_guest_token']) : '';
		if ($browser === '' || $expires < time() || $expires > time() + self::TTL + 60
			|| !preg_match('/^[a-f0-9]{64}$/', $submitted) || !self::same_origin_headers()) {
			return false;
		}

		$expected = hash_hmac('sha256', $action . '|' . $browser . '|' . $expires, wp_salt('nonce'));
		return hash_equals($expected, $submitted);
	}

	public static function binding_digest(): string {
		$browser = self::read_cookie();
		return $browser === '' ? '' : hash_hmac('sha256', $browser, wp_salt('nonce'));
	}

	private static function browser_token(): string {
		$token = self::read_cookie();
		if ($token !== '') {
			return $token;
		}

		$token = bin2hex(random_bytes(32));
		$name = self::cookie_name();
		$options = array(
			'expires' => time() + self::TTL,
			'path' => '/',
			'samesite' => 'Lax',
			'secure' => is_ssl(),
			'httponly' => true,
		);
		if (!headers_sent()) {
			setcookie($name, $token, $options);
			$_COOKIE[$name] = $token;
		}
		return $token;
	}

	private static function read_cookie(): string {
		$name = self::cookie_name();
		$value = isset($_COOKIE[$name]) && is_string($_COOKIE[$name]) ? wp_unslash($_COOKIE[$name]) : '';
		return preg_match('/^[a-f0-9]{64}$/', $value) ? $value : '';
	}

	private static function cookie_name(): string {
		return is_ssl() ? '__Host-kklidi_members_guest' : 'kklidi_members_guest';
	}

	private static function same_origin_headers(): bool {
		$home = wp_parse_url(home_url('/'));
		foreach (array('HTTP_ORIGIN', 'HTTP_REFERER') as $header) {
			if (empty($_SERVER[$header]) || !is_string($_SERVER[$header])) {
				continue;
			}
			$value = wp_parse_url(wp_unslash($_SERVER[$header]));
			if (!is_array($value) || !is_array($home)
				|| strtolower($value['scheme'] ?? '') !== strtolower($home['scheme'] ?? '')
				|| strtolower($value['host'] ?? '') !== strtolower($home['host'] ?? '')
				|| self::port($value) !== self::port($home)) {
				return false;
			}
		}
		return true;
	}

	private static function port(array $parts): int {
		return isset($parts['port']) ? (int) $parts['port']
			: (strtolower($parts['scheme'] ?? '') === 'https' ? 443 : 80);
	}
}
