<?php

namespace KKLIDI\Members\Auth;

if (!defined('ABSPATH')) {
	exit;
}

final class PasswordResetController {
	private const REQUEST_ACTION = 'kklidi_members_password_reset_request';
	private const COMPLETE_ACTION = 'kklidi_members_password_reset_complete';

	public static function handle(): void {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Security/GuestCsrf.php';
		require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';
		self::send_private_headers();

		$redirect_to = kklidi_members_safe_redirect_url(self::value('redirect_to'), home_url('/'));
		$key = self::value('key');
		$login = self::value('login');
		$mode = ($key !== '' || $login !== '') ? 'reset' : 'request';
		$message = '';
		$message_type = 'error';
		$field_errors = array();
		$identifier = self::value('user_login');
		$reset_user = null;

		if (strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
			if (self::value('reset_action') === 'complete') {
				$mode = 'reset';
				$result = self::complete($key, $login);
				if ($result === true) {
					$login_url = add_query_arg('password_reset', '1', kklidi_members_login_url($redirect_to));
					wp_safe_redirect($login_url);
					exit;
				}
				$message = $result->get_error_message();
				$data = $result->get_error_data();
				$field_errors = is_array($data) && isset($data['fields']) && is_array($data['fields'])
					? $data['fields'] : array();
			} else {
				$mode = 'request';
				$result = self::request($identifier, $redirect_to);
				if (is_wp_error($result)
					&& in_array('kklidi_members_rate_limited', $result->get_error_codes(), true)) {
					status_header(429);
					$message = __('There have been too many password reset requests. Please try again later.', 'kklidi-members');
				} elseif (is_wp_error($result) && $result->get_error_code() === 'invalid_request') {
					$message = $result->get_error_message();
				} else {
					$message = __('If an account matches that information, WordPress will send a password reset link.', 'kklidi-members');
					$message_type = 'success';
					$identifier = '';
				}
			}
		}

		if ($mode === 'reset') {
			$reset_user = self::validated_user($key, $login);
			if (is_wp_error($reset_user)) {
				$mode = 'invalid';
				$message = __('This password reset link is invalid or has expired. Request a new link.', 'kklidi-members');
			}
		}

		$request_fields = \KKLIDI\Members\Security\GuestCsrf::fields(self::REQUEST_ACTION);
		$complete_fields = \KKLIDI\Members\Security\GuestCsrf::fields(self::COMPLETE_ACTION);
		$action_url = kklidi_members_password_reset_url($redirect_to);
		$login_url = kklidi_members_login_url($redirect_to);
		require KKLIDI_MEMBERS_DIR . 'templates/password-reset.php';
		exit;
	}

	private static function request(string $identifier, string $redirect_to) {
		$nonce = self::value('_kklidi_members_password_reset_nonce');
		if ($nonce === '' || !wp_verify_nonce($nonce, self::REQUEST_ACTION)
			|| !\KKLIDI\Members\Security\GuestCsrf::verify(self::REQUEST_ACTION)) {
			return new \WP_Error('invalid_request', __('We could not verify this request. Please reload the page and try again.', 'kklidi-members'));
		}

		$filter = static function (array $email, string $key, string $user_login) use ($redirect_to): array {
			$url = \KKLIDI\Members\Core\Url::passwordResetForKey($key, $user_login, $redirect_to);
			$email['message'] = __('Someone requested a password reset for your account.', 'kklidi-members')
				. "\n\n" . sprintf(__('Reset your password: %s', 'kklidi-members'), $url)
				. "\n\n" . __('If this was not you, you can ignore this message.', 'kklidi-members');
			return $email;
		};
		add_filter('retrieve_password_notification_email', $filter, 10, 3);
		try {
			return retrieve_password($identifier);
		} finally {
			remove_filter('retrieve_password_notification_email', $filter, 10);
		}
	}

	private static function complete(string $key, string $login) {
		$nonce = self::value('_kklidi_members_password_reset_complete_nonce');
		if ($nonce === '' || !wp_verify_nonce($nonce, self::COMPLETE_ACTION)
			|| !\KKLIDI\Members\Security\GuestCsrf::verify(self::COMPLETE_ACTION)) {
			return new \WP_Error('invalid_request', __('We could not verify this request. Please reload the page and try again.', 'kklidi-members'));
		}
		$user = self::validated_user($key, $login);
		if (is_wp_error($user)) {
			return new \WP_Error('invalid_key', __('This password reset link is invalid or has expired. Request a new link.', 'kklidi-members'));
		}
		$password = self::raw('new_password');
		$confirmation = self::raw('new_password_confirm');
		if ($password !== $confirmation || strlen($password) < 12 || strlen($password) > 1024) {
			return new \WP_Error(
				'invalid_password',
				__('The new password must be at least 12 characters and match the confirmation.', 'kklidi-members'),
				array('fields' => array('new_password', 'new_password_confirm'))
			);
		}

		reset_password($user, $password);
		return true;
	}

	private static function validated_user(string $key, string $login) {
		if ($key === '' || $login === '') {
			return new \WP_Error('invalid_key');
		}
		return check_password_reset_key($key, $login);
	}

	private static function value(string $key): string {
		$source = isset($_POST[$key]) ? $_POST[$key] : ($_GET[$key] ?? '');
		return is_string($source) ? sanitize_text_field(wp_unslash($source)) : '';
	}

	private static function raw(string $key): string {
		return isset($_POST[$key]) && is_string($_POST[$key]) ? wp_unslash($_POST[$key]) : '';
	}

	private static function send_private_headers(): void {
		nocache_headers();
		if (!headers_sent()) {
			header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
			header('Pragma: no-cache');
			header('Referrer-Policy: no-referrer');
		}
	}
}
