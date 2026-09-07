<?php

namespace KKLIDI\Members\Admin;

if (!defined('ABSPATH')) {
	exit;
}

final class AdminController {
	public static function boot(): void {
		add_action('admin_menu', array(__CLASS__, 'menu'));
		add_action('admin_init', array(__CLASS__, 'handle_post'));
		add_action('admin_enqueue_scripts', array(__CLASS__, 'enqueue_assets'));
	}

	/**
	 * Keep Members admin styling off every other wp-admin screen.
	 */
	public static function enqueue_assets(string $hook_suffix): void {
		if ($hook_suffix !== 'tools_page_kklidi-members') {
			return;
		}

		wp_enqueue_style(
			'kklidi-members-admin',
			plugins_url('assets/css/admin.css', KKLIDI_MEMBERS_FILE),
			array(),
			KKLIDI_MEMBERS_VERSION
		);
	}

	public static function menu(): void {
		add_management_page(
			__('KKLIDI Members', 'kklidi-members'),
			__('KKLIDI Members', 'kklidi-members'),
			'manage_kklidi_members',
			'kklidi-members',
			array(__CLASS__, 'render')
		);
	}

	public static function handle_post(): void {
		if (!isset($_POST['kklidi_members_admin_action']) || !current_user_can('manage_kklidi_members')) {
			return;
		}
		check_admin_referer('kklidi_members_admin', '_kklidi_members_admin_nonce');
		$action = sanitize_key(wp_unslash($_POST['kklidi_members_admin_action']));
		if ($action === 'save_settings') {
			self::save_settings();
		} elseif ($action === 'finalize_withdrawal') {
			self::finalize_withdrawal();
		}
		wp_safe_redirect(add_query_arg(array('page' => 'kklidi-members', 'updated' => '1'), admin_url('tools.php')));
		exit;
	}

	private static function save_settings(): void {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
		foreach (array('service', 'privacy', 'marketing') as $type) {
			$version_key = $type . '_version';
			$content_key = $type . '_content';
			$version = isset($_POST[$version_key]) && is_string($_POST[$version_key])
				? sanitize_text_field(wp_unslash($_POST[$version_key])) : '';
			$content = isset($_POST[$content_key]) && is_string($_POST[$content_key])
				? wp_unslash($_POST[$content_key]) : '';
			if ($version !== '' || trim($content) !== '') {
				$result = \KKLIDI\Members\Consent\Documents::save($type, $version, $content);
				if (is_wp_error($result)) {
					wp_die(esc_html($result->get_error_message()));
				}
			}
		}

		$registration = isset($_POST['registration_enabled'])
			&& (bool) get_option('users_can_register', false)
			&& \KKLIDI\Members\Consent\Documents::required_ready();
		update_option('kklidi_members_registration_enabled', $registration ? '1' : '0', false);
		update_option('kklidi_members_own_login_url', isset($_POST['own_login_url']) ? '1' : '0', false);
		update_option('kklidi_members_own_register_url', isset($_POST['own_register_url']) ? '1' : '0', false);
	}

	private static function finalize_withdrawal(): void {
		$user_id = isset($_POST['user_id']) ? absint($_POST['user_id']) : 0;
		if ($user_id < 1 || user_can($user_id, 'manage_options')
			|| !\KKLIDI\Members\Security\AccountState::transition($user_id, 'withdrawal_pending', 'disabled')) {
			return;
		}
		$request_id = wp_generate_uuid4();
		\KKLIDI\Members\Security\AccountState::revoke_access($user_id);
		\KKLIDI\Members\Audit\Recorder::record('withdrawal_disabled', 'success', 'admin_review', $user_id, '', $request_id);
		do_action('kklidi_members_account_state_changed', $user_id, 'withdrawal_pending', 'disabled', $request_id);
	}

	public static function render(): void {
		if (!current_user_can('manage_kklidi_members')) {
			wp_die(esc_html__('You do not have permission to access this page.', 'kklidi-members'));
		}
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
		global $wpdb;
		$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
		$audit_rows = $wpdb->get_results("SELECT id, user_id, occurred_at_utc, event_type, result, reason_code
			FROM {$audit_table} ORDER BY id DESC LIMIT 50");
		$queue = get_users(array(
			'meta_key' => '_kklidi_members_account_state',
			'meta_value' => 'withdrawal_pending',
			'number' => 50,
			'fields' => array('ID', 'display_name'),
		));
		$documents = array(
			'service' => \KKLIDI\Members\Consent\Documents::current('service'),
			'privacy' => \KKLIDI\Members\Consent\Documents::current('privacy'),
			'marketing' => \KKLIDI\Members\Consent\Documents::current('marketing'),
		);
		require KKLIDI_MEMBERS_DIR . 'templates/admin.php';
	}
}
