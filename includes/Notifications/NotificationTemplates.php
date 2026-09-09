<?php

namespace KKLIDI\Members\Notifications;

if (!defined('ABSPATH')) {
	exit;
}

final class NotificationTemplates {
	public const OPTION_NAME = 'kklidi_members_notification_templates';
	public const OPTION_GROUP = 'kklidi_members_notifications';
	public const SETTINGS_PAGE = 'kklidi_members_notifications';
	private const SCHEMA_VERSION = 1;
	private const SUBJECT_MAX = 200;
	private const BODY_MAX = 5000;
	private const EVENTS = array(
		'registration_completed' => array('site_name', 'login_url'),
		'password_changed' => array('site_name', 'password_reset_url'),
		'withdrawal_requested' => array('site_name'),
		'withdrawal_finalized' => array('site_name'),
	);

	public static function register_settings(): void {
		// Upgrades may load this release without running the activation hook first.
		// Establish the Settings API row explicitly so Core never has to infer autoload.
		add_option(self::OPTION_NAME, self::empty_settings(), '', false);
		register_setting(self::OPTION_GROUP, self::OPTION_NAME, array(
			'type' => 'array',
			'sanitize_callback' => array(__CLASS__, 'sanitize'),
			'show_in_rest' => false,
		));
		add_settings_section(
			'kklidi_members_notification_transport',
			__('Delivery policy', 'kklidi-members'),
			array(__CLASS__, 'render_transport_policy'),
			self::SETTINGS_PAGE
		);
		foreach (array_keys(self::EVENTS) as $event) {
			add_settings_field(
				'kklidi_members_notification_' . $event,
				self::event_label($event),
				array(__CLASS__, 'render_event_field'),
				self::SETTINGS_PAGE,
				'kklidi_members_notification_transport',
				array('event' => $event)
			);
		}
	}

	public static function settings_capability(string $capability): string {
		return 'manage_kklidi_members';
	}

	public static function audit_update($old_value, $new_value): void {
		if ($old_value === $new_value || !current_user_can('manage_kklidi_members')) {
			return;
		}
		\KKLIDI\Members\Audit\Recorder::record(
			'notification_settings_update',
			'success',
			'admin_settings',
			get_current_user_id(),
			'',
			wp_generate_uuid4()
		);
	}

	public static function sanitize($input): array {
		$previous = self::stored_settings();
		if (!is_array($input) || !isset($input['events']) || !is_array($input['events'])) {
			self::settings_error(__('Notification settings were not saved because the submitted data was invalid.', 'kklidi-members'));
			return $previous;
		}

		$sanitized = self::empty_settings();
		foreach (self::EVENTS as $event => $allowed_placeholders) {
			$submitted = isset($input['events'][$event]) && is_array($input['events'][$event])
				? $input['events'][$event] : array();
			foreach (array('subject', 'body') as $field) {
				$raw = isset($submitted[$field]) && is_string($submitted[$field])
					? $submitted[$field] : '';
				$value = $field === 'subject' ? sanitize_text_field($raw) : sanitize_textarea_field($raw);
				if ($value === '') {
					$sanitized['events'][$event][$field] = '';
					continue;
				}
				$error = self::validation_error($value, $field, $allowed_placeholders, $raw);
				if ($error !== '') {
					self::settings_error($error);
					return $previous;
				}
				$sanitized['events'][$event][$field] = $value;
			}
		}
		return $sanitized;
	}

	public static function content(string $event): array {
		if (!isset(self::EVENTS[$event])) {
			return array('', '');
		}

		$defaults = self::default_content($event);
		$settings = self::stored_settings();
		$stored = isset($settings['events'][$event]) && is_array($settings['events'][$event])
			? $settings['events'][$event] : array();
		$resolved = array();
		foreach (array('subject', 'body') as $index => $field) {
			$value = isset($stored[$field]) && is_string($stored[$field]) ? $stored[$field] : '';
			$value = $field === 'subject' ? sanitize_text_field($value) : sanitize_textarea_field($value);
			if ($value === '' || self::validation_error(
				$value,
				$field,
				self::EVENTS[$event],
				$value
			) !== '') {
				$resolved[] = $defaults[$index];
				continue;
			}
			$resolved[] = strtr($value, self::placeholder_values($event));
		}
		return $resolved;
	}

	public static function render_transport_policy(): void {
		?>
		<p><?php esc_html_e('Messages use WordPress wp_mail() as plain text. The active WordPress or site mail transport controls the sender name and address.', 'kklidi-members'); ?></p>
		<p><strong><?php esc_html_e('Sender policy', 'kklidi-members'); ?>:</strong> <?php esc_html_e('Inherited from the WordPress or site mail transport (read only)', 'kklidi-members'); ?></p>
		<p><?php esc_html_e('Empty fields use the translated default at send time for the recipient locale. Leaving a field empty does not disable the notice.', 'kklidi-members'); ?></p>
		<?php
	}

