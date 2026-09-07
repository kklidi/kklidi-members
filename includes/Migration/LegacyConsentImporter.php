<?php

namespace KKLIDI\Members\Migration;

if (!defined('ABSPATH')) {
	exit;
}

final class LegacyConsentImporter {
	private const FIELDS = array(
		'service' => 'policy_service',
		'privacy' => 'policy_privacy',
	);

	public static function dry_run(int $after_user_id = 0, int $limit = 100): array {
		return self::batch($after_user_id, $limit, false);
	}

	public static function import(int $after_user_id = 0, int $limit = 100): array {
		return self::batch($after_user_id, $limit, true);
	}

	private static function batch(int $after_user_id, int $limit, bool $write): array {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Repository.php';
		global $wpdb;
		$limit = max(1, min(500, $limit));
		$user_ids = $wpdb->get_col($wpdb->prepare(
			"SELECT ID FROM {$wpdb->users} WHERE ID > %d ORDER BY ID ASC LIMIT %d",
			max(0, $after_user_id),
			$limit
		));
		$result = array('scanned' => count($user_ids), 'eligible' => 0, 'imported' => 0,
			'duplicates' => 0, 'errors' => 0, 'next_cursor' => $after_user_id);
		$table = $wpdb->prefix . 'kklidi_mem_consents';
		foreach ($user_ids as $user_id) {
			$user_id = (int) $user_id;
			$result['next_cursor'] = $user_id;
			foreach (self::FIELDS as $type => $meta_key) {
				if ((string) get_user_meta($user_id, $meta_key, true) !== 'agree') {
					continue;
				}
				$result['eligible']++;
				$request_id = self::request_id($user_id, $type);
				$exists = (int) $wpdb->get_var($wpdb->prepare(
					"SELECT COUNT(*) FROM {$table} WHERE request_id=%s AND consent_type=%s AND action='legacy_import'",
					$request_id,
					$type
				));
				if ($exists) {
					$result['duplicates']++;
					continue;
				}
				if (!$write) {
					continue;
				}
				if (\KKLIDI\Members\Consent\Repository::append(
					$user_id, $type, 'legacy_import', 'legacy_wpmembers', $request_id
				)) {
					$result['imported']++;
				} else {
					$result['errors']++;
				}
			}
		}
		return $result;
	}

	private static function request_id(int $user_id, string $type): string {
		$site = strtolower(untrailingslashit(home_url('/')));
		$hex = md5('legacy:' . $site . ':' . $user_id . ':' . $type);
		// A deterministic RFC 4122-shaped v5 identifier for the schema's UUID key.
		$hex[12] = '5';
		$hex[16] = dechex((hexdec($hex[16]) & 0x3) | 0x8);
		return substr($hex, 0, 8) . '-' . substr($hex, 8, 4) . '-' . substr($hex, 12, 4)
			. '-' . substr($hex, 16, 4) . '-' . substr($hex, 20, 12);
	}
}
