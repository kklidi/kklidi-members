<?php

namespace KKLIDI\Members\Auth;

if (!defined('ABSPATH')) {
	exit;
}

final class LogoutController {
	public static function handle(): void {
		nocache_headers();
		header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
		$redirect = kklidi_members_safe_redirect_url(self::value('redirect_to', true), home_url('/'));
		if (!is_user_logged_in()) {
			wp_safe_redirect($redirect);
			exit;
		}
		$message = '';
		if (strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
			$nonce = self::value('_kklidi_members_logout_nonce');
			if ($nonce === '' || !wp_verify_nonce($nonce, 'kklidi_members_logout')) {
				$message = __('We could not verify this request.', 'kklidi-members');
			} else {
				$user_id = get_current_user_id();
				\KKLIDI\Members\Audit\Recorder::record('logout', 'success', 'user_request', $user_id);
				wp_logout();
				wp_safe_redirect($redirect);
				exit;
			}
		}
		require KKLIDI_MEMBERS_DIR . 'templates/logout.php';
		exit;
	}

	private static function value(string $key, bool $preserve = false): string {
		$source = $_POST[$key] ?? ($_GET[$key] ?? '');
		if (!is_string($source)) {
			return '';
		}
		$value = wp_unslash($source);
		return $preserve ? $value : sanitize_text_field($value);
	}
}
