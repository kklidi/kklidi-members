<?php

namespace KKLIDI\Members\Notifications;

if (!defined('ABSPATH')) {
	exit;
}

final class AccountMailer {
	private const EVENTS = array(
		'registration_completed',
		'password_changed',
		'withdrawal_requested',
		'withdrawal_finalized',
	);

	/**
	 * Send one post-success account notice to the current Core user email.
	 */
	public static function send(string $event, int $user_id, string $event_id): bool {
		if (!in_array($event, self::EVENTS, true) || $user_id < 1 || !wp_is_uuid($event_id)) {
			return false;
		}

		$user = get_user_by('id', $user_id);
		if (!$user instanceof \WP_User || !is_email($user->user_email)) {
			\KKLIDI\Members\Audit\Recorder::record(
				'mail_' . $event,
				'failure',
				'invalid_recipient',
				$user_id,
				'',
				$event_id
			);
			return false;
		}

		if (!\KKLIDI\Members\Audit\Recorder::claim_notification($event, $user_id, $event_id)) {
			return false;
		}

		$switched = switch_to_user_locale($user_id);
		$sent = false;
		try {
			require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/NotificationTemplates.php';
			list($subject, $message) = NotificationTemplates::content($event);
			$headers = array('Content-Type: text/plain; charset=' . get_bloginfo('charset'));
			$sent = wp_mail($user->user_email, $subject, $message, $headers) === true;
		} catch (\Throwable $error) {
			$sent = false;
		} finally {
			if ($switched) {
				restore_previous_locale();
			}
		}

		\KKLIDI\Members\Audit\Recorder::complete_notification($event, $event_id, $sent);
		return $sent;
	}
}
