<?php

namespace KKLIDI\Members\Admin;

if (!defined('ABSPATH')) {
	exit;
}

final class AdminController {
	private const SECTIONS = array('overview', 'documents', 'registration', 'notifications', 'withdrawals', 'audit');
	private static $document_preview = null;
	private static $consent_status_cache = array();

	public static function boot(): void {
		add_action('admin_menu', array(__CLASS__, 'menu'));
		add_action('admin_init', array(__CLASS__, 'register_registration_settings'));
		add_action('admin_init', array(__CLASS__, 'register_notification_settings'));
		add_action('admin_init', array(__CLASS__, 'handle_admin_request'));
		add_action('admin_enqueue_scripts', array(__CLASS__, 'enqueue_assets'));
		add_filter('option_page_capability_kklidi_members_notifications', array(
			'\KKLIDI\Members\Notifications\NotificationTemplates',
			'settings_capability',
		));
		add_filter('option_page_capability_kklidi_members_registration_fields', array(
			'\KKLIDI\Members\Registration\RegistrationFields',
			'settings_capability',
		));
		add_action('update_option_kklidi_members_registration_fields', array(
			'\KKLIDI\Members\Registration\RegistrationFields',
			'audit_update',
		), 10, 2);
		add_action('update_option_kklidi_members_notification_templates', array(
			'\KKLIDI\Members\Notifications\NotificationTemplates',
			'audit_update',
		), 10, 2);
		add_filter('manage_users_columns', array(__CLASS__, 'user_columns'));
		add_filter('manage_users_custom_column', array(__CLASS__, 'user_column_value'), 10, 3);
		add_action('restrict_manage_users', array(__CLASS__, 'user_filters'));
		add_action('pre_get_users', array(__CLASS__, 'filter_users_by_state'));
		add_action('pre_user_query', array(__CLASS__, 'filter_users_by_consent'));
	}

	public static function register_registration_settings(): void {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Registration/RegistrationFields.php';
		\KKLIDI\Members\Registration\RegistrationFields::register_settings();
	}

