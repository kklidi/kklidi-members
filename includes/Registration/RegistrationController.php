<?php

namespace KKLIDI\Members\Registration;

if (!defined('ABSPATH')) {
	exit;
}

final class RegistrationController {
	private const ACTION = 'kklidi_members_register';

	public static function handle(): void {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Security/GuestCsrf.php';
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Repository.php';
		require_once KKLIDI_MEMBERS_DIR . 'includes/Registration/RegistrationFields.php';
		nocache_headers();
		header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
		$enabled = (bool) get_option('users_can_register', false)
			&& \KKLIDI\Members\Consent\Documents::required_ready();
		$message = $enabled ? '' : __('New registrations are currently closed.', 'kklidi-members');
		$field_errors = array();
		$field_settings = RegistrationFields::settings();
		$field_states = $field_settings['fields'];
		$values = self::safe_values($field_states);
		$request_id = self::text('request_id');
		if (!wp_is_uuid($request_id)) {
			$request_id = wp_generate_uuid4();
		}

		if ($enabled && strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
			$result = self::process($request_id, $field_states);
			if (is_wp_error($result)) {
				$message = $result->get_error_message();
				$field_errors = self::field_errors($result);
				if ($result->get_error_code() === 'rate_limited') {
					status_header(429);
					$data = $result->get_error_data();
					if (is_array($data) && !empty($data['retry_after'])) {
						header('Retry-After: ' . max(1, (int) $data['retry_after']));
					}
				}
			} else {
				wp_safe_redirect(add_query_arg('registered', '1', kklidi_members_login_url()));
				exit;
			}
		}

		$service_document = \KKLIDI\Members\Consent\Documents::current('service');
		$privacy_document = \KKLIDI\Members\Consent\Documents::current('privacy');
		$marketing_document = \KKLIDI\Members\Consent\Documents::current('marketing');
		$login_url = kklidi_members_login_url();
		$home_url = home_url('/');
		$guest_fields = \KKLIDI\Members\Security\GuestCsrf::fields(self::ACTION);
		require KKLIDI_MEMBERS_DIR . 'templates/register.php';
		exit;
	}

