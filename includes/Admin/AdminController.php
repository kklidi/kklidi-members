<?php

namespace KKLIDI\Members\Admin;

if (!defined('ABSPATH')) {
	exit;
}

final class AdminController {
	private const SECTIONS = array('overview', 'documents', 'withdrawals', 'audit');
	private static $document_preview = null;
	private static $consent_status_cache = array();

	public static function boot(): void {
		add_action('admin_menu', array(__CLASS__, 'menu'));
		add_action('admin_init', array(__CLASS__, 'handle_admin_request'));
		add_action('admin_enqueue_scripts', array(__CLASS__, 'enqueue_assets'));
		add_filter('manage_users_columns', array(__CLASS__, 'user_columns'));
		add_filter('manage_users_custom_column', array(__CLASS__, 'user_column_value'), 10, 3);
		add_action('restrict_manage_users', array(__CLASS__, 'user_filters'));
		add_action('pre_get_users', array(__CLASS__, 'filter_users_by_state'));
		add_action('pre_user_query', array(__CLASS__, 'filter_users_by_consent'));
	}

	public static function enqueue_assets(string $hook_suffix): void {
		if ($hook_suffix !== 'users_page_kklidi-members') {
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
		add_users_page(
			__('KKLIDI Members', 'kklidi-members'),
			__('KKLIDI Members', 'kklidi-members'),
			'manage_kklidi_members',
			'kklidi-members',
			array(__CLASS__, 'render')
		);
	}

	public static function handle_admin_request(): void {
		global $pagenow;
		if (strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'GET'
			&& $pagenow === 'tools.php'
			&& isset($_GET['page']) && sanitize_key(wp_unslash($_GET['page'])) === 'kklidi-members'
			&& current_user_can('manage_kklidi_members')) {
			wp_safe_redirect(self::page_url(self::requested_section()));
			exit;
		}

		if (!isset($_POST['kklidi_members_admin_action']) || !current_user_can('manage_kklidi_members')) {
			return;
		}
		check_admin_referer('kklidi_members_admin', '_kklidi_members_admin_nonce');
		$action = sanitize_key(wp_unslash($_POST['kklidi_members_admin_action']));
		if ($action === 'save_url_settings') {
			self::save_url_settings();
			self::redirect('documents', 'saved');
		}
		if ($action === 'publish_document') {
			self::publish_document();
			self::redirect('documents', 'saved');
		}
		if ($action === 'preview_document') {
			self::preview_document();
			return;
		}
		if ($action === 'finalize_withdrawal') {
			self::finalize_withdrawal();
			self::redirect('withdrawals', 'withdrawal_updated');
		}
	}

	private static function save_url_settings(): void {
		delete_option('kklidi_members_registration_enabled');
		update_option('kklidi_members_own_login_url', isset($_POST['own_login_url']) ? '1' : '0', false);
		update_option('kklidi_members_own_register_url', isset($_POST['own_register_url']) ? '1' : '0', false);
	}

	private static function publish_document(): void {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
		$type = isset($_POST['document_type']) && is_string($_POST['document_type'])
			? sanitize_key(wp_unslash($_POST['document_type'])) : '';
		$version_key = $type . '_version';
		$content_key = $type . '_content';
		$version = isset($_POST[$version_key]) && is_string($_POST[$version_key])
			? sanitize_text_field(wp_unslash($_POST[$version_key])) : '';
		$content = isset($_POST[$content_key]) && is_string($_POST[$content_key])
			? wp_unslash($_POST[$content_key]) : '';
		$result = \KKLIDI\Members\Consent\Documents::save($type, $version, $content);
		if (is_wp_error($result)) {
			wp_die(esc_html($result->get_error_message()));
		}
	}

	private static function preview_document(): void {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
		$type = isset($_POST['document_type']) && is_string($_POST['document_type'])
			? sanitize_key(wp_unslash($_POST['document_type'])) : '';
		$version_key = $type . '_version';
		$content_key = $type . '_content';
		$version = isset($_POST[$version_key]) && is_string($_POST[$version_key])
			? sanitize_text_field(wp_unslash($_POST[$version_key])) : '';
		$content = isset($_POST[$content_key]) && is_string($_POST[$content_key])
			? wp_unslash($_POST[$content_key]) : '';
		self::$document_preview = array(
			'type' => $type,
			'result' => \KKLIDI\Members\Consent\Documents::preview($type, $version, $content),
		);
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
		require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AccountMailer.php';
		\KKLIDI\Members\Notifications\AccountMailer::send('withdrawal_finalized', $user_id, $request_id);
	}

	public static function user_columns(array $columns): array {
		if (!current_user_can('manage_kklidi_members')) {
			return $columns;
		}
		$columns['kklidi_members_account_state'] = __('Account state', 'kklidi-members');
		$columns['kklidi_members_required_consent'] = __('Required consent', 'kklidi-members');
		return $columns;
	}

	public static function user_column_value(string $value, string $column, int $user_id): string {
		if (!current_user_can('manage_kklidi_members')) {
			return $value;
		}
		if ($column === 'kklidi_members_account_state') {
			return esc_html(self::account_state_label(\KKLIDI\Members\Security\AccountState::get($user_id)));
		}
		if ($column === 'kklidi_members_required_consent') {
			if (!isset(self::$consent_status_cache[$user_id])) {
				require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
				require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Repository.php';
				self::$consent_status_cache[$user_id] = \KKLIDI\Members\Consent\Repository::has_current_required($user_id);
			}
			return esc_html(self::$consent_status_cache[$user_id]
				? __('Complete', 'kklidi-members') : __('Incomplete', 'kklidi-members'));
		}
		return $value;
	}

	public static function user_filters(string $which): void {
		if ($which !== 'top' || !current_user_can('manage_kklidi_members')) {
			return;
		}
		$state = self::requested_filter('kklidi_members_account_state');
		$consent = self::requested_filter('kklidi_members_required_consent');
		?>
		<label class="screen-reader-text" for="kklidi-members-account-state-filter"><?php esc_html_e('Filter by account state', 'kklidi-members'); ?></label>
		<select id="kklidi-members-account-state-filter" name="kklidi_members_account_state">
			<option value=""><?php esc_html_e('All account states', 'kklidi-members'); ?></option>
			<?php foreach (array('active', 'registration_pending', 'withdrawal_pending', 'disabled') as $item) : ?>
				<option value="<?php echo esc_attr($item); ?>" <?php selected($state, $item); ?>><?php echo esc_html(self::account_state_label($item)); ?></option>
			<?php endforeach; ?>
		</select>
		<label class="screen-reader-text" for="kklidi-members-consent-filter"><?php esc_html_e('Filter by required consent', 'kklidi-members'); ?></label>
		<select id="kklidi-members-consent-filter" name="kklidi_members_required_consent">
			<option value=""><?php esc_html_e('All consent states', 'kklidi-members'); ?></option>
			<option value="complete" <?php selected($consent, 'complete'); ?>><?php esc_html_e('Required consent complete', 'kklidi-members'); ?></option>
			<option value="incomplete" <?php selected($consent, 'incomplete'); ?>><?php esc_html_e('Required consent incomplete', 'kklidi-members'); ?></option>
		</select>
		<?php
	}

	public static function filter_users_by_state(\WP_User_Query $query): void {
		global $pagenow;
		if (!is_admin() || $pagenow !== 'users.php' || !current_user_can('manage_kklidi_members')) {
			return;
		}
		$state = self::requested_filter('kklidi_members_account_state');
		if (!in_array($state, array('active', 'registration_pending', 'withdrawal_pending', 'disabled'), true)) {
			return;
		}
		if ($state === 'active') {
			$query->set('meta_query', array(
				'relation' => 'OR',
				array('key' => '_kklidi_members_account_state', 'compare' => 'NOT EXISTS'),
				array('key' => '_kklidi_members_account_state', 'value' => 'active'),
			));
			return;
		}
		$query->set('meta_key', '_kklidi_members_account_state');
		$query->set('meta_value', $state);
	}

	public static function filter_users_by_consent(\WP_User_Query $query): void {
		global $pagenow;
		if (!is_admin() || $pagenow !== 'users.php' || !current_user_can('manage_kklidi_members')) {
			return;
		}
		$status = self::requested_filter('kklidi_members_required_consent');
		if (!in_array($status, array('complete', 'incomplete'), true)) {
			return;
		}
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
		$service = \KKLIDI\Members\Consent\Documents::current('service');
		$privacy = \KKLIDI\Members\Consent\Documents::current('privacy');
		if ($service === array() || $privacy === array()) {
			if ($status === 'complete') {
				$query->query_where .= ' AND 1 = 0';
			}
			return;
		}
		global $wpdb;
		$table = $wpdb->prefix . 'kklidi_mem_consents';
		$exists = array();
		foreach (array('service' => $service, 'privacy' => $privacy) as $type => $document) {
			$exists[] = $wpdb->prepare(
				"EXISTS (SELECT 1 FROM {$table} kmc WHERE kmc.user_id = {$wpdb->users}.ID AND kmc.consent_type = %s AND kmc.document_version = %s AND kmc.document_hash = %s AND kmc.action = 'accept')",
				$type,
				(string) $document['version'],
				(string) $document['hash']
			);
		}
		$complete = '(' . implode(' AND ', $exists) . ')';
		$query->query_where .= $status === 'complete' ? ' AND ' . $complete : ' AND NOT ' . $complete;
	}

	public static function render(): void {
		if (!current_user_can('manage_kklidi_members')) {
			wp_die(esc_html__('You do not have permission to access this page.', 'kklidi-members'));
		}
		$section = self::requested_section();
		$sections = array(
			'overview' => __('Overview', 'kklidi-members'),
			'documents' => __('Documents', 'kklidi-members'),
			'withdrawals' => __('Withdrawals', 'kklidi-members'),
			'audit' => __('Audit', 'kklidi-members'),
		);
		$overview = array();
		$documents = array();
		$document_history = array();
		$queue = array();
		$audit_rows = array();

		if ($section === 'overview') {
			$overview = self::overview();
		} elseif ($section === 'documents') {
			require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
			foreach (array('service', 'privacy', 'marketing') as $type) {
				$documents[$type] = \KKLIDI\Members\Consent\Documents::current($type);
				$document_history[$type] = \KKLIDI\Members\Consent\Documents::history($type);
			}
		} elseif ($section === 'withdrawals') {
			$queue = get_users(array(
				'meta_key' => '_kklidi_members_account_state',
				'meta_value' => 'withdrawal_pending',
				'number' => 50,
				'fields' => array('ID', 'display_name'),
			));
		} else {
			global $wpdb;
			$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
			$audit_rows = $wpdb->get_results("SELECT id, user_id, occurred_at_utc, event_type, result, reason_code FROM {$audit_table} ORDER BY id DESC LIMIT 50");
		}
		$document_preview = self::$document_preview;
		require KKLIDI_MEMBERS_DIR . 'templates/admin.php';
	}

	private static function overview(): array {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
		require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';
		global $wpdb;
		$preflight = \KKLIDI\Members\Core\Url::cleanRoutePreflight();
		$tables = array($wpdb->prefix . 'kklidi_mem_login_audit', $wpdb->prefix . 'kklidi_mem_consents');
		$tables_ready = true;
		foreach ($tables as $table) {
			$tables_ready = $tables_ready && $wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s', $wpdb->esc_like($table))) === $table;
		}
		$cleanup = wp_next_scheduled('kklidi_members_daily_cleanup');
		return array(
			array('label' => __('WordPress public registration', 'kklidi-members'), 'ready' => (bool) get_option('users_can_register'), 'detail' => get_option('users_can_register') ? __('Allowed by WordPress', 'kklidi-members') : __('Closed by WordPress', 'kklidi-members')),
			array('label' => __('Required documents', 'kklidi-members'), 'ready' => \KKLIDI\Members\Consent\Documents::required_ready(), 'detail' => \KKLIDI\Members\Consent\Documents::required_ready() ? __('Ready', 'kklidi-members') : __('Service terms or privacy policy is missing', 'kklidi-members')),
			array('label' => __('Clean route preflight', 'kklidi-members'), 'ready' => (bool) $preflight['ready'], 'detail' => $preflight['ready'] ? __('No page collisions found', 'kklidi-members') : sprintf(__('%d page collisions found', 'kklidi-members'), count($preflight['collisions']))),
			array('label' => __('Members URL ownership', 'kklidi-members'), 'ready' => get_option('kklidi_members_own_login_url') === '1' || get_option('kklidi_members_own_register_url') === '1', 'detail' => sprintf(__('Login: %1$s / Registration: %2$s', 'kklidi-members'), get_option('kklidi_members_own_login_url') === '1' ? __('Owned', 'kklidi-members') : __('Core fallback', 'kklidi-members'), get_option('kklidi_members_own_register_url') === '1' ? __('Owned', 'kklidi-members') : __('Core fallback', 'kklidi-members'))),
			array('label' => __('Members tables', 'kklidi-members'), 'ready' => $tables_ready, 'detail' => $tables_ready ? __('Both owned tables are available', 'kklidi-members') : __('An owned table is missing', 'kklidi-members')),
			array('label' => __('Daily cleanup schedule', 'kklidi-members'), 'ready' => $cleanup !== false, 'detail' => $cleanup !== false ? sprintf(__('Next run: %s UTC', 'kklidi-members'), gmdate('Y-m-d H:i:s', (int) $cleanup)) : __('Cleanup is not scheduled', 'kklidi-members')),
		);
	}

	private static function account_state_label(string $state): string {
		$labels = array(
			'active' => __('Active', 'kklidi-members'),
			'registration_pending' => __('Registration pending', 'kklidi-members'),
			'withdrawal_pending' => __('Withdrawal pending', 'kklidi-members'),
			'disabled' => __('Disabled', 'kklidi-members'),
		);
		return $labels[$state] ?? __('Unknown', 'kklidi-members');
	}

	private static function requested_filter(string $key): string {
		return isset($_GET[$key]) && is_string($_GET[$key])
			? sanitize_key(wp_unslash($_GET[$key])) : '';
	}

	private static function requested_section(): string {
		$section = isset($_REQUEST['section']) && is_string($_REQUEST['section'])
			? sanitize_key(wp_unslash($_REQUEST['section'])) : 'overview';
		return in_array($section, self::SECTIONS, true) ? $section : 'overview';
	}

	private static function page_url(string $section): string {
		return add_query_arg(array('page' => 'kklidi-members', 'section' => $section), admin_url('users.php'));
	}

	private static function redirect(string $section, string $notice): void {
		wp_safe_redirect(add_query_arg('notice', $notice, self::page_url($section)));
		exit;
	}
}
