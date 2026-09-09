<?php

namespace KKLIDI\Members\Auth;

if (!defined('ABSPATH')) {
	exit;
}

final class PasswordController {
	public static function handle(): void {
		nocache_headers();
		header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
		if (!is_user_logged_in()) {
			wp_safe_redirect(kklidi_members_login_url(kklidi_members_account_url()));
			exit;
		}
		$message = '';
		if (strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
			$nonce = self::text('_kklidi_members_password_nonce');
			$current = self::raw('current_password');
			$new = self::raw('new_password');
			$confirm = self::raw('new_password_confirm');
			$user = wp_get_current_user();
			if ($nonce === '' || !wp_verify_nonce($nonce, 'kklidi_members_password')) {
				$message = __('We could not verify this request.', 'kklidi-members');
			} elseif (!wp_check_password($current, $user->user_pass, $user->ID)) {
				$message = __('Please check your current password.', 'kklidi-members');
			} elseif ($new !== $confirm || strlen($new) < 12 || strlen($new) > 1024) {
				$message = __('The new password must be at least 12 characters and match the confirmation.', 'kklidi-members');
			} else {
				$request_id = wp_generate_uuid4();
				wp_set_password($new, $user->ID);
				\KKLIDI\Members\Security\AccountState::revoke_access((int) $user->ID);
				\KKLIDI\Members\Audit\Recorder::record('password_change', 'success', 'self', (int) $user->ID, '', $request_id);
				require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AccountMailer.php';
				\KKLIDI\Members\Notifications\AccountMailer::send('password_changed', (int) $user->ID, $request_id);
				wp_clear_auth_cookie();
				wp_set_current_user(0);
				wp_safe_redirect(kklidi_members_login_url());
				exit;
			}
		}
		require KKLIDI_MEMBERS_DIR . 'templates/password.php';
		exit;
	}

	private static function text(string $key): string {
		return isset($_POST[$key]) && is_string($_POST[$key])
			? sanitize_text_field(wp_unslash($_POST[$key])) : '';
	}

	private static function raw(string $key): string {
		return isset($_POST[$key]) && is_string($_POST[$key]) ? wp_unslash($_POST[$key]) : '';
	}
}
