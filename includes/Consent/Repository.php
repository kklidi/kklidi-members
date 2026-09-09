<?php

namespace KKLIDI\Members\Consent;

if (!defined('ABSPATH')) {
	exit;
}

final class Repository {
	private const TYPES = array('service', 'privacy', 'marketing');
	private const ACTIONS = array('accept', 'withdraw', 'legacy_import');

	public static function append(int $user_id, string $type, string $action, string $source,
		string $request_id, array $document = array()): bool {
		global $wpdb;
		if ($user_id < 1 || !in_array($type, self::TYPES, true)
			|| !in_array($action, self::ACTIONS, true) || !wp_is_uuid($request_id)) {
			return false;
		}
		if ($action !== 'legacy_import' && (empty($document['version']) || empty($document['hash']))) {
			return false;
		}

		$table = $wpdb->prefix . 'kklidi_mem_consents';
		$version = $action === 'legacy_import' ? '' : substr((string) $document['version'], 0, 80);
		$hash = $action === 'legacy_import' ? '' : (string) $document['hash'];
		$occurred = $action === 'legacy_import' ? '' : current_time('mysql', true);
		$inserted = $wpdb->query($wpdb->prepare(
			"INSERT INTO {$table}
			(user_id, consent_type, document_version, document_hash, action, occurred_at_utc, recorded_at_utc, source, request_id)
			VALUES (%d, %s, NULLIF(%s, ''), NULLIF(%s, ''), %s, NULLIF(%s, ''), %s, %s, %s)",
			$user_id,
			$type,
			$version,
			$hash,
			$action,
			$occurred,
			current_time('mysql', true),
			substr(sanitize_key($source), 0, 40),
			$request_id
		));
		if ($inserted !== false) {
			return true;
		}
		return (int) $wpdb->get_var($wpdb->prepare(
			"SELECT COUNT(*) FROM {$table} WHERE request_id = %s AND consent_type = %s AND action = %s",
			$request_id,
			$type,
			$action
		)) === 1;
	}

	public static function has_current(int $user_id, string $type): bool {
		$document = Documents::current($type);
		if ($document === array()) {
			return false;
		}
		$latest = self::latest($user_id, $type);
		return $latest && $latest->action === 'accept'
			&& hash_equals((string) $document['hash'], (string) $latest->document_hash)
			&& (string) $document['version'] === (string) $latest->document_version;
	}

	public static function has_current_required(int $user_id): bool {
		return self::has_current($user_id, 'service') && self::has_current($user_id, 'privacy');
	}

	public static function latest(int $user_id, string $type) {
		global $wpdb;
		if (!in_array($type, self::TYPES, true)) {
			return null;
		}
		$table = $wpdb->prefix . 'kklidi_mem_consents';
		return $wpdb->get_row($wpdb->prepare(
			"SELECT consent_type, document_version, document_hash, action, recorded_at_utc
			 FROM {$table} WHERE user_id = %d AND consent_type = %s ORDER BY id DESC LIMIT 1",
			$user_id,
			$type
		));
	}
}
