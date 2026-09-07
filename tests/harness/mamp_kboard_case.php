<?php
// CLI-only synthetic data; never accepts a different site or database.
if (PHP_SAPI !== 'cli') { exit(1); }
$sandbox_root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';
if (str_replace('\\', '/', (string) realpath($sandbox_root)) !== $sandbox_root) { exit(1); }
$fixture_action = $argv[1] ?? '';
$run_token = $argv[2] ?? '';
if (!preg_match('/^[a-f0-9]{12}$/', $run_token)
    || !in_array($fixture_action, array('setup', 'off', 'probe', 'cleanup'), true)) { exit(1); }
require $sandbox_root . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
if (untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox'
    || !class_exists('KBoard') || !class_exists('KBComment')) { exit(1); }
add_filter('pre_wp_mail', '__return_true');
$key = '_kklidi_members_kboard_case_' . $run_token;
$plugin = 'kklidi-members/kklidi-members.php';
global $wpdb;
$state = get_option($key, false);
if ($fixture_action === 'setup') {
    if ($state !== false) { exit(1); }
    $state = array('active' => is_plugin_active($plugin));
    add_option($key, $state, '', false);
    $user = wp_insert_user(array('user_login' => 'kboard_case_' . $run_token,
        'user_email' => $run_token . '@example.invalid', 'role' => 'subscriber',
        'user_pass' => wp_generate_password(40), 'display_name' => 'Synthetic board author'));
    if (is_wp_error($user)) { exit(1); }
    $state['user'] = (int) $user;
    update_option($key, $state, false);
    // Complete schema defaults avoid relying on MySQL non-strict mode.
    $insert = static function (string $suffix, array $values) use ($wpdb): int {
        $table = $wpdb->prefix . $suffix;
        $row = array();
        foreach ($wpdb->get_results("SHOW COLUMNS FROM `$table`") as $column) {
            if ($column->Extra === 'auto_increment') { continue; }
            $row[$column->Field] = strpos($column->Type, 'int') !== false ? 0 : '';
        }
        if (!$wpdb->insert($table, array_merge($row, $values))) { exit(1); }
        return (int) $wpdb->insert_id;
    };
    $state['board'] = $insert('kboard_board_setting', array('board_name' => 'Case ' . $run_token,
        'skin' => 'default', 'use_comment' => 'true', 'permission_read' => 'all',
        'permission_write' => 'author', 'page_rpp' => 10, 'created' => gmdate('YmdHis')));
    update_option($key, $state, false);
    $board = new KBoard($state['board']);
    $board->meta->comment_skin = 'default';
    $board->meta->permission_comment_write = 'author';
    $state['content'] = $insert('kboard_board_content', array('board_id' => $state['board'],
        'member_uid' => $user, 'member_display' => 'Synthetic author', 'title' => 'POST-' . $run_token,
        'content' => 'BODY-' . $run_token, 'date' => gmdate('YmdHis'), 'update' => gmdate('YmdHis'),
        'search' => '1', 'comment' => 1));
    update_option($key, $state, false);
    $state['comment'] = $insert('kboard_comments', array('content_uid' => $state['content'],
        'user_uid' => $user, 'user_display' => 'Synthetic author', 'content' => 'COMMENT-' . $run_token,
        'created' => gmdate('YmdHis')));
    update_option($key, $state, false);
    $page = wp_insert_post(array('post_type' => 'page', 'post_status' => 'publish',
        'post_title' => 'KBoard case ' . $run_token,
        'post_content' => '[kboard id="' . $state['board'] . '"]'), true);
    if (is_wp_error($page)) { exit(1); }
    $state['page'] = (int) $page;
    update_option($key, $state, false);
    echo wp_json_encode(array('page' => $page, 'content' => $state['content']));
    exit;
}
if (!is_array($state)) { exit(1); }
if ($fixture_action === 'off') {
    deactivate_plugins($plugin, true);
    echo wp_json_encode(array('active' => is_plugin_active($plugin)));
    exit;
}
if ($fixture_action === 'probe') {
    wp_set_current_user(0);
    $guest = new KBoard($state['board']);
    $guest_allowed = $guest->isWriter();
    wp_set_current_user($state['user']);
    $member = new KBoard($state['board']);
    echo wp_json_encode(array('guest_write' => $guest_allowed, 'member_write' => $member->isWriter(),
        'post_owner' => (int) $wpdb->get_var($wpdb->prepare("SELECT member_uid FROM {$wpdb->prefix}kboard_board_content WHERE uid=%d", $state['content'])) === $state['user'],
        'comment_owner' => (int) $wpdb->get_var($wpdb->prepare("SELECT user_uid FROM {$wpdb->prefix}kboard_comments WHERE uid=%d", $state['comment'])) === $state['user']));
    exit;
}
if (!empty($state['board'])) { (new KBoard($state['board']))->delete(); }
if (!empty($state['page'])) { wp_delete_post($state['page'], true); }
if (!empty($state['user'])) {
    require_once ABSPATH . 'wp-admin/includes/user.php';
    wp_delete_user($state['user']);
}
if ($state['active'] && !is_plugin_active($plugin)) {
    if (is_wp_error(activate_plugin($plugin))) { exit(1); }
}
$remaining = array(
    'board' => (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$wpdb->prefix}kboard_board_setting WHERE uid=%d", $state['board'] ?? 0)),
    'content' => (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$wpdb->prefix}kboard_board_content WHERE board_id=%d", $state['board'] ?? 0)),
    'comment' => (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$wpdb->prefix}kboard_comments WHERE content_uid=%d", $state['content'] ?? 0)),
    'user' => get_user_by('id', $state['user'] ?? 0) ? 1 : 0,
    'page' => get_post($state['page'] ?? 0) ? 1 : 0);
if (array_sum($remaining) !== 0) { echo wp_json_encode(array('cleanup_failed' => $remaining)); exit(1); }
delete_option($key);
echo wp_json_encode(array('remaining' => $remaining, 'members_restored' => is_plugin_active($plugin) === $state['active']));