	private static function process(string $request_id, array $field_states) {
		$nonce = self::text('_kklidi_members_register_nonce');
		if ($nonce === '' || !wp_verify_nonce($nonce, self::ACTION)
			|| !\KKLIDI\Members\Security\GuestCsrf::verify(self::ACTION)) {
			return new \WP_Error('invalid_request', __('We could not verify this request. Please reload the registration page.', 'kklidi-members'));
		}
		$limit = \KKLIDI\Members\Security\RateLimiter::consume(
			'registration_network',
			\KKLIDI\Members\Security\RateLimiter::network(),
			10,
			HOUR_IN_SECONDS
		);
		if (is_wp_error($limit)) {
			return new \WP_Error('temporarily_unavailable', __('Please try again later.', 'kklidi-members'));
		}
		if (!$limit['allowed']) {
			return new \WP_Error('rate_limited', __('There have been too many registration attempts. Please try again later.', 'kklidi-members'), array(
				'retry_after' => $limit['retry_after'],
			));
		}

		$email = strtolower(sanitize_email(self::text('email')));
		$password = self::raw('password');
		$confirm = self::raw('password_confirm');
		$first = self::visible($field_states, 'first_name') ? self::text('first_name') : '';
		$last = self::visible($field_states, 'last_name') ? self::text('last_name') : '';
		$display = self::text('display_name');
		$phone = self::visible($field_states, 'phone') ? self::text('phone') : '';
		$invalid_fields = array();
		if (!is_email($email)) {
			$invalid_fields[] = 'email';
		}
		if ((self::required($field_states, 'first_name') && $first === '')
			|| ($first !== '' && self::text_length($first) > 200)) {
			$invalid_fields[] = 'first_name';
		}
		if ((self::required($field_states, 'last_name') && $last === '')
			|| ($last !== '' && self::text_length($last) > 200)) {
			$invalid_fields[] = 'last_name';
		}
		if ($display === '' || strlen($display) > 200) {
			$invalid_fields[] = 'display_name';
		}
		if ((self::required($field_states, 'phone') && $phone === '') || !self::valid_phone($phone)) {
			$invalid_fields[] = 'phone';
		}
		if ($invalid_fields) {
			return new \WP_Error('invalid_fields', __('Please check the registration details.', 'kklidi-members'), array(
				'fields' => $invalid_fields,
			));
		}
		if ($password !== $confirm || strlen($password) < 12 || strlen($password) > 1024) {
			return new \WP_Error('invalid_password', __('The password must be at least 12 characters and match the confirmation.', 'kklidi-members'), array(
				'fields' => array('password', 'password_confirm'),
			));
		}
		if (!isset($_POST['consent_service'], $_POST['consent_privacy'])) {
			$fields = array();
			if (!isset($_POST['consent_service'])) {
				$fields[] = 'consent_service';
			}
			if (!isset($_POST['consent_privacy'])) {
				$fields[] = 'consent_privacy';
			}
			return new \WP_Error('consent_required', __('Please accept the required terms and privacy policy.', 'kklidi-members'), array(
				'fields' => $fields,
			));
		}

		global $wpdb;
		$lock = 'kklidi_members_reg_' . substr(hash_hmac('sha256', $email, wp_salt('auth')), 0, 32);
		if ((int) $wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 3)', $lock)) !== 1) {
			return new \WP_Error('registration_busy', __('Another registration request is being processed. Please try again later.', 'kklidi-members'));
		}
		$completed_user_id = 0;
		try {
			$binding = \KKLIDI\Members\Security\GuestCsrf::binding_digest();
			$user = get_user_by('email', $email);
			if ($user) {
				$same_request = \KKLIDI\Members\Security\AccountState::get((int) $user->ID) === 'registration_pending'
					&& hash_equals((string) get_user_meta($user->ID, '_kklidi_members_registration_request_id', true), $request_id)
					&& $binding !== ''
					&& hash_equals((string) get_user_meta($user->ID, '_kklidi_members_registration_binding', true), $binding);
				if (!$same_request) {
					return new \WP_Error('registration_unavailable', __('We could not complete the registration. Please use login or password reset.', 'kklidi-members'));
				}
				$user_id = (int) $user->ID;
			} else {
				$login = self::unique_login();
				$user_id = wp_insert_user(array(
					'user_login' => $login,
					'user_nicename' => str_replace('_', '-', $login),
					'user_email' => $email,
					'user_pass' => $password,
					'first_name' => $first,
					'last_name' => $last,
					'display_name' => $display,
					'role' => 'subscriber',
					'meta_input' => array(
						'_kklidi_members_account_state' => 'registration_pending',
						'_kklidi_members_email_state' => 'legacy_unknown',
						'_kklidi_members_registration_request_id' => $request_id,
						'_kklidi_members_registration_binding' => $binding,
						'billing_phone' => $phone,
					),
				));
				if (is_wp_error($user_id)) {
					return new \WP_Error('registration_unavailable', __('We could not complete the registration. Please use login or password reset.', 'kklidi-members'));
				}
				$user_id = (int) $user_id;
			}

			$service = \KKLIDI\Members\Consent\Documents::current('service');
			$privacy = \KKLIDI\Members\Consent\Documents::current('privacy');
			if (!\KKLIDI\Members\Consent\Repository::append($user_id, 'service', 'accept', 'registration', $request_id, $service)
				|| !\KKLIDI\Members\Consent\Repository::append($user_id, 'privacy', 'accept', 'registration', $request_id, $privacy)) {
				\KKLIDI\Members\Audit\Recorder::record('registration_failed', 'failure', 'consent_storage', $user_id, '', $request_id);
				return new \WP_Error('registration_pending', __('Registration is incomplete. Please try again from this page.', 'kklidi-members'));
			}
			$marketing = \KKLIDI\Members\Consent\Documents::current('marketing');
			if ($marketing !== array() && isset($_POST['consent_marketing'])
				&& !\KKLIDI\Members\Consent\Repository::append($user_id, 'marketing', 'accept', 'registration', $request_id, $marketing)) {
				return new \WP_Error('registration_pending', __('Registration is incomplete. Please try again from this page.', 'kklidi-members'));
			}
			if (!\KKLIDI\Members\Security\AccountState::transition($user_id, 'registration_pending', 'active')) {
				return new \WP_Error('registration_pending', __('Registration is incomplete. Please try again from this page.', 'kklidi-members'));
			}
			delete_user_meta($user_id, '_kklidi_members_registration_binding');
			\KKLIDI\Members\Audit\Recorder::record('registration_success', 'success', 'completed', $user_id, '', $request_id);
			do_action('kklidi_members_account_state_changed', $user_id, 'registration_pending', 'active', $request_id);
			$completed_user_id = $user_id;
		} finally {
			$wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)', $lock));
		}

		require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AccountMailer.php';
		\KKLIDI\Members\Notifications\AccountMailer::send('registration_completed', $completed_user_id, $request_id);
		require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AdminRegistrationMailer.php';
		\KKLIDI\Members\Notifications\AdminRegistrationMailer::send($completed_user_id, $request_id);
		return $completed_user_id;
	}

	private static function unique_login(): string {
		for ($attempt = 0; $attempt < 10; $attempt++) {
			$candidate = 'member_' . bin2hex(random_bytes(8));
			if (!username_exists($candidate)) {
				return $candidate;
			}
		}
		return 'member_' . wp_generate_password(24, false, false);
	}

	private static function valid_phone(string $phone): bool {
		return $phone === '' || (strlen($phone) <= 30 && preg_match('/^[0-9+() .-]{7,30}$/', $phone));
	}

	private static function safe_values(array $field_states): array {
		return array(
			'email' => strtolower(sanitize_email(self::text('email'))),
			'first_name' => self::visible($field_states, 'first_name') ? self::text('first_name') : '',
			'last_name' => self::visible($field_states, 'last_name') ? self::text('last_name') : '',
			'display_name' => self::text('display_name'),
			'phone' => self::visible($field_states, 'phone') ? self::text('phone') : '',
		);
	}

	private static function field_errors(\WP_Error $error): array {
		$data = $error->get_error_data();
		$fields = is_array($data) && isset($data['fields']) && is_array($data['fields'])
			? $data['fields'] : array();
		$messages = array(
			'email' => __('Enter a valid email address.', 'kklidi-members'),
			'first_name' => __('Enter a first name of 200 characters or fewer.', 'kklidi-members'),
			'last_name' => __('Enter a last name of 200 characters or fewer.', 'kklidi-members'),
			'display_name' => __('Enter a display name of 200 characters or fewer.', 'kklidi-members'),
			'phone' => __('Enter a valid phone number or leave this field blank.', 'kklidi-members'),
			'password' => __('Use at least 12 characters.', 'kklidi-members'),
			'password_confirm' => __('Enter the same password again.', 'kklidi-members'),
			'consent_service' => __('You must accept the service terms.', 'kklidi-members'),
			'consent_privacy' => __('You must accept the privacy policy.', 'kklidi-members'),
		);
		$errors = array();
		foreach ($fields as $field) {
			if (isset($messages[$field])) {
				$errors[$field] = $messages[$field];
			}
		}
		return $errors;
	}

	private static function visible(array $states, string $field): bool {
		return isset($states[$field]) && in_array($states[$field], array('required', 'optional'), true);
	}

	private static function required(array $states, string $field): bool {
		return isset($states[$field]) && $states[$field] === 'required';
	}

	private static function text_length(string $value): int {
		return function_exists('mb_strlen') ? mb_strlen($value, 'UTF-8') : strlen($value);
	}

	private static function text(string $key): string {
		return isset($_POST[$key]) && is_string($_POST[$key])
			? sanitize_text_field(wp_unslash($_POST[$key])) : '';
	}

	private static function raw(string $key): string {
		return isset($_POST[$key]) && is_string($_POST[$key]) ? wp_unslash($_POST[$key]) : '';
	}
}
