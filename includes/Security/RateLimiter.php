<?php

namespace KKLIDI\Members\Security;

if (!defined('ABSPATH')) {
	exit;
}

final class RateLimiter {
	private static $login_reservations = array();

	public static function boot(): void {
		// Core resolves credentials first. We then count both success and failure while
		// leaving account-state (90) and device-limit (100+) able to add stricter denial.
		add_filter('authenticate', array(__CLASS__, 'reserve_login'), 80, 3);
		add_action('wp_login', array(__CLASS__, 'release_success'), 1, 2);
		add_filter('lostpassword_errors', array(__CLASS__, 'limit_password_reset'), 10, 2);
	}

	public static function limit_password_reset($errors, $user_data) {
		if (!($errors instanceof \WP_Error)) {
			return $errors;
		}
		$subject = isset($_POST['user_login']) && is_string($_POST['user_login'])
			? strtolower(wp_unslash($_POST['user_login'])) : '';
		foreach (array(
			array('reset_subject', self::digest($subject), 5, HOUR_IN_SECONDS),
			array('reset_network', self::network(), 20, HOUR_IN_SECONDS),
		) as $check) {
			$result = self::increment($check[0], $check[1], $check[2], $check[3]);
			if (is_wp_error($result) || !$result['allowed']) {
				$errors->add('kklidi_members_rate_limited', __('We could not process this request. Please try again later.', 'kklidi-members'));
				break;
			}
		}
		return $errors;
	}

	public static function reserve_login($user, string $username, string $password) {
		if ($username === '' || $password === '') {
			return $user;
		}
		$checks = array(
			array('login_subject', self::digest(strtolower($username)), 10, 15 * MINUTE_IN_SECONDS),
			array('login_network', self::network(), 50, 15 * MINUTE_IN_SECONDS),
			array('login_global', 'global', 200, 15 * MINUTE_IN_SECONDS),
		);
		foreach ($checks as $check) {
			$result = self::increment($check[0], $check[1], $check[2], $check[3]);
			if (is_wp_error($result)) {
				return $result;
			}
			self::$login_reservations[] = $result['option'];
			if (!$result['allowed']) {
				return new \WP_Error('kklidi_members_rate_limited', __('Please try again later.', 'kklidi-members'), array(
					'retry_after' => $result['retry_after'],
				));
			}
		}
		return $user;
	}

	public static function release_success(string $login, \WP_User $user): void {
		foreach (array_unique(self::$login_reservations) as $option) {
			self::decrement($option);
		}
		self::$login_reservations = array();
	}

	public static function consume(string $purpose, string $subject, int $limit, int $window) {
		return self::increment($purpose, $subject, $limit, $window);
	}

	public static function network(): string {
		$ip = isset($_SERVER['REMOTE_ADDR']) && is_string($_SERVER['REMOTE_ADDR'])
			? trim(wp_unslash($_SERVER['REMOTE_ADDR'])) : '';
		$packed = @inet_pton($ip);
		if ($packed === false) {
			return 'unknown';
		}
		if (strlen($packed) === 4) {
			$packed[3] = "\0";
		} else {
			$packed = substr($packed, 0, 8) . str_repeat("\0", 8);
		}
		return bin2hex($packed);
	}

	public static function cleanup(): void {
		global $wpdb;
		$like = $wpdb->esc_like('_kklidi_members_rate_') . '%';
		$rows = $wpdb->get_results($wpdb->prepare(
			"SELECT option_name, option_value FROM {$wpdb->options} WHERE option_name LIKE %s LIMIT 500",
			$like
		));
		foreach ($rows as $row) {
			$data = json_decode($row->option_value, true);
			if (!is_array($data) || (int) ($data['expires'] ?? 0) < time()) {
				delete_option($row->option_name);
			}
		}
	}

	private static function increment(string $purpose, string $subject, int $limit, int $window) {
		global $wpdb;
		$option = '_kklidi_members_rate_' . self::digest($purpose . '|' . $subject);
		$lock = 'kklidi_members_' . substr(self::digest($option), 0, 32);
		$claimed = (int) $wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 2)', $lock));
		if ($claimed !== 1) {
			return new \WP_Error('kklidi_members_limiter_unavailable', __('Please try again later.', 'kklidi-members'));
		}
		try {
			$now = time();
			$data = get_option($option, null);
			$data = is_string($data) ? json_decode($data, true) : $data;
			if (!is_array($data) || (int) ($data['expires'] ?? 0) <= $now) {
				$data = array('count' => 0, 'expires' => $now + $window);
			}
			$data['count'] = min($limit + 1, (int) $data['count'] + 1);
			$stored = update_option($option, wp_json_encode($data), false);
			if (!$stored && get_option($option, '') !== wp_json_encode($data)) {
			return new \WP_Error('kklidi_members_limiter_unavailable', __('Please try again later.', 'kklidi-members'));
			}
			return array(
				'allowed' => $data['count'] <= $limit,
				'retry_after' => max(1, (int) $data['expires'] - $now),
				'option' => $option,
			);
		} finally {
			$wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)', $lock));
		}
	}

	private static function decrement(string $option): void {
		global $wpdb;
		$lock = 'kklidi_members_' . substr(self::digest($option), 0, 32);
		if ((int) $wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 2)', $lock)) !== 1) {
			return;
		}
		try {
			$data = get_option($option, null);
			$data = is_string($data) ? json_decode($data, true) : $data;
			if (is_array($data) && (int) ($data['count'] ?? 0) > 0) {
				$data['count'] = (int) $data['count'] - 1;
				update_option($option, wp_json_encode($data), false);
			}
		} finally {
			$wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)', $lock));
		}
	}

	private static function digest(string $value): string {
		return hash_hmac('sha256', $value, wp_salt('auth'));
	}
}
