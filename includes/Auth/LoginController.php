<?php

namespace KKLIDI\Members\Auth;

if (!defined('ABSPATH')) {
	exit;
}

final class LoginController {
	private const NONCE_ACTION = 'kklidi_members_login';
	private const NONCE_FIELD = '_kklidi_members_login_nonce';

	public static function handle(): void {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Security/GuestCsrf.php';
		self::send_private_headers();

		$redirect_to = kklidi_members_safe_redirect_url(self::request_value('redirect_to', true), home_url('/'));
		$message = '';
		$notice = '';
		$message_html = '';
		$identifier = '';
		$remember = false;
		$field_errors = array();
		if (self::request_value('registered') === '1') {
			$notice = __('Your account was created. Please sign in with the email address you registered.', 'kklidi-members');
		} elseif (self::request_value('password_changed') === '1') {
			$notice = __('Your password was changed. Please sign in again.', 'kklidi-members');
		} elseif (self::request_value('password_reset') === '1') {
			$notice = __('Your password has been reset. Please log in with your new password.', 'kklidi-members');
		} elseif (self::request_value('withdrawal') === 'requested') {
			$notice = __('Your withdrawal request was submitted. Access is blocked while it is reviewed.', 'kklidi-members');
		}

		if (strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
			$identifier = self::request_value('kklidi_members_identifier', true);
			$password = self::request_value('kklidi_members_password', true);
			$remember = isset($_POST['kklidi_members_remember']);
			$nonce = self::request_value(self::NONCE_FIELD);

			if ($nonce === '' || !wp_verify_nonce($nonce, self::NONCE_ACTION)
				|| !\KKLIDI\Members\Security\GuestCsrf::verify(self::NONCE_ACTION)) {
				$message = __('We could not verify this request. Please reload the login page and try again.', 'kklidi-members');
			} elseif ($identifier === '' || $password === '') {
				$message = __('Please correct the highlighted fields.', 'kklidi-members');
				if ($identifier === '') {
					$field_errors['identifier'] = __('Enter your username or email.', 'kklidi-members');
				}
				if ($password === '') {
					$field_errors['password'] = __('Enter your password.', 'kklidi-members');
				}
			} else {
				$user = wp_signon(
					array(
						'user_login'    => $identifier,
						'user_password' => $password,
						'remember'      => isset($_POST['kklidi_members_remember']),
					),
					is_ssl()
				);

				if (!is_wp_error($user)) {
					wp_safe_redirect($redirect_to);
					exit;
				}
				if ($user->get_error_code() === 'kklidi_members_rate_limited') {
					$data = $user->get_error_data();
					status_header(429);
					if (is_array($data) && !empty($data['retry_after'])) {
						header('Retry-After: ' . max(1, (int) $data['retry_after']));
					}
					$message = __('There have been too many login attempts. Please try again later.', 'kklidi-members');
				} elseif ($user->get_error_code() === 'kklidi_device_exchange_required') {
					$message_html = wp_kses_post($user->get_error_message());
				} else {
					$message = __('Please check your login details.', 'kklidi-members');
				}
			}
		}

		$action_url = kklidi_members_login_url($redirect_to);
		$register_url = kklidi_members_register_url($redirect_to);
		$password_reset_url = kklidi_members_password_reset_url($redirect_to);
		$home_url = home_url('/');
		$guest_fields = \KKLIDI\Members\Security\GuestCsrf::fields(self::NONCE_ACTION);
		require KKLIDI_MEMBERS_DIR . 'templates/login.php';
		exit;
	}

	private static function request_value(string $key, bool $preserve = false): string {
		$source = isset($_POST[$key]) ? $_POST[$key] : ($_GET[$key] ?? '');
		if (!is_string($source)) {
			return '';
		}

		$value = wp_unslash($source);

		return $preserve ? $value : sanitize_text_field($value);
	}

	private static function send_private_headers(): void {
		nocache_headers();
		if (!headers_sent()) {
			header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
			header('Pragma: no-cache');
		}
	}
}
