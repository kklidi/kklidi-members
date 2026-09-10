<?php

namespace KKLIDI\Members\Notifications;

if (!defined('ABSPATH')) {
	exit;
}

/**
 * Owns the bounded sender/footer settings for Members-owned mail only.
 */
final class MailSenderSettings {
	public const OPTION_NAME = 'kklidi_members_mail_sender';
	public const OPTION_GROUP = 'kklidi_members_mail_sender';
	public const SETTINGS_PAGE = 'kklidi_members_mail_sender';
	private const SCHEMA_VERSION = 1;
	private const FROM_NAME_MAX = 100;
	private const FROM_EMAIL_MAX = 254;
	private const FOOTER_MAX = 500;

	public static function register_settings(): void {
		add_option(self::OPTION_NAME, self::defaults(), '', false);
		register_setting(self::OPTION_GROUP, self::OPTION_NAME, array(
			'type' => 'array',
			'sanitize_callback' => array(__CLASS__, 'sanitize'),
			'show_in_rest' => false,
		));
		add_settings_section(
			'kklidi_members_mail_sender',
			__('Members sender and footer', 'kklidi-members'),
			array(__CLASS__, 'render_policy'),
			self::SETTINGS_PAGE
		);
		add_settings_field(
			'kklidi_members_mail_sender_fields',
			__('Sender and footer settings', 'kklidi-members'),
			array(__CLASS__, 'render_fields'),
			self::SETTINGS_PAGE,
			'kklidi_members_mail_sender'
		);
	}

	public static function settings_capability(string $capability): string {
		return 'manage_kklidi_members';
	}

	public static function audit_update($old_value, $new_value): void {
		if ($old_value === $new_value || !current_user_can('manage_kklidi_members')) {
			return;
		}
		\KKLIDI\Members\Audit\Recorder::record(
			'mail_sender_settings_update',
			'success',
			'admin_settings',
			get_current_user_id(),
			'',
			wp_generate_uuid4()
		);
	}

	public static function sanitize($input): array {
		$previous = self::settings();
		if (!is_array($input)
			|| (int) ($input['version'] ?? 0) !== self::SCHEMA_VERSION
			|| array_diff(array_keys($input), array(
				'version', 'sender_enabled', 'from_name', 'from_email', 'footer_enabled', 'footer_text',
			))) {
			self::settings_error(__('Sender settings were not saved because the submitted data was invalid.', 'kklidi-members'));
			return $previous;
		}

		$from_name = isset($input['from_name']) && is_string($input['from_name'])
			? wp_unslash($input['from_name']) : '';
		$from_email = isset($input['from_email']) && is_string($input['from_email'])
			? trim(wp_unslash($input['from_email'])) : '';
		$footer_text = isset($input['footer_text']) && is_string($input['footer_text'])
			? wp_unslash($input['footer_text']) : '';

		$from_name_error = self::plain_text_error($from_name, self::FROM_NAME_MAX);
		if ($from_name_error !== '') {
			self::settings_error($from_name_error);
			return $previous;
		}
		if (self::contains_line_break($from_email) || self::text_length($from_email) > self::FROM_EMAIL_MAX
			|| ($from_email !== '' && !is_email($from_email))) {
			self::settings_error(__('The sender email must be a valid email address without line breaks.', 'kklidi-members'));
			return $previous;
		}
		$footer_error = self::plain_text_error($footer_text, self::FOOTER_MAX);
		if ($footer_error !== '') {
			self::settings_error($footer_error);
			return $previous;
		}

		return array(
			'version' => self::SCHEMA_VERSION,
			'sender_enabled' => isset($input['sender_enabled']) && (string) $input['sender_enabled'] === '1',
			'from_name' => sanitize_text_field($from_name),
			'from_email' => sanitize_email($from_email),
			'footer_enabled' => isset($input['footer_enabled']) && (string) $input['footer_enabled'] === '1',
			'footer_text' => sanitize_textarea_field($footer_text),
		);
	}

