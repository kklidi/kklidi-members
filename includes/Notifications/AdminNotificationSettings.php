<?php

namespace KKLIDI\Members\Notifications;

if (!defined('ABSPATH')) {
	exit;
}

final class AdminNotificationSettings {
	public const OPTION_NAME = 'kklidi_members_admin_notifications';
	public const OPTION_GROUP = 'kklidi_members_admin_notifications';
	public const SETTINGS_PAGE = 'kklidi_members_admin_notifications';
	private const SCHEMA_VERSION = 1;

	public static function register_settings(): void {
		add_option(self::OPTION_NAME, self::defaults(), '', false);
		register_setting(self::OPTION_GROUP, self::OPTION_NAME, array(
			'type' => 'array',
			'sanitize_callback' => array(__CLASS__, 'sanitize'),
			'show_in_rest' => false,
		));
		add_settings_section(
			'kklidi_members_admin_registration_notice',
			__('Delivery policy', 'kklidi-members'),
			array(__CLASS__, 'render_policy'),
			self::SETTINGS_PAGE
		);
		add_settings_field(
			'kklidi_members_admin_registration_enabled',
			__('New member registration', 'kklidi-members'),
			array(__CLASS__, 'render_field'),
			self::SETTINGS_PAGE,
			'kklidi_members_admin_registration_notice'
		);
	}

	public static function settings_capability(string $capability): string {
		return 'manage_kklidi_members';
	}

	public static function sanitize($input): array {
		$previous = self::settings();
		if (!is_array($input)
			|| (int) ($input['version'] ?? 0) !== self::SCHEMA_VERSION
			|| array_diff(array_keys($input), array('version', 'registration_enabled'))) {
			add_settings_error(
				self::OPTION_NAME,
				'kklidi_members_admin_notification_invalid',
				__('Administrator notification settings were not saved because the submitted data was invalid.', 'kklidi-members'),
				'error'
			);
			return $previous;
		}
		return array(
			'version' => self::SCHEMA_VERSION,
			'registration_enabled' => isset($input['registration_enabled'])
				&& (string) $input['registration_enabled'] === '1',
		);
	}

	public static function settings(): array {
		$value = get_option(self::OPTION_NAME, self::defaults());
		if (!is_array($value) || (int) ($value['version'] ?? 0) !== self::SCHEMA_VERSION
			|| !isset($value['registration_enabled'])
			|| !is_bool($value['registration_enabled'])
			|| array_diff(array_keys($value), array('version', 'registration_enabled'))) {
			return self::defaults();
		}
		return $value;
	}

	public static function enabled(): bool {
		return self::settings()['registration_enabled'];
	}

	public static function defaults(): array {
		return array('version' => self::SCHEMA_VERSION, 'registration_enabled' => false);
	}

	public static function audit_update($old_value, $new_value): void {
		if ($old_value === $new_value || !current_user_can('manage_kklidi_members')) {
			return;
		}
		\KKLIDI\Members\Audit\Recorder::record(
			'admin_notification_settings_update',
			'success',
			'admin_settings',
			get_current_user_id(),
			'',
			wp_generate_uuid4()
		);
	}

	public static function render_policy(): void {
		?>
		<p><?php esc_html_e('When enabled, Members requests one plain-text email through WordPress wp_mail() after a registration becomes active.', 'kklidi-members'); ?></p>
		<p><?php esc_html_e('This setting does not require administrator approval and does not delay or roll back registration.', 'kklidi-members'); ?></p>
		<?php
	}

	public static function render_field(): void {
		$settings = self::settings();
		?>
		<input type="hidden" name="<?php echo esc_attr(self::OPTION_NAME); ?>[version]" value="1">
		<label><input type="checkbox" name="<?php echo esc_attr(self::OPTION_NAME); ?>[registration_enabled]" value="1" <?php checked($settings['registration_enabled']); ?>> <?php esc_html_e('Email the WordPress administrator after a new registration becomes active', 'kklidi-members'); ?></label>
		<?php
	}
}