	public static function render_event_field(array $args): void {
		$event = isset($args['event']) && is_string($args['event']) ? $args['event'] : '';
		if (!isset(self::EVENTS[$event])) {
			return;
		}
		$settings = self::stored_settings();
		$values = isset($settings['events'][$event]) && is_array($settings['events'][$event])
			? $settings['events'][$event] : array();
		$subject = isset($values['subject']) && is_string($values['subject']) ? $values['subject'] : '';
		$body = isset($values['body']) && is_string($values['body']) ? $values['body'] : '';
		$name = self::OPTION_NAME . '[events][' . $event . ']';
		$placeholder_list = implode(', ', array_map(static function (string $placeholder): string {
			return '{' . $placeholder . '}';
		}, self::EVENTS[$event]));
		?>
		<div class="kklidi-members-notification-fields">
			<label for="kklidi-members-<?php echo esc_attr($event); ?>-subject"><?php esc_html_e('Subject', 'kklidi-members'); ?></label>
			<input class="large-text" id="kklidi-members-<?php echo esc_attr($event); ?>-subject" maxlength="<?php echo (int) self::SUBJECT_MAX; ?>" name="<?php echo esc_attr($name); ?>[subject]" placeholder="<?php echo esc_attr__('Leave empty to use the translated default subject.', 'kklidi-members'); ?>" type="text" value="<?php echo esc_attr($subject); ?>">
			<label for="kklidi-members-<?php echo esc_attr($event); ?>-body"><?php esc_html_e('Message body', 'kklidi-members'); ?></label>
			<textarea class="large-text code" id="kklidi-members-<?php echo esc_attr($event); ?>-body" maxlength="<?php echo (int) self::BODY_MAX; ?>" name="<?php echo esc_attr($name); ?>[body]" placeholder="<?php echo esc_attr__('Leave empty to use the translated default message for the recipient locale.', 'kklidi-members'); ?>" rows="7"><?php echo esc_textarea($body); ?></textarea>
			<p class="description"><?php printf(esc_html__('Allowed placeholders: %s', 'kklidi-members'), esc_html($placeholder_list)); ?></p>
		</div>
		<?php
	}

	public static function event_label(string $event): string {
		$labels = array(
			'registration_completed' => __('Registration notice', 'kklidi-members'),
			'password_changed' => __('Password-change notice', 'kklidi-members'),
			'withdrawal_requested' => __('Withdrawal-request notice', 'kklidi-members'),
			'withdrawal_finalized' => __('Withdrawal-finalized notice', 'kklidi-members'),
		);
		return $labels[$event] ?? $event;
	}

	private static function default_content(string $event): array {
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

	private static function placeholder_values(string $event): array {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';
		$values = array(
			'{site_name}' => sanitize_text_field(wp_specialchars_decode(get_bloginfo('name'), ENT_QUOTES)),
		);
		if ($event === 'registration_completed') {
			$values['{login_url}'] = \KKLIDI\Members\Core\Url::login();
		} elseif ($event === 'password_changed') {
			$values['{password_reset_url}'] = \KKLIDI\Members\Core\Url::passwordReset();
		}
		return $values;
	}

	private static function stored_settings(): array {
		$value = get_option(self::OPTION_NAME, self::empty_settings());
		if (!is_array($value) || (int) ($value['version'] ?? 0) !== self::SCHEMA_VERSION
			|| !isset($value['events']) || !is_array($value['events'])) {
			return self::empty_settings();
		}
		return $value;
	}

	private static function empty_settings(): array {
		return array('version' => self::SCHEMA_VERSION, 'events' => array());
	}

	private static function validation_error(string $value, string $field,
		array $allowed_placeholders, string $raw): string {
		$limit = $field === 'subject' ? self::SUBJECT_MAX : self::BODY_MAX;
		if (self::text_length($value) > $limit) {
			return $field === 'subject'
				? __('A notification subject exceeds the 200 character limit.', 'kklidi-members')
				: __('A notification message exceeds the 5,000 character limit.', 'kklidi-members');
		}
		if (wp_strip_all_tags($raw) !== $raw || strpos($raw, '<?') !== false
			|| preg_match('/\[[a-z][^\]]*\]/i', $raw)) {
			return __('Notification messages must be plain text without HTML, shortcodes, or PHP.', 'kklidi-members');
		}
		$remainder = $value;
		foreach ($allowed_placeholders as $placeholder) {
			$remainder = str_replace('{' . $placeholder . '}', '', $remainder);
		}
		if (strpos($remainder, '{') !== false || strpos($remainder, '}') !== false) {
			return __('A notification message contains an unknown placeholder.', 'kklidi-members');
		}
		return '';
	}

	private static function settings_error(string $message): void {
		add_settings_error(
			self::OPTION_GROUP,
			'kklidi_members_notification_invalid',
			$message,
			'error'
		);
	}

	private static function text_length(string $value): int {
		return function_exists('mb_strlen') ? mb_strlen($value, 'UTF-8') : strlen($value);
	}
}
