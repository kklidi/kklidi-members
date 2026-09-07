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
			'withdrawal' => add_query_arg('kklidi_members_withdrawal', '1', home_url('/')),
			'logout' => add_query_arg('kklidi_members_logout', '1', home_url('/')),
		);
		require KKLIDI_MEMBERS_DIR . 'templates/account.php';
		exit;
	}
}
