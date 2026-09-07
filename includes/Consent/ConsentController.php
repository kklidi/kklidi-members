<?php

namespace KKLIDI\Members\Consent;

if (!defined('ABSPATH')) {
	exit;
}

final class ConsentController {
	public static function handle(): void {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Repository.php';
		nocache_headers();
		header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
		if (!is_user_logged_in()) {
			wp_safe_redirect(kklidi_members_login_url(add_query_arg('kklidi_members_consent', '1', home_url('/'))));
			exit;
		}
		$user_id = get_current_user_id();
		$message = '';
		$documents = array(
			'service' => Documents::current('service'),
			'privacy' => Documents::current('privacy'),
			'marketing' => Documents::current('marketing'),
		);
		if (strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
			$nonce = self::text('_kklidi_members_consent_nonce');
			$request_id = self::text('request_id');
			if ($nonce === '' || !wp_verify_nonce($nonce, 'kklidi_members_consent') || !wp_is_uuid($request_id)) {
				$message = __('We could not verify this request.', 'kklidi-members');
			} elseif ($documents['service'] === array() || $documents['privacy'] === array()
				|| !isset($_POST['consent_service'], $_POST['consent_privacy'])) {
				$message = __('Please review and accept the required consent documents.', 'kklidi-members');
			} else {
				$changed = array();
				foreach (array('service', 'privacy') as $type) {
					if (!Repository::has_current($user_id, $type)) {
						if (!Repository::append($user_id, $type, 'accept', 'account', $request_id, $documents[$type])) {
							$message = __('We could not save the required consent.', 'kklidi-members');
							break;
						}
						$changed[] = $type;
					}
				}
				if ($message === '' && $documents['marketing'] !== array()) {
					$latest = Repository::latest($user_id, 'marketing');
					$wants = isset($_POST['consent_marketing']);
					$is_current = Repository::has_current($user_id, 'marketing');
					if ($wants && !$is_current) {
						if (!Repository::append($user_id, 'marketing', 'accept', 'account', $request_id, $documents['marketing'])) {
							$message = __('We could not save the optional consent.', 'kklidi-members');
						} else {
							$changed[] = 'marketing_accept';
						}
					} elseif (!$wants && $latest && $latest->action === 'accept') {
						if (!Repository::append($user_id, 'marketing', 'withdraw', 'account', $request_id, $documents['marketing'])) {
							$message = __('We could not save the optional consent withdrawal.', 'kklidi-members');
						} else {
							$changed[] = 'marketing_withdraw';
						}
					}
				}
				if ($message === '') {
					if ($changed) {
						\KKLIDI\Members\Audit\Recorder::record('consent_update', 'success', implode('_', $changed), $user_id, '', $request_id);
					}
					$message = __('Your consent settings have been saved.', 'kklidi-members');
				}
			}
		}
		$current = array(
			'service' => Repository::has_current($user_id, 'service'),
			'privacy' => Repository::has_current($user_id, 'privacy'),
			'marketing' => Repository::has_current($user_id, 'marketing'),
		);
		$request_id = wp_generate_uuid4();
		require KKLIDI_MEMBERS_DIR . 'templates/consent.php';
		exit;
	}

	private static function text(string $key): string {
		return isset($_POST[$key]) && is_string($_POST[$key])
			? sanitize_text_field(wp_unslash($_POST[$key])) : '';
	}
}
