<?php

namespace KKLIDI\Members\Frontend;

if (!defined('ABSPATH')) {
	exit;
}

final class AccountController {
	public static function handle(): void {
		nocache_headers();
		header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
		require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';
		$user = wp_get_current_user();
		$urls = array(
			'login' => \KKLIDI\Members\Core\Url::login(\KKLIDI\Members\Core\Url::account()),
			'register' => \KKLIDI\Members\Core\Url::register(),
			'profile' => \KKLIDI\Members\Core\Url::profile(),
			'password' => \KKLIDI\Members\Core\Url::password(),
			'consent' => \KKLIDI\Members\Core\Url::consent(),
			'withdrawal' => \KKLIDI\Members\Core\Url::withdrawal(),
			'logout' => \KKLIDI\Members\Core\Url::logout(),
		);
		$notice = isset($_GET['withdrawal']) && is_string($_GET['withdrawal'])
			&& sanitize_key(wp_unslash($_GET['withdrawal'])) === 'requested'
			? __('Your withdrawal request was submitted. Access is blocked while it is reviewed.', 'kklidi-members')
			: '';
		$integration_links = $user->exists() ? self::integration_links((int) $user->ID) : array();
		require KKLIDI_MEMBERS_DIR . 'templates/account.php';
		exit;
	}

	/**
	 * Let optional plugins provide links while keeping their data and APIs outside Members.
	 */
	private static function integration_links(int $user_id): array {
		$registered = apply_filters('kklidi_members_account_navigation_links', array(), $user_id);
		if (!is_array($registered)) {
			return array();
		}

		$links = array();
		foreach ($registered as $key => $link) {
			if (!is_array($link) || !isset($link['label'], $link['url'])
				|| !is_string($link['label']) || !is_string($link['url'])) {
				continue;
			}
			$key = is_string($key) ? sanitize_key($key) : '';
			$label = sanitize_text_field($link['label']);
			$url = \KKLIDI\Members\Core\Url::optionalLocal($link['url']);
			if ($key === '' || $label === '' || $url === '') {
				continue;
			}
			$priority = isset($link['priority']) && is_scalar($link['priority'])
				? max(-100, min(100, (int) $link['priority'])) : 10;
			$links[$key] = array(
				'label' => $label,
				'url' => $url,
				'priority' => $priority,
			);
		}
		uasort($links, static function (array $left, array $right): int {
			return $left['priority'] <=> $right['priority'];
		});
		return $links;
	}
}