	/**
	 * Apply settings to a Members-owned plain-text message and its headers.
	 * No global mail filters are registered.
	 *
	 * @return array{message:string,headers:array<int,string>}
	 */
	public static function prepare(string $message, array $headers = array()): array {
		$settings = self::settings();
		if ($settings['footer_enabled']) {
			$footer = $settings['footer_text'] !== ''
				? $settings['footer_text']
				: __('This is a no-reply email. Please use the website support channel if you need help.', 'kklidi-members');
			$message = rtrim($message) . "\n\n" . trim($footer);
		}

		if ($settings['sender_enabled'] && $settings['from_email'] !== '' && is_email($settings['from_email'])) {
			$from = $settings['from_email'];
			if ($settings['from_name'] !== '') {
				$from = $settings['from_name'] . ' <' . $settings['from_email'] . '>';
			}
			$headers[] = 'From: ' . $from;
		}

		return array('message' => $message, 'headers' => array_values($headers));
	}

	/**
	 * Send a bounded test message to the current administrator only.
	 *
	 * @return true|\WP_Error
	 */
	public static function test_send() {
		$admin_id = get_current_user_id();
		$admin = $admin_id > 0 ? get_userdata($admin_id) : false;
		if (!$admin instanceof \WP_User || !is_email($admin->user_email)) {
			self::record_test($admin_id, false, 'invalid_recipient');
			return new \WP_Error('invalid_recipient', __('The current administrator email is not valid.', 'kklidi-members'));
		}

		require_once KKLIDI_MEMBERS_DIR . 'includes/Security/RateLimiter.php';
		$limited = \KKLIDI\Members\Security\RateLimiter::consume(
			'mail_sender_test',
			(string) $admin_id,
			3,
			15 * MINUTE_IN_SECONDS
		);
		if (is_wp_error($limited) || !$limited['allowed']) {
			self::record_test($admin_id, false, 'rate_limited');
			return new \WP_Error('rate_limited', __('Please try again later.', 'kklidi-members'));
		}

		$site_name = sanitize_text_field(wp_specialchars_decode(get_bloginfo('name'), ENT_QUOTES));
		$subject = sprintf(__('[%s] Members sender test', 'kklidi-members'), $site_name);
		$message = __('This is a test email for the Members-owned account notification sender.', 'kklidi-members');
		$prepared = self::prepare($message, array('Content-Type: text/plain; charset=' . get_bloginfo('charset')));
		$sent = wp_mail($admin->user_email, $subject, $prepared['message'], $prepared['headers']) === true;
		self::record_test($admin_id, $sent, $sent ? 'wp_mail_accepted' : 'wp_mail_failed');
		return $sent ? true : new \WP_Error('mail_failed', __('WordPress could not accept the test email.', 'kklidi-members'));
	}

	public static function defaults(): array {
		return array(
			'version' => self::SCHEMA_VERSION,
			'sender_enabled' => false,
			'from_name' => '',
			'from_email' => '',
			'footer_enabled' => false,
			'footer_text' => '',
		);
	}

	public static function settings(): array {
		$value = get_option(self::OPTION_NAME, self::defaults());
		if (!is_array($value)
			|| (int) ($value['version'] ?? 0) !== self::SCHEMA_VERSION
			|| array_diff(array_keys($value), array(
				'version', 'sender_enabled', 'from_name', 'from_email', 'footer_enabled', 'footer_text',
			))
			|| !is_bool($value['sender_enabled'] ?? null)
			|| !is_bool($value['footer_enabled'] ?? null)
			|| !is_string($value['from_name'] ?? null)
			|| !is_string($value['from_email'] ?? null)
			|| !is_string($value['footer_text'] ?? null)
			|| self::plain_text_error($value['from_name'], self::FROM_NAME_MAX) !== ''
			|| self::contains_line_break($value['from_email'])
			|| self::text_length($value['from_email']) > self::FROM_EMAIL_MAX
			|| ($value['from_email'] !== '' && !is_email($value['from_email']))
			|| self::plain_text_error($value['footer_text'], self::FOOTER_MAX) !== '') {
			return self::defaults();
		}
		return array(
			'version' => self::SCHEMA_VERSION,
			'sender_enabled' => $value['sender_enabled'],
			'from_name' => $value['from_name'],
			'from_email' => $value['from_email'],
			'footer_enabled' => $value['footer_enabled'],
			'footer_text' => $value['footer_text'],
		);
	}