	public static function register_notification_settings(): void {
		require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/NotificationTemplates.php';
		\KKLIDI\Members\Notifications\NotificationTemplates::register_settings();
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
			$updated = self::review_withdrawal('disabled');
			self::redirect('withdrawals', $updated ? 'withdrawal_disabled' : 'withdrawal_not_updated');
		}
		if ($action === 'restore_withdrawal') {
			$updated = self::review_withdrawal('active');
			self::redirect('withdrawals', $updated ? 'withdrawal_restored' : 'withdrawal_not_updated');
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

	private static function review_withdrawal(string $target_state): bool {
		$user_id = isset($_POST['user_id']) ? absint($_POST['user_id']) : 0;
		$reason = isset($_POST['review_reason']) && is_string($_POST['review_reason'])
			? trim(sanitize_textarea_field(wp_unslash($_POST['review_reason']))) : '';
		if (!in_array($target_state, array('active', 'disabled'), true)
			|| $user_id < 1 || !get_userdata($user_id) || user_can($user_id, 'manage_options')
			|| \KKLIDI\Members\Security\AccountState::get($user_id) !== 'withdrawal_pending'
			|| ($target_state === 'active' && ($reason === '' || self::text_length($reason) > 500))
			|| !\KKLIDI\Members\Security\AccountState::transition($user_id, 'withdrawal_pending', $target_state)) {
			return false;
		}
		$request_id = wp_generate_uuid4();
		\KKLIDI\Members\Security\AccountState::revoke_access($user_id);
		$event = $target_state === 'active' ? 'withdrawal_restored' : 'withdrawal_disabled';
		$reason_code = $target_state === 'active' ? 'admin_restore' : 'admin_review';
		\KKLIDI\Members\Audit\Recorder::record($event, 'success', $reason_code, $user_id, $reason, $request_id);
		do_action('kklidi_members_account_state_changed', $user_id, 'withdrawal_pending', $target_state, $request_id);
		if ($target_state === 'disabled') {
			require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AccountMailer.php';
			\KKLIDI\Members\Notifications\AccountMailer::send('withdrawal_finalized', $user_id, $request_id);
		}
		return true;
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
			'registration' => __('Registration fields', 'kklidi-members'),
			'notifications' => __('Notifications', 'kklidi-members'),
			'withdrawals' => __('Withdrawals', 'kklidi-members'),
			'audit' => __('Audit', 'kklidi-members'),
		);
		$overview = array();
		$documents = array();
		$document_history = array();
		$queue = array();
		$audit_view = array();
		$quick_links = array();
		$route_urls = array();

		if ($section === 'overview') {
			$overview = self::overview();
			require_once KKLIDI_MEMBERS_DIR . 'includes/Core/Url.php';
			$quick_links = array(
				array('label' => __('Documents', 'kklidi-members'), 'description' => __('Publish and review the required account documents.', 'kklidi-members'), 'url' => self::page_url('documents')),
				array('label' => __('Registration fields', 'kklidi-members'), 'description' => __('Choose which approved profile fields appear during registration.', 'kklidi-members'), 'url' => self::page_url('registration')),
				array('label' => __('Notifications', 'kklidi-members'), 'description' => __('Edit the four approved account notice messages.', 'kklidi-members'), 'url' => self::page_url('notifications')),
				array('label' => __('Withdrawals', 'kklidi-members'), 'description' => __('Review pending withdrawal requests without deleting records.', 'kklidi-members'), 'url' => self::page_url('withdrawals')),
				array('label' => __('Audit', 'kklidi-members'), 'description' => __('Filter security and account events.', 'kklidi-members'), 'url' => self::page_url('audit')),
			);
			if (current_user_can('manage_options')) {
				$quick_links[] = array('label' => __('WordPress registration settings', 'kklidi-members'), 'description' => __('Public registration remains controlled by WordPress Core.', 'kklidi-members'), 'url' => admin_url('options-general.php#users_can_register'));
			}
			$route_urls = array(
				'login' => array(__('Login', 'kklidi-members'), \KKLIDI\Members\Core\Url::login()),
				'register' => array(__('Registration', 'kklidi-members'), \KKLIDI\Members\Core\Url::register()),
				'account' => array(__('Account', 'kklidi-members'), \KKLIDI\Members\Core\Url::account()),
				'profile' => array(__('Profile', 'kklidi-members'), \KKLIDI\Members\Core\Url::profile()),
				'password' => array(__('Change password', 'kklidi-members'), \KKLIDI\Members\Core\Url::password()),
				'password_reset' => array(__('Password reset', 'kklidi-members'), \KKLIDI\Members\Core\Url::passwordReset()),
				'consent' => array(__('Consent settings', 'kklidi-members'), \KKLIDI\Members\Core\Url::consent()),
				'withdrawal' => array(__('Withdrawal request', 'kklidi-members'), \KKLIDI\Members\Core\Url::withdrawal()),
				'logout' => array(__('Log out', 'kklidi-members'), \KKLIDI\Members\Core\Url::logout()),
			);
		} elseif ($section === 'documents') {
			require_once KKLIDI_MEMBERS_DIR . 'includes/Consent/Documents.php';
			foreach (array('service', 'privacy', 'marketing') as $type) {
				$documents[$type] = \KKLIDI\Members\Consent\Documents::current($type);
				$document_history[$type] = \KKLIDI\Members\Consent\Documents::history($type);
			}
		} elseif ($section === 'registration') {
			require_once KKLIDI_MEMBERS_DIR . 'includes/Registration/RegistrationFields.php';
		} elseif ($section === 'notifications') {
			require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/NotificationTemplates.php';
		} elseif ($section === 'withdrawals') {
			$queue = get_users(array(
				'meta_key' => '_kklidi_members_account_state',
				'meta_value' => 'withdrawal_pending',
				'number' => 50,
				'fields' => array('ID', 'display_name'),
			));
		} else {
			$audit_view = self::audit_view();
		}
		$document_preview = self::$document_preview;
		require KKLIDI_MEMBERS_DIR . 'templates/admin.php';
	}

