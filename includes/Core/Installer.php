<?php

namespace KKLIDI\Members\Core;

if (!defined('ABSPATH')) {
	exit;
}

final class Installer {
	public const SCHEMA_VERSION = '1';

	public static function activate(): void {
		if (is_multisite()) {
			wp_die(esc_html__('KKLIDI Members currently supports single-site installations only.', 'kklidi-members'));
		}

		self::create_tables();
		add_option('kklidi_members_schema_version', self::SCHEMA_VERSION, '', 'no');
		delete_option('kklidi_members_registration_enabled');
		add_option('kklidi_members_own_login_url', '0', '', 'no');
		add_option('kklidi_members_own_register_url', '0', '', 'no');
		add_option('kklidi_members_audit_success_days', '30', '', 'no');
		add_option('kklidi_members_audit_security_days', '90', '', 'no');
		add_option('kklidi_members_notification_templates', array(
			'version' => 1,
			'events' => array(),
		), '', false);
		require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AdminNotificationSettings.php';
		add_option(
			\KKLIDI\Members\Notifications\AdminNotificationSettings::OPTION_NAME,
			\KKLIDI\Members\Notifications\AdminNotificationSettings::defaults(),
			'',
			false
		);
		require_once KKLIDI_MEMBERS_DIR . 'includes/Registration/RegistrationFields.php';
		add_option(
			\KKLIDI\Members\Registration\RegistrationFields::OPTION_NAME,
			\KKLIDI\Members\Registration\RegistrationFields::defaults(),
			'',
			'no'
		);

		$role = get_role('administrator');
		if ($role) {
			$role->add_cap('manage_kklidi_members');
		}

		if (!wp_next_scheduled('kklidi_members_daily_cleanup')) {
			wp_schedule_event(time() + HOUR_IN_SECONDS, 'daily', 'kklidi_members_daily_cleanup');
		}
	}

	public static function create_tables(): void {
		global $wpdb;
		require_once ABSPATH . 'wp-admin/includes/upgrade.php';
		$charset = $wpdb->get_charset_collate();
		$audit = $wpdb->prefix . 'kklidi_mem_login_audit';
		$consents = $wpdb->prefix . 'kklidi_mem_consents';

		dbDelta("CREATE TABLE {$audit} (
			id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
			user_id bigint(20) unsigned NULL,
			occurred_at_utc datetime NOT NULL,
			event_type varchar(40) NOT NULL,
			result varchar(20) NOT NULL,
			reason_code varchar(80) NOT NULL DEFAULT '',
			request_id char(36) NOT NULL,
			subject_digest char(64) NULL,
			network_digest char(64) NULL,
			PRIMARY KEY  (id),
			UNIQUE KEY request_event (request_id,event_type),
			KEY user_time (user_id,occurred_at_utc,id),
			KEY event_time (event_type,occurred_at_utc),
			KEY occurred (occurred_at_utc,id)
		) {$charset};");

		dbDelta("CREATE TABLE {$consents} (
			id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
			user_id bigint(20) unsigned NULL,
			consent_type varchar(30) NOT NULL,
			document_version varchar(80) NULL,
			document_hash char(64) NULL,
			action varchar(20) NOT NULL,
			occurred_at_utc datetime NULL,
			recorded_at_utc datetime NOT NULL,
			source varchar(40) NOT NULL,
			request_id char(36) NOT NULL,
			PRIMARY KEY  (id),
			UNIQUE KEY request_consent_action (request_id,consent_type,action),
			KEY user_consent (user_id,consent_type,id),
			KEY consent_document (consent_type,document_version),
			KEY recorded (recorded_at_utc,id)
		) {$charset};");
	}
}