	public static function render_policy(): void {
		?>
		<p><?php esc_html_e('These settings apply only to Members-owned account notices and administrator registration notices. WordPress Core, WooCommerce, LMS, and other plugin mail keep their existing sender.', 'kklidi-members'); ?></p>
		<p><?php esc_html_e('Members uses WordPress wp_mail() and plain text. It does not store SMTP credentials or register global sender filters. Confirm SPF, DKIM, and DMARC with your mail provider before using a custom address.', 'kklidi-members'); ?></p>
		<?php
	}

	public static function render_fields(): void {
		$settings = self::settings();
		?>
		<label><input type="checkbox" name="<?php echo esc_attr(self::OPTION_NAME); ?>[sender_enabled]" value="1" <?php checked($settings['sender_enabled']); ?>> <?php esc_html_e('Use a custom sender for Members emails', 'kklidi-members'); ?></label>
		<p><label for="kklidi-members-mail-from-name"><?php esc_html_e('Sender name', 'kklidi-members'); ?></label><br><input class="regular-text" id="kklidi-members-mail-from-name" maxlength="100" name="<?php echo esc_attr(self::OPTION_NAME); ?>[from_name]" type="text" value="<?php echo esc_attr($settings['from_name']); ?>"><br><span class="description"><?php esc_html_e('Plain text only, up to 100 characters. Leave empty to use the mail transport default name.', 'kklidi-members'); ?></span></p>
		<p><label for="kklidi-members-mail-from-email"><?php esc_html_e('Sender email', 'kklidi-members'); ?></label><br><input class="regular-text" id="kklidi-members-mail-from-email" maxlength="254" name="<?php echo esc_attr(self::OPTION_NAME); ?>[from_email]" type="email" value="<?php echo esc_attr($settings['from_email']); ?>"><br><span class="description"><?php esc_html_e('Use an address owned and authorized by the site mail provider.', 'kklidi-members'); ?></span></p>
		<label><input type="checkbox" name="<?php echo esc_attr(self::OPTION_NAME); ?>[footer_enabled]" value="1" <?php checked($settings['footer_enabled']); ?>> <?php esc_html_e('Append a sender-only footer to Members emails', 'kklidi-members'); ?></label>
		<p><label for="kklidi-members-mail-footer-text"><?php esc_html_e('Footer text', 'kklidi-members'); ?></label><br><textarea class="large-text" id="kklidi-members-mail-footer-text" maxlength="500" name="<?php echo esc_attr(self::OPTION_NAME); ?>[footer_text]" rows="4"><?php echo esc_textarea($settings['footer_text']); ?></textarea><br><span class="description"><?php esc_html_e('Plain text only, up to 500 characters. Leave empty to use the translated no-reply default.', 'kklidi-members'); ?></span></p>
		<?php
	}

	private static function plain_text_error(string $value, int $limit): string {
		if (self::contains_line_break($value) || self::text_length($value) > $limit
			|| wp_strip_all_tags($value) !== $value || strpos($value, '<?') !== false
			|| preg_match('/\[[a-z][^\]]*\]/i', $value)) {
			return $limit === self::FOOTER_MAX
				? __('The footer must be plain text without HTML, shortcodes, PHP, or line breaks and stay within 500 characters.', 'kklidi-members')
				: __('The sender name must be plain text without HTML, PHP, or line breaks and stay within 100 characters.', 'kklidi-members');
		}
		return '';
	}

	private static function contains_line_break(string $value): bool {
		return strpos($value, "\r") !== false || strpos($value, "\n") !== false;
	}

	private static function settings_error(string $message): void {
		add_settings_error(self::OPTION_NAME, 'kklidi_members_mail_sender_invalid', $message, 'error');
	}

	private static function record_test(int $user_id, bool $sent, string $reason): void {
		\KKLIDI\Members\Audit\Recorder::record(
			'mail_sender_test',
			$sent ? 'success' : 'failure',
			$reason,
			$user_id,
			'',
			wp_generate_uuid4()
		);
	}

	private static function text_length(string $value): int {
		return function_exists('mb_strlen') ? mb_strlen($value, 'UTF-8') : strlen($value);
	}
}
