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
			list($subject, $message) = self::content($event);
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

	private static function content(string $event): array {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';
		$site_name = sanitize_text_field(wp_specialchars_decode(get_bloginfo('name'), ENT_QUOTES));

		switch ($event) {
			case 'registration_completed':
				return array(
					sprintf(__('[%s] Registration complete', 'kklidi-members'), $site_name),
					implode("\n\n", array(
						__('Your account registration is complete.', 'kklidi-members'),
						sprintf(__('Sign in: %s', 'kklidi-members'), \KKLIDI\Members\Core\Url::login()),
					)),
				);
			case 'password_changed':
				return array(
					sprintf(__('[%s] Password changed', 'kklidi-members'), $site_name),
					implode("\n\n", array(
						__('The password for your account was changed.', 'kklidi-members'),
						sprintf(
							__('If you did not make this change, reset your password immediately: %s', 'kklidi-members'),
							\KKLIDI\Members\Core\Url::passwordReset()
						),
					)),
				);
			case 'withdrawal_requested':
				return array(
					sprintf(__('[%s] Withdrawal request received', 'kklidi-members'), $site_name),
					implode("\n\n", array(
						__('We received your account withdrawal request.', 'kklidi-members'),
						__('Sign-in access has been blocked while the site administrator and service owners complete their review.', 'kklidi-members'),
					)),
				);
			case 'withdrawal_finalized':
				return array(
					sprintf(__('[%s] Withdrawal processing complete', 'kklidi-members'), $site_name),
					implode("\n\n", array(
						__('Your withdrawal request has been processed and sign-in access remains blocked.', 'kklidi-members'),
						__('Your WordPress account ID and related order or learning records may be retained according to the applicable retention policies.', 'kklidi-members'),
					)),
				);
		}

		return array('', '');
	}
}
