<?php
// CLI-only state probe/mutator for the owned synthetic fixture.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || realpath(dirname($root)) !== realpath(dirname(getenv('KKH_DATA')))
    || @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) {
    exit('Invalid harness root.');
}
require $root . '/wp-load.php';
global $wpdb;
$action = $argv[1] ?? 'summary';
$email = getenv('KKH_MVP_EMAIL') ?: '';
$user = $email !== '' ? get_user_by('email', $email) : false;

if ($action === 'set-fixture-state') {
    $target = get_user_by('email', $argv[2] ?? '');
    $state = $argv[3] ?? '';
    if (!$target || !in_array($state, array('active', 'registration_pending', 'withdrawal_pending', 'disabled'), true)) {
        exit('Invalid state mutation.');
    }
    if ($state === 'active') {
        delete_user_meta($target->ID, '_kklidi_members_account_state');
    } else {
        update_user_meta($target->ID, '_kklidi_members_account_state', $state);
    }
    echo json_encode(array('user_id' => (int) $target->ID, 'state' => $state));
    exit;
}
if ($action === 'set-user-locale') {
    if (!$user || !isset($argv[2]) || !in_array($argv[2], array('en_US', 'ko_KR'), true)) {
        exit('Invalid synthetic user locale.');
    }
    update_user_meta($user->ID, 'locale', sanitize_text_field($argv[2]));
    echo wp_json_encode(array('user_id' => (int) $user->ID, 'locale' => get_user_locale($user)));
    exit;
}
if ($action === 'translation-check') {
    $catalog = WP_PLUGIN_DIR . '/kklidi-members/languages/kklidi-members-ko_KR.mo';
    echo wp_json_encode(array(
        'locale' => get_locale(),
        'determined_locale' => determine_locale(),
        'catalog_exists' => file_exists($catalog),
        'registration_subject' => sprintf(__('[%s] Registration complete', 'kklidi-members'), get_bloginfo('name')),
    ));
    exit;
}
if ($action === 'expire-audit') {
    $table = $wpdb->prefix . 'kklidi_mem_login_audit';
    $wpdb->query("UPDATE {$table} SET occurred_at_utc = '2000-01-01 00:00:00'");
    do_action('kklidi_members_daily_cleanup');
}
if ($action === 'replay-registration-notification') {
    if (!$user) { exit('Missing synthetic notification user.'); }
    $request_id = (string) get_user_meta($user->ID, '_kklidi_members_registration_request_id', true);
    require_once KKLIDI_MEMBERS_DIR . 'includes/Notifications/AccountMailer.php';
    echo wp_json_encode(array(
        'sent' => \KKLIDI\Members\Notifications\AccountMailer::send(
            'registration_completed',
            (int) $user->ID,
            $request_id
        ),
    ));
    exit;
}

$consent_table = $wpdb->prefix . 'kklidi_mem_consents';
$audit_table = $wpdb->prefix . 'kklidi_mem_login_audit';
$audit_rows = $wpdb->get_results("SELECT event_type, result, reason_code, subject_digest, network_digest FROM {$audit_table} ORDER BY id ASC", ARRAY_A);
$serialized_audit = wp_json_encode($audit_rows);
$summary = array(
    'users_count' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->users}"),
    'consent_rows' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$consent_table}"),
    'audit_rows' => count($audit_rows),
    'audit_events' => array_values(array_map(static fn($row) => $row['event_type'], $audit_rows)),
    'mail_audit' => array_values(array_filter($audit_rows, static function ($row) {
        return str_starts_with($row['event_type'], 'mail_');
    })),
    'audit_contains_raw_email' => $email !== '' && stripos($serialized_audit, $email) !== false,
    'audit_contains_raw_ip' => stripos($serialized_audit, '127.0.0.1') !== false,
    'rate_option_count' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name LIKE '\\_kklidi\\_members\\_rate\\_%'"),
);
if ($user) {
    $summary['user'] = array(
        'id' => (int) $user->ID,
        'login_is_private' => str_starts_with($user->user_login, 'member_'),
        'email_matches' => strtolower($user->user_email) === strtolower($email),
        'roles' => array_values($user->roles),
        'state' => (string) get_user_meta($user->ID, '_kklidi_members_account_state', true),
        'email_state' => (string) get_user_meta($user->ID, '_kklidi_members_email_state', true),
        'phone' => (string) get_user_meta($user->ID, 'billing_phone', true),
        'service_consents' => (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$consent_table} WHERE user_id=%d AND consent_type='service'", $user->ID)),
        'privacy_consents' => (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$consent_table} WHERE user_id=%d AND consent_type='privacy'", $user->ID)),
        'marketing_actions' => $wpdb->get_col($wpdb->prepare("SELECT action FROM {$consent_table} WHERE user_id=%d AND consent_type='marketing' ORDER BY id", $user->ID)),
        'old_password_valid' => wp_check_password(getenv('KKH_USER_PASSWORD'), $user->user_pass, $user->ID),
        'new_password_valid' => wp_check_password(getenv('KKH_NEW_PASSWORD'), $user->user_pass, $user->ID),
    );
}
echo json_encode($summary, JSON_UNESCAPED_UNICODE);
