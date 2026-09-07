<?php

namespace KKLIDI\Members\Security;

if (!defined('ABSPATH')) {
	exit;
}

final class AccountState {
	private const META_KEY = '_kklidi_members_account_state';
	private const BLOCKED = array('registration_pending', 'withdrawal_pending', 'disabled');

	public static function boot(): void {
		add_filter('authenticate', array(__CLASS__, 'authenticate'), 90, 3);
		add_action('init', array(__CLASS__, 'enforce_current_user'), 1);
	}

	public static function get(int $user_id): string {
		$state = (string) get_user_meta($user_id, self::META_KEY, true);
		return in_array($state, array('active', 'registration_pending', 'withdrawal_pending', 'disabled'), true)
			? $state
			: 'active';
	}

	public static function is_blocked(int $user_id): bool {
		return in_array(self::get($user_id), self::BLOCKED, true);
	}

	public static function authenticate($user, string $username, string $password) {
		if (!($user instanceof \WP_User) || !self::is_blocked((int) $user->ID)) {
			return $user;
		}

		return new \WP_Error(
			'kklidi_members_account_unavailable',
			__('Please check your login details.', 'kklidi-members')
		);
	}

	public static function transition(int $user_id, string $from, string $to): bool {
		if (!in_array($from, array('active', 'registration_pending', 'withdrawal_pending'), true)
			|| !in_array($to, array('active', 'withdrawal_pending', 'disabled'), true)) {
			return false;
		}

		$current = (string) get_user_meta($user_id, self::META_KEY, true);
		if ($current === '' && $from === 'active') {
			return add_user_meta($user_id, self::META_KEY, $to, true) !== false;
		}
		if ($current !== $from) {
			return false;
		}

		return update_user_meta($user_id, self::META_KEY, $to, $from) !== false
			&& self::get($user_id) === $to;
	}

	public static function set_registration_pending(int $user_id): bool {
		return update_user_meta($user_id, self::META_KEY, 'registration_pending') !== false;
	}

	public static function revoke_access(int $user_id): void {
		\WP_Session_Tokens::get_instance($user_id)->destroy_all();
		if (class_exists('WP_Application_Passwords')) {
			\WP_Application_Passwords::delete_all_application_passwords($user_id);
		}
		clean_user_cache($user_id);
	}

	public static function enforce_current_user(): void {
		if (PHP_SAPI === 'cli' || !is_user_logged_in()) {
			return;
		}
		$user_id = get_current_user_id();
		if (!self::is_blocked($user_id)) {
			return;
		}

		wp_clear_auth_cookie();
		wp_set_current_user(0);
		if (wp_doing_ajax() || (defined('REST_REQUEST') && REST_REQUEST)) {
			wp_send_json_error(array('message' => __('This account is not available.', 'kklidi-members')), 403);
		}
	}
}
