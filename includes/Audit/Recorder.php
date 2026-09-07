<?php

namespace KKLIDI\Members\Audit;

if (!defined('ABSPATH')) {
	exit;
}

final class Recorder {
	private static $request_id = '';

	public static function boot(): void {
		add_action('wp_login', array(__CLASS__, 'login_success'), PHP_INT_MAX, 2);
		add_action('wp_login_failed', array(__CLASS__, 'login_failed'), PHP_INT_MAX, 2);
	}

	public static function login_success(string $login, \WP_User $user): void {
		self::record('login', 'success', 'core', (int) $user->ID, $login);
	}

	public static function login_failed(string $username, $error): void {
		$reason = $error instanceof \WP_Error && $error->get_error_code()
			? sanitize_key($error->get_error_code()) : 'authentication_failed';
		self::record('login', 'failure', $reason, 0, $username);
	}

	public static function record(string $event, string $result, string $reason = '', int $user_id = 0,
		string $subject = '', string $request_id = ''): bool {
		global $wpdb;
		$table = $wpdb->prefix . 'kklidi_mem_login_audit';
		$request_id = $request_id !== '' ? $request_id : self::request_id();
		$event = substr(sanitize_key($event), 0, 40);
		$subject_digest = $subject === '' ? null : self::digest(strtolower($subject));
		$inserted = $wpdb->query($wpdb->prepare(
			"INSERT INTO {$table}
			(user_id, occurred_at_utc, event_type, result, reason_code, request_id, subject_digest, network_digest)
			VALUES (NULLIF(%d, 0), %s, %s, %s, %s, %s, NULLIF(%s, ''), %s)",
			$user_id,
			current_time('mysql', true),
			$event,
			substr(sanitize_key($result), 0, 20),
			substr(sanitize_key($reason), 0, 80),
			$request_id,
			$subject_digest ?: '',
			self::digest(\KKLIDI\Members\Security\RateLimiter::network())
		));
		return $inserted !== false || self::is_duplicate($table, $request_id, $event);
	}

	public static function cleanup(): void {
		global $wpdb;
		$table = $wpdb->prefix . 'kklidi_mem_login_audit';
		$success_days = max(1, (int) get_option('kklidi_members_audit_success_days', 30));
		$security_days = max($success_days, (int) get_option('kklidi_members_audit_security_days', 90));
		$success_cutoff = gmdate('Y-m-d H:i:s', time() - $success_days * DAY_IN_SECONDS);
		$security_cutoff = gmdate('Y-m-d H:i:s', time() - $security_days * DAY_IN_SECONDS);
		$wpdb->query($wpdb->prepare("DELETE FROM {$table} WHERE result = 'success' AND occurred_at_utc < %s LIMIT 500", $success_cutoff));
		$wpdb->query($wpdb->prepare("DELETE FROM {$table} WHERE result <> 'success' AND occurred_at_utc < %s LIMIT 500", $security_cutoff));
	}

	public static function request_id(): string {
		if (self::$request_id === '') {
			self::$request_id = wp_generate_uuid4();
		}
		return self::$request_id;
	}

	private static function digest(string $value): string {
		return hash_hmac('sha256', $value, wp_salt('secure_auth'));
	}

	private static function is_duplicate(string $table, string $request_id, string $event): bool {
		global $wpdb;
		return (int) $wpdb->get_var($wpdb->prepare(
			"SELECT COUNT(*) FROM {$table} WHERE request_id = %s AND event_type = %s",
			$request_id,
			$event
		)) === 1;
	}
}
