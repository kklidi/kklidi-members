<?php

namespace KKLIDI\Members\Withdrawal;

if (!defined('ABSPATH')) {
	exit;
}

final class WithdrawalController {
	public static function handle(): void {
		nocache_headers();
		header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
		if (!is_user_logged_in()) {
			wp_safe_redirect(kklidi_members_login_url());
			exit;
		}
		$user = wp_get_current_user();
		$message = '';
		$field_errors = array();
		if (user_can($user, 'manage_options')) {
			$message = __('Administrator accounts require separate manual review for withdrawal.', 'kklidi-members');
		} elseif (strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
			$nonce = self::text('_kklidi_members_withdrawal_nonce');
			$password = self::raw('current_password');
			$request_id = self::text('request_id');
			if ($nonce === '' || !wp_verify_nonce($nonce, 'kklidi_members_withdrawal') || !wp_is_uuid($request_id)) {
				$message = __('We could not verify this request.', 'kklidi-members');
			} elseif (!wp_check_password($password, $user->user_pass, $user->ID)) {
				$message = __('Please check your current password.', 'kklidi-members');
				$field_errors['current_password'] = __('Enter your current password again.', 'kklidi-members');
			} else {
				$state = \KKLIDI\Members\Security\AccountState::get((int) $user->ID);
				$existing_request = (string) get_user_meta($user->ID, '_kklidi_members_withdrawal_request_id', true);
				$transitioned = ($state === 'withdrawal_pending' && hash_equals($existing_request, $request_id))
					|| \KKLIDI\Members\Security\AccountState::transition((int) $user->ID, 'active', 'withdrawal_pending');
				if (!$transitioned) {
					$message = __('We could not save the withdrawal request.', 'kklidi-members');
				} else {
					update_user_meta($user->ID, '_kklidi_members_withdrawal_requested_at', current_time('mysql', true));
					update_user_meta($user->ID, '_kklidi_members_withdrawal_request_id', $request_id);
					\KKLIDI\Members\Audit\Recorder::record('withdrawal_request', 'success', 'self', (int) $user->ID, '', $request_id);
					do_action('kklidi_members_account_state_changed', (int) $user->ID, 'active', 'withdrawal_pending', $request_id);
					\KKLIDI\Members\Security\AccountState::revoke_access((int) $user->ID);
					require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AccountMailer.php';
					\KKLIDI\Members\Notifications\AccountMailer::send('withdrawal_requested', (int) $user->ID, $request_id);
					wp_clear_auth_cookie();
					wp_set_current_user(0);
					wp_safe_redirect(add_query_arg('withdrawal', 'requested', kklidi_members_login_url()));
					exit;
				}
			}
		}
		$request_id = wp_generate_uuid4();
		require KKLIDI_MEMBERS_DIR . 'templates/withdrawal.php';
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
