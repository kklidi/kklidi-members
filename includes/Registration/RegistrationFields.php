<?php

namespace KKLIDI\Members\Registration;

if (!defined('ABSPATH')) {
	exit;
}

final class RegistrationFields {
	public const OPTION_NAME = 'kklidi_members_registration_fields';
	public const OPTION_GROUP = 'kklidi_members_registration_fields';
	public const SETTINGS_PAGE = 'kklidi_members_registration_fields';
	private const VERSION = 1;
	private const FIELD_KEYS = array('first_name', 'last_name', 'phone');
	private const FIXED_REQUIRED_FIELDS = array('email', 'password', 'password_confirm', 'display_name', 'consent_service', 'consent_privacy');
	private const STATES = array('required', 'optional', 'hidden');

	public static function defaults(): array {
		return array(
			'version' => self::VERSION,
			'fields' => array(
				'first_name' => 'required',
				'last_name' => 'optional',
				'phone' => 'optional',
			),
		);
	}

	public static function settings(): array {
		$normalized = self::normalize(get_option(self::OPTION_NAME, null));
		return $normalized ?? self::defaults();
	}

	public static function state(string $field): string {
		$settings = self::settings();
		return isset($settings['fields'][$field]) ? $settings['fields'][$field] : 'hidden';
	}

	public static function fixed_required_fields(): array {
		return array(
			'email' => __('Email', 'kklidi-members'),
			'password' => __('Password', 'kklidi-members'),
			'password_confirm' => __('Confirm password', 'kklidi-members'),
			'display_name' => __('Display name', 'kklidi-members'),
			'consent_service' => __('Service terms consent', 'kklidi-members'),
			'consent_privacy' => __('Privacy policy consent', 'kklidi-members'),
		);
	}

	public static function is_required(string $field, array $states = array()): bool {
		if (in_array($field, self::FIXED_REQUIRED_FIELDS, true)) {
			return true;
		}
		return isset($states[$field]) && $states[$field] === 'required';
	}

	public static function render_required_marker(bool $required): void {
		if ($required) {
			echo '<span class="kklidi-members-required" aria-hidden="true">*</span>';
		}
	}

	public static function register_settings(): void {
		add_option(self::OPTION_NAME, self::defaults(), '', 'no');
		register_setting(self::OPTION_GROUP, self::OPTION_NAME, array(
			'type' => 'array',
			'sanitize_callback' => array(__CLASS__, 'sanitize'),
			'show_in_rest' => false,
		));
		add_settings_section(
			'kklidi_members_registration_fields_section',
			__('Registration fields', 'kklidi-members'),
			array(__CLASS__, 'render_section'),
			self::SETTINGS_PAGE
		);
		foreach (self::field_labels() as $field => $label) {
			add_settings_field(
				'kklidi_members_registration_field_' . $field,
				$label,
				array(__CLASS__, 'render_field'),
				self::SETTINGS_PAGE,
				'kklidi_members_registration_fields_section',
				array('field' => $field, 'label_for' => 'kklidi-members-registration-field-' . $field)
			);
		}
	}

	public static function settings_capability(string $capability): string {
		return 'manage_kklidi_members';
	}

	public static function render_section(): void {
		echo '<p>' . esc_html__('Choose whether each approved built-in field is required, optional, or hidden. Identity, password, display name, and required consent fields stay required.', 'kklidi-members') . '</p>';
		echo '<input type="hidden" name="' . esc_attr(self::OPTION_NAME) . '[version]" value="' . (int) self::VERSION . '">';
	}

	public static function render_field(array $args): void {
		$field = isset($args['field']) && is_string($args['field']) ? $args['field'] : '';
		if (!in_array($field, self::FIELD_KEYS, true)) {
			return;
		}
		$current = self::state($field);
		?>
		<select id="kklidi-members-registration-field-<?php echo esc_attr($field); ?>" name="<?php echo esc_attr(self::OPTION_NAME); ?>[fields][<?php echo esc_attr($field); ?>]">
			<?php foreach (self::state_labels() as $state => $label) : ?>
				<option value="<?php echo esc_attr($state); ?>" <?php selected($current, $state); ?>><?php echo esc_html($label); ?></option>
			<?php endforeach; ?>
		</select>
		<?php
	}

	public static function sanitize($input): array {
		$current = self::settings();
		if (!current_user_can('manage_kklidi_members')) {
			return $current;
		}
		$normalized = self::normalize($input);
		if ($normalized === null) {
			add_settings_error(
				self::OPTION_NAME,
				'kklidi_members_registration_fields_invalid',
				__('Registration field settings were not saved because they contained an unsupported field or state.', 'kklidi-members'),
				'error'
			);
			return $current;
		}
		return $normalized;
	}

	public static function audit_update($old_value, $new_value): void {
		$old = self::normalize($old_value);
		$new = self::normalize($new_value);
		if ($new === null || $old === $new || !current_user_can('manage_kklidi_members')) {
			return;
		}
		$states = array();
		foreach (self::FIELD_KEYS as $field) {
			$states[] = $field . ':' . $new['fields'][$field];
		}
		\KKLIDI\Members\Audit\Recorder::record(
			'registration_fields_update',
			'success',
			'admin_settings',
			get_current_user_id(),
			implode('|', $states),
			wp_generate_uuid4()
		);
	}

	private static function normalize($input): ?array {
		if (!is_array($input) || count($input) !== 2 || !array_key_exists('version', $input)
			|| !array_key_exists('fields', $input) || (int) $input['version'] !== self::VERSION
			|| !is_array($input['fields']) || count($input['fields']) !== count(self::FIELD_KEYS)
			|| array_diff(array_keys($input['fields']), self::FIELD_KEYS)
			|| array_diff(self::FIELD_KEYS, array_keys($input['fields']))) {
			return null;
		}
		$fields = array();
		foreach (self::FIELD_KEYS as $field) {
			$state = is_string($input['fields'][$field]) ? sanitize_key($input['fields'][$field]) : '';
			if (!in_array($state, self::STATES, true)) {
				return null;
			}
			$fields[$field] = $state;
		}
		return array('version' => self::VERSION, 'fields' => $fields);
	}

	private static function field_labels(): array {
		return array(
			'first_name' => __('First name', 'kklidi-members'),
			'last_name' => __('Last name', 'kklidi-members'),
			'phone' => __('Phone', 'kklidi-members'),
		);
	}

	private static function state_labels(): array {
		return array(
			'required' => __('Required', 'kklidi-members'),
			'optional' => __('Optional', 'kklidi-members'),
			'hidden' => __('Hidden', 'kklidi-members'),
		);
	}
}