	private static function audit_view(): array {
		global $wpdb;
		$table = $wpdb->prefix . 'kklidi_mem_login_audit';
		$events = self::audit_event_labels();
		$results = self::audit_result_labels();
		$filters = array(
			'event' => self::requested_filter('audit_event'),
			'result' => self::requested_filter('audit_result'),
			'date' => self::requested_text('audit_date'),
			'user_id' => isset($_GET['audit_user_id']) ? absint($_GET['audit_user_id']) : 0,
		);
		if (!isset($events[$filters['event']])) {
			$filters['event'] = '';
		}
		if (!isset($results[$filters['result']])) {
			$filters['result'] = '';
		}
		if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $filters['date'])) {
			$filters['date'] = '';
		} else {
			list($year, $month, $day) = array_map('intval', explode('-', $filters['date']));
			if (!checkdate($month, $day, $year)) {
				$filters['date'] = '';
			}
		}

		$where = array('1 = 1');
		$args = array();
		if ($filters['event'] !== '') {
			$where[] = 'event_type = %s';
			$args[] = $filters['event'];
		}
		if ($filters['result'] !== '') {
			$where[] = 'result = %s';
			$args[] = $filters['result'];
		}
		if ($filters['user_id'] > 0) {
			$where[] = 'user_id = %d';
			$args[] = $filters['user_id'];
		}
		if ($filters['date'] !== '') {
			$where[] = 'occurred_at_utc >= %s AND occurred_at_utc < %s';
			$args[] = $filters['date'] . ' 00:00:00';
			$args[] = gmdate('Y-m-d 00:00:00', strtotime($filters['date'] . ' +1 day'));
		}
		$where_sql = implode(' AND ', $where);
		$count_sql = "SELECT COUNT(*) FROM {$table} WHERE {$where_sql}";
		if ($args) {
			$count_sql = $wpdb->prepare($count_sql, $args);
		}
		$total = (int) $wpdb->get_var($count_sql);
		$per_page = 25;
		$pages = max(1, min(100, (int) ceil($total / $per_page)));
		$page = isset($_GET['paged']) ? absint($_GET['paged']) : 1;
		$page = max(1, min($pages, $page));
		$list_args = array_merge($args, array($per_page, ($page - 1) * $per_page));
		$list_sql = "SELECT id, user_id, occurred_at_utc, event_type, result, reason_code
			FROM {$table} WHERE {$where_sql} ORDER BY id DESC LIMIT %d OFFSET %d";
		$rows = $wpdb->get_results($wpdb->prepare($list_sql, $list_args));
		return array(
			'rows' => $rows,
			'filters' => $filters,
			'events' => $events,
			'results' => $results,
			'page' => $page,
			'pages' => $pages,
			'total' => $total,
			'success_days' => max(1, (int) get_option('kklidi_members_audit_success_days', 30)),
			'security_days' => max(1, (int) get_option('kklidi_members_audit_security_days', 90)),
		);
	}

	public static function audit_event_label(string $event): string {
		$labels = self::audit_event_labels();
		return $labels[$event] ?? $event;
	}

	public static function audit_result_label(string $result): string {
		$labels = self::audit_result_labels();
		return $labels[$result] ?? $result;
	}

	public static function audit_reason_label(string $reason): string {
		$labels = array(
			'core' => __('WordPress Core', 'kklidi-members'),
			'admin_settings' => __('Administrator updated notification messages', 'kklidi-members'),
			'admin_review' => __('Administrator confirmed access block', 'kklidi-members'),
			'admin_restore' => __('Administrator restored access with a reason', 'kklidi-members'),
			'wp_mail_accepted' => __('WordPress accepted the email for delivery', 'kklidi-members'),
			'wp_mail_failed' => __('WordPress rejected the email submission', 'kklidi-members'),
			'self' => __('Member request', 'kklidi-members'),
			'completed' => __('Completed', 'kklidi-members'),
			'user_request' => __('Member logout request', 'kklidi-members'),
		);
		return $labels[$reason] ?? $reason;
	}

	private static function audit_event_labels(): array {
		return array(
			'login' => __('Login', 'kklidi-members'),
			'logout' => __('Logout', 'kklidi-members'),
			'registration_success' => __('Registration completed', 'kklidi-members'),
			'registration_failed' => __('Registration failed', 'kklidi-members'),
			'profile_update' => __('Profile updated', 'kklidi-members'),
			'password_change' => __('Password changed', 'kklidi-members'),
			'consent_update' => __('Consent updated', 'kklidi-members'),
			'withdrawal_request' => __('Withdrawal requested', 'kklidi-members'),
			'withdrawal_restored' => __('Withdrawal restored', 'kklidi-members'),
			'withdrawal_disabled' => __('Withdrawal finalized', 'kklidi-members'),
			'mail_registration_completed' => __('Registration notice', 'kklidi-members'),
			'mail_password_changed' => __('Password-change notice', 'kklidi-members'),
			'mail_withdrawal_requested' => __('Withdrawal-request notice', 'kklidi-members'),
			'mail_withdrawal_finalized' => __('Withdrawal-finalized notice', 'kklidi-members'),
			'notification_settings_update' => __('Notification settings updated', 'kklidi-members'),
			'registration_fields_update' => __('Registration field settings updated', 'kklidi-members'),
		);
	}

	private static function audit_result_labels(): array {
		return array(
			'success' => __('Success', 'kklidi-members'),
			'failure' => __('Failure', 'kklidi-members'),
			'pending' => __('Pending', 'kklidi-members'),
		);
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
			array('key' => 'public_registration', 'label' => __('WordPress public registration', 'kklidi-members'), 'ready' => (bool) get_option('users_can_register'), 'detail' => get_option('users_can_register') ? __('Allowed by WordPress', 'kklidi-members') : __('Closed by WordPress', 'kklidi-members'), 'action_url' => current_user_can('manage_options') ? admin_url('options-general.php#users_can_register') : '', 'action_label' => __('Open WordPress settings', 'kklidi-members')),
			array('key' => 'required_documents', 'label' => __('Required documents', 'kklidi-members'), 'ready' => \KKLIDI\Members\Consent\Documents::required_ready(), 'detail' => \KKLIDI\Members\Consent\Documents::required_ready() ? __('Ready', 'kklidi-members') : __('Service terms or privacy policy is missing', 'kklidi-members'), 'action_url' => self::page_url('documents'), 'action_label' => __('Manage documents', 'kklidi-members')),
			array('key' => 'clean_route', 'label' => __('Clean route preflight', 'kklidi-members'), 'ready' => (bool) $preflight['ready'], 'detail' => $preflight['ready'] ? __('No page collisions found', 'kklidi-members') : sprintf(__('%d page collisions found', 'kklidi-members'), count($preflight['collisions'])), 'action_url' => self::page_url('documents'), 'action_label' => __('Review route settings', 'kklidi-members')),
			array('key' => 'url_ownership', 'label' => __('Members URL ownership', 'kklidi-members'), 'ready' => get_option('kklidi_members_own_login_url') === '1' || get_option('kklidi_members_own_register_url') === '1', 'detail' => sprintf(__('Login: %1$s / Registration: %2$s', 'kklidi-members'), get_option('kklidi_members_own_login_url') === '1' ? __('Owned', 'kklidi-members') : __('Core fallback', 'kklidi-members'), get_option('kklidi_members_own_register_url') === '1' ? __('Owned', 'kklidi-members') : __('Core fallback', 'kklidi-members')), 'action_url' => self::page_url('documents'), 'action_label' => __('Manage URL ownership', 'kklidi-members')),
			array('key' => 'members_tables', 'label' => __('Members tables', 'kklidi-members'), 'ready' => $tables_ready, 'detail' => $tables_ready ? __('Both owned tables are available', 'kklidi-members') : __('An owned table is missing', 'kklidi-members')),
			array('key' => 'cleanup_schedule', 'label' => __('Daily cleanup schedule', 'kklidi-members'), 'ready' => $cleanup !== false, 'detail' => $cleanup !== false ? sprintf(__('Next run: %s UTC', 'kklidi-members'), gmdate('Y-m-d H:i:s', (int) $cleanup)) : __('Cleanup is not scheduled', 'kklidi-members')),
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

	private static function requested_text(string $key): string {
		return isset($_GET[$key]) && is_string($_GET[$key])
			? sanitize_text_field(wp_unslash($_GET[$key])) : '';
	}

	private static function text_length(string $value): int {
		return function_exists('mb_strlen') ? mb_strlen($value, 'UTF-8') : strlen($value);
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
