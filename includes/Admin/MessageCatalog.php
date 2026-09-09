<?php

namespace KKLIDI\Members\Admin;

if (!defined('ABSPATH')) {
	exit;
}

/**
 * Read-only catalog of the approved account messages.
 *
 * The English strings remain the gettext source of truth. This class does not
 * register settings, filters, or storage and is loaded only for the Messages
 * section of the Members administration screen.
 */
final class MessageCatalog {
	public static function groups(): array {
		return array(
			'account_notices' => array(
				'label' => __('Account notices', 'kklidi-members'),
				'messages' => array(
					self::message('registration_complete', 'notice', __('Your account was created. Please sign in with the email address you registered.', 'kklidi-members')),
					self::message('password_changed', 'notice', __('Your password was changed. Please sign in again.', 'kklidi-members')),
					self::message('password_reset', 'notice', __('Your password has been reset. Please log in with your new password.', 'kklidi-members')),
					self::message('withdrawal_requested', 'notice', __('Your withdrawal request was submitted. Access is blocked while it is reviewed.', 'kklidi-members')),
				),
			),
			'authentication' => array(
				'label' => __('Authentication', 'kklidi-members'),
				'messages' => array(
					self::message('invalid_credentials', 'security', __('Please check your login details.', 'kklidi-members')),
					self::message('login_rate_limited', 'security', __('There have been too many login attempts. Please try again later.', 'kklidi-members')),
				),
			),
			'registration' => array(
				'label' => __('Registration', 'kklidi-members'),
				'messages' => array(
					self::message('registration_closed', 'error', __('New registrations are currently closed.', 'kklidi-members')),
					self::message('registration_invalid', 'error', __('Please check the registration details.', 'kklidi-members')),
					self::message('registration_unavailable', 'security', __('We could not complete the registration. Please use login or password reset.', 'kklidi-members')),
				),
			),
			'password_reset' => array(
				'label' => __('Password reset', 'kklidi-members'),
				'messages' => array(
					self::message('reset_request_generic', 'security', __('If an account matches that information, WordPress will send a password reset link.', 'kklidi-members')),
					self::message('reset_invalid_link', 'security', __('This password reset link is invalid or has expired. Request a new link.', 'kklidi-members')),
				),
			),
			'profile' => array(
				'label' => __('Profile', 'kklidi-members'),
				'messages' => array(
					self::message('profile_saved', 'notice', __('Your profile has been saved.', 'kklidi-members')),
					self::message('profile_save_failed', 'error', __('We could not save your profile.', 'kklidi-members')),
				),
			),
			'consent' => array(
				'label' => __('Consent', 'kklidi-members'),
				'messages' => array(
					self::message('consent_saved', 'notice', __('Your consent settings have been saved.', 'kklidi-members')),
					self::message('consent_save_failed', 'error', __('We could not save the required consent.', 'kklidi-members')),
				),
			),
			'withdrawal' => array(
				'label' => __('Withdrawal', 'kklidi-members'),
				'messages' => array(
					self::message('withdrawal_save_failed', 'error', __('We could not save the withdrawal request.', 'kklidi-members')),
				),
			),
		);
	}

	public static function type_label(string $type): string {
		$labels = array(
			'notice' => __('Notice', 'kklidi-members'),
			'error' => __('Error', 'kklidi-members'),
			'security' => __('Security message', 'kklidi-members'),
		);
		return $labels[$type] ?? $type;
	}

	private static function message(string $key, string $type, string $text): array {
		return array('key' => $key, 'type' => $type, 'text' => $text);
	}
}
