<?php

namespace KKLIDI\Members\Profile;

if (!defined('ABSPATH')) {
	exit;
}

final class ProfileController {
	public static function handle(): void {
		nocache_headers();
		header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
		if (!is_user_logged_in()) {
			wp_safe_redirect(kklidi_members_login_url(kklidi_members_profile_url()));
			exit;
		}
		$user = wp_get_current_user();
		$message = '';
		$message_type = 'error';
		$field_errors = array();
		$values = array(
			'first_name' => (string) $user->first_name,
			'last_name' => (string) $user->last_name,
			'display_name' => (string) $user->display_name,
			'phone' => (string) get_user_meta($user->ID, 'billing_phone', true),
			'description' => (string) $user->description,
		);
		if (strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
			$nonce = self::text('_kklidi_members_profile_nonce');
			$first = self::text('first_name');
			$last = self::text('last_name');
			$display = self::text('display_name');
			$description = self::textarea('description');
			$phone = self::text('phone');
			$values = array(
				'first_name' => $first,
				'last_name' => $last,
				'display_name' => $display,
				'phone' => $phone,
				'description' => $description,
			);
			if ($nonce === '' || !wp_verify_nonce($nonce, 'kklidi_members_profile')) {
				$message = __('We could not verify this request.', 'kklidi-members');
			} elseif ($display === '' || strlen($display) > 200 || !self::valid_phone($phone)) {
				$message = __('Please correct the highlighted fields.', 'kklidi-members');
				if ($display === '' || strlen($display) > 200) {
					$field_errors['display_name'] = __('Enter a display name of 200 characters or fewer.', 'kklidi-members');
				}
				if (!self::valid_phone($phone)) {
					$field_errors['phone'] = __('Enter a valid phone number or leave this field blank.', 'kklidi-members');
				}
			} else {
				$changed = array();
				$old_phone = (string) get_user_meta($user->ID, 'billing_phone', true);
				foreach (array('first_name' => $first, 'last_name' => $last,
					'display_name' => $display, 'description' => $description) as $field => $value) {
					if ((string) $user->{$field} !== $value) {
						$changed[] = $field;
					}
				}
				$result = wp_update_user(array(
					'ID' => $user->ID,
					'first_name' => $first,
					'last_name' => $last,
					'display_name' => $display,
					'description' => $description,
				));
				if (is_wp_error($result) || !self::save_phone((int) $user->ID, $phone)) {
					$message = __('We could not save your profile.', 'kklidi-members');
				} else {
					if ($old_phone !== $phone) {
						$changed[] = 'phone';
						delete_user_meta($user->ID, '_kklidi_members_phone_verified_at');
					}
					$changed = array_values(array_unique($changed));
					if ($changed) {
						do_action('kklidi_members_profile_updated', (int) $user->ID, $changed);
						\KKLIDI\Members\Audit\Recorder::record('profile_update', 'success', implode('_', $changed), (int) $user->ID);
					}
					$message = __('Your profile has been saved.', 'kklidi-members');
					$message_type = 'success';
					$user = wp_get_current_user();
					$values = array(
						'first_name' => (string) $user->first_name,
						'last_name' => (string) $user->last_name,
						'display_name' => (string) $user->display_name,
						'phone' => (string) get_user_meta($user->ID, 'billing_phone', true),
						'description' => (string) $user->description,
					);
				}
			}
		}
		$account_url = kklidi_members_account_url();
		require KKLIDI_MEMBERS_DIR . 'templates/profile.php';
		exit;
	}

	private static function save_phone(int $user_id, string $phone): bool {
		if (class_exists('WC_Customer')) {
			try {
				$customer = new \WC_Customer($user_id);
				$customer->set_billing_phone($phone);
				$customer->save();
				return true;
			} catch (\Throwable $error) {
				return false;
			}
		}
		$updated = update_user_meta($user_id, 'billing_phone', $phone);
		return $updated !== false || (string) get_user_meta($user_id, 'billing_phone', true) === $phone;
	}

	private static function valid_phone(string $phone): bool {
		return $phone === '' || (strlen($phone) <= 30 && preg_match('/^[0-9+() .-]{7,30}$/', $phone));
	}

	private static function text(string $key): string {
		return isset($_POST[$key]) && is_string($_POST[$key])
			? sanitize_text_field(wp_unslash($_POST[$key])) : '';
	}

	private static function textarea(string $key): string {
		return isset($_POST[$key]) && is_string($_POST[$key])
			? sanitize_textarea_field(wp_unslash($_POST[$key])) : '';
	}
}
