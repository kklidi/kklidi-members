<?php

namespace KKLIDI\Members\Consent;

if (!defined('ABSPATH')) {
	exit;
}

final class Documents {
	private const TYPES = array('service', 'privacy', 'marketing');

	public static function current(string $type): array {
		if (!in_array($type, self::TYPES, true)) {
			return array();
		}
		$value = get_option('kklidi_members_document_' . $type, array());
		return is_array($value) && !empty($value['version']) && !empty($value['hash'])
			? $value : array();
	}

	public static function save(string $type, string $version, string $content) {
		$snapshot = self::preview($type, $version, $content);
		if (is_wp_error($snapshot)) {
			return $snapshot;
		}

		$name = '_kklidi_members_document_snapshot_' . $type . '_' . $snapshot['hash'];
		$existing = get_option($name, null);
		if ($existing !== null && (!is_array($existing)
			|| ($existing['type'] ?? '') !== $snapshot['type']
			|| ($existing['version'] ?? '') !== $snapshot['version']
			|| ($existing['hash'] ?? '') !== $snapshot['hash']
			|| ($existing['content'] ?? '') !== $snapshot['content'])) {
			return new \WP_Error('document_snapshot_conflict', __('The saved content differs for the same document hash.', 'kklidi-members'));
		}
		if ($existing === null && !add_option($name, $snapshot, '', 'no')) {
			return new \WP_Error('document_snapshot_failed', __('We could not save the document.', 'kklidi-members'));
		}
		if (is_array($existing)) {
			$snapshot = $existing;
		}
		if (!update_option('kklidi_members_document_' . $type, $snapshot, false)
			&& get_option('kklidi_members_document_' . $type) !== $snapshot) {
			return new \WP_Error('document_pointer_failed', __('We could not set the current document.', 'kklidi-members'));
		}
		return $snapshot;
	}

	/**
	 * Build a sanitized immutable snapshot without writing it.
	 */
	public static function preview(string $type, string $version, string $content) {
		if (!in_array($type, self::TYPES, true)) {
			return new \WP_Error('invalid_document_type', __('This document type is not supported.', 'kklidi-members'));
		}
		$version = trim(sanitize_text_field($version));
		$content = trim(wp_kses_post($content));
		if ($version === '' || strlen($version) > 80 || $content === '') {
			return new \WP_Error('invalid_document', __('A document version and content are required.', 'kklidi-members'));
		}
		$hash = hash('sha256', str_replace(array("\r\n", "\r"), "\n", $content));
		$snapshot = array(
			'type' => $type,
			'version' => $version,
			'hash' => $hash,
			'content' => $content,
			'created_at_utc' => current_time('mysql', true),
		);
		return $snapshot;
	}

	/**
	 * Return a bounded list of published immutable snapshots for administrators.
	 */
	public static function history(string $type, int $limit = 20): array {
		if (!in_array($type, self::TYPES, true)) {
			return array();
		}
		global $wpdb;
		$limit = max(1, min(50, $limit));
		$prefix = '_kklidi_members_document_snapshot_' . $type . '_';
		$rows = $wpdb->get_results($wpdb->prepare(
			"SELECT option_value FROM {$wpdb->options} WHERE option_name LIKE %s ORDER BY option_id DESC LIMIT %d",
			$wpdb->esc_like($prefix) . '%',
			$limit
		), ARRAY_A);
		$history = array();
		foreach ($rows as $row) {
			$snapshot = maybe_unserialize($row['option_value'] ?? '');
			if (!is_array($snapshot) || ($snapshot['type'] ?? '') !== $type
				|| empty($snapshot['version']) || empty($snapshot['hash'])) {
				continue;
			}
			$history[] = $snapshot;
		}
		return $history;
	}

	public static function required_ready(): bool {
		return self::current('service') !== array() && self::current('privacy') !== array();
	}
}
