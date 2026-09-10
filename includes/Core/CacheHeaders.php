<?php

namespace KKLIDI\Members\Core;

if (!defined('ABSPATH')) {
	exit;
}

/**
 * Mark Members-owned pages as non-cacheable across common proxy stacks.
 *
 * This is route-scoped. It does not change caching for the rest of WordPress
 * or for optional consumer plugins.
 */
final class CacheHeaders {
	private static $marked = false;

	public static function mark_route(): void {
		if (self::$marked) {
			return;
		}

		self::$marked = true;
		foreach (array('DONOTCACHEPAGE', 'DONOTCACHEOBJECT', 'DONOTMINIFY', 'DONOTCDN') as $constant) {
			if (!defined($constant)) {
				define($constant, true);
			}
		}

		self::send_headers();
		// LiteSpeed exposes this action so applications can opt a response out
		// even when the generic Cache-Control header is rewritten by the server.
		do_action('litespeed_control_set_nocache', 'kklidi-members-route');
		add_action('litespeed_control_finalize', array(__CLASS__, 'finalize'), 999);
	}

	public static function finalize($esi_id = false): void {
		if (!self::$marked || $esi_id !== false) {
			return;
		}

		self::send_headers();
		do_action('litespeed_control_set_nocache', 'kklidi-members-route-finalize');
	}

	private static function send_headers(): void {
		if (function_exists('nocache_headers')) {
			nocache_headers();
		}
		if (headers_sent()) {
			return;
		}

		header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private', true);
		header('Pragma: no-cache', true);
		header('Expires: Wed, 11 Jan 1984 05:00:00 GMT', true);
		// These are understood by common reverse proxies/CDNs. Unknown headers
		// are harmless and are ignored by stacks that do not implement them.
		header('Surrogate-Control: no-store', true);
		header('CDN-Cache-Control: no-store', true);
		header('Cloudflare-CDN-Cache-Control: no-store', true);
		header('X-LiteSpeed-Cache-Control: no-cache', true);
	}
}
