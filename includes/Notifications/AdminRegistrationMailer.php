<?php

namespace KKLIDI\Members\Notifications;

if (!defined('ABSPATH')) {
	exit;
}

final class AdminRegistrationMailer {
	private const EVENT = 'admin_registration';

	public static function send(int $user_id, string $request_id): bool {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AdminNotificationSettings.php';
		if (!AdminNotificationSettings::enabled() || $user_id < 1 || !wp_is_uuid($request_id)) {
			return false;
		}

		$user = get_user_by('id', $user_id);
		$recipient = sanitize_email((string) get_option('admin_email', ''));
		if (!$user instanceof \WP_User || !is_email($recipient)) {
			\KKLIDI\Members\Audit\Recorder::record(
				'mail_' . self::EVENT,
				'failure',
				'invalid_recipient',
				$user_id,
				'',
				$request_id
			);
			return false;
		}

		if (!\KKLIDI\Members\Audit\Recorder::claim_notification(self::EVENT, $user_id, $request_id)) {
			return false;
		}

		$site_locale = (string) get_option('WPLANG', '');
		$site_locale = $site_locale !== '' ? $site_locale : 'en_US';
		$switched = switch_to_locale($site_locale);
		$sent = false;
		try {
			$site_name = sanitize_text_field(wp_specialchars_decode(get_bloginfo('name'), ENT_QUOTES));
			$subject = sprintf(__('[%s] New member registration', 'kklidi-members'), $site_name);
			$message = implode("\n\n", array(
				__('A new member registration is complete.', 'kklidi-members'),
				sprintf(__('Display name: %s', 'kklidi-members'), sanitize_text_field($user->display_name)),
				sprintf(__('Email: %s', 'kklidi-members'), sanitize_email($user->user_email)),
				sprintf(__('Registered at (UTC): %s', 'kklidi-members'), sanitize_text_field($user->user_registered)),
			));
			$headers = array('Content-Type: text/plain; charset=' . get_bloginfo('charset'));
			$sent = wp_mail($recipient, $subject, $message, $headers) === true;
		} catch (\Throwable $error) {
			$sent = false;
		} finally {
			if ($switched) {
				restore_previous_locale();
			}
		}

		\KKLIDI\Members\Audit\Recorder::complete_notification(self::EVENT, $request_id, $sent);
		return $sent;
	}
}
