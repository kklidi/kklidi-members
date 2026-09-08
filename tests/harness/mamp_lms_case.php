<?php
/**
 * CLI-only AUTH-LMS-001 fixture for the dedicated MAMP sandbox.
 *
 * This fixture can target only the synthetic kklidi-members MAMP site.
 */

if (PHP_SAPI !== 'cli') {
	exit(1);
}

$sandbox_root = 'C:/MAMP/htdocs/kklidi-members-mamp-sandbox';
$resolved_root = realpath($sandbox_root);
if ($resolved_root === false
	|| str_replace('\\', '/', $resolved_root) !== $sandbox_root
	|| !is_file($resolved_root . '/wp-load.php')) {
	exit('The dedicated MAMP sandbox is unavailable.');
}

$fixture_action = $argv[1] ?? '';
$run_token = $argv[2] ?? '';
if (!in_array($fixture_action, array('setup', 'probe', 'student-cookie', 'outsider-cookie', 'members-off', 'members-on', 'cleanup'), true)
	|| !preg_match('/^[a-f0-9]{12}$/', $run_token)) {
	exit('Invalid AUTH-LMS-001 fixture command.');
}

define('WP_USE_THEMES', false);
require $resolved_root . '/wp-load.php';

if (untrailingslashit(home_url('/')) !== 'http://localhost:8888/kklidi-members-mamp-sandbox') {
	exit('Refusing a non-sandbox WordPress site.');
}
if (!defined('KKLIDI_LMS_VERSION') || !class_exists('KKLIDI_LMS_Enrollments')
	|| !class_exists('KKLIDI_LMS_WooCommerce') || !class_exists('WooCommerce')) {
	exit('KKLIDI LMS is not active.');
}
require_once ABSPATH . 'wp-admin/includes/plugin.php';

$state_key = '_kklidi_members_lms_case_' . $run_token;
$members_plugin = 'kklidi-members/kklidi-members.php';
$login_prefix = 'lms_case_' . $run_token . '_';

$option_snapshot = static function (string $name): array {
	$missing = new stdClass();
	$value = get_option($name, $missing);
	return array('exists' => $value !== $missing, 'value' => $value !== $missing ? $value : null);
};

$restore_option = static function (string $name, array $snapshot): void {
	if (!empty($snapshot['exists'])) {
		update_option($name, $snapshot['value'], false);
	} else {
		delete_option($name);
	}
};

$save_state = static function (array $state) use ($state_key): void {
	update_option($state_key, $state, false);
};

if ($fixture_action === 'setup') {
	if (get_option($state_key, false) !== false
		|| username_exists($login_prefix . 'student')
		|| username_exists($login_prefix . 'outsider')
		|| username_exists($login_prefix . 'instructor')) {
		exit('Fixture token already exists.');
	}

	$state = array(
		'run_token' => $run_token,
		'user_ids' => array('student' => 0, 'outsider' => 0, 'instructor' => 0),
		'course_id' => 0,
		'lesson_id' => 0,
		'product_id' => 0,
		'order_id' => 0,
		'enrollment_id' => 0,
		'progress_id' => 0,
		'certificate_id' => 0,
		'question_id' => 0,
		'members_was_active' => is_plugin_active($members_plugin),
		'options' => array(
			'kklidi_members_own_login_url' => $option_snapshot('kklidi_members_own_login_url'),
		),
	);
	add_option($state_key, $state, '', false);
	update_option('kklidi_members_own_login_url', '1', false);

	foreach (array(
		'student' => 'AUTH-LMS-001 Student',
		'outsider' => 'AUTH-LMS-001 Outsider',
		'instructor' => 'AUTH-LMS-001 Instructor',
	) as $role_key => $display_name) {
		$login = $login_prefix . $role_key;
		$user_id = wp_insert_user(array(
			'user_login' => $login,
			'user_email' => $login . '@example.invalid',
			'user_pass' => wp_generate_password(32, true, true),
			'display_name' => $display_name,
			'role' => 'subscriber',
		));
		if (is_wp_error($user_id)) {
			exit('Synthetic LMS user creation failed.');
		}
		$state['user_ids'][$role_key] = (int) $user_id;
		$save_state($state);
	}

	$course_id = wp_insert_post(array(
		'post_type' => 'kklidi_lms_course',
		'post_status' => 'publish',
		'post_title' => 'AUTH-LMS-001 ' . $run_token,
		'post_content' => 'Synthetic LMS contract fixture.',
	), true);
	if (is_wp_error($course_id)) {
		exit('Synthetic LMS course creation failed.');
	}
	$state['course_id'] = (int) $course_id;
	$save_state($state);
	update_post_meta($course_id, '_kklidi_members_lms_test_run', $run_token);
	update_post_meta($course_id, KKLIDI_LMS_Meta_Keys::COURSE_INSTRUCTOR_USER_ID, $state['user_ids']['instructor']);
	update_post_meta($course_id, KKLIDI_LMS_Meta_Keys::COURSE_CERT_ENABLED, 'yes');
	update_post_meta($course_id, KKLIDI_LMS_Meta_Keys::COURSE_CERT_THRESHOLD, 100);

	$lesson_id = wp_insert_post(array(
		'post_type' => 'kklidi_lms_lesson',
		'post_status' => 'publish',
		'post_title' => 'AUTH-LMS-001 Lesson ' . $run_token,
		'post_content' => 'Synthetic LMS lesson fixture.',
	), true);
	if (is_wp_error($lesson_id)) {
		exit('Synthetic LMS lesson creation failed.');
	}
	$state['lesson_id'] = (int) $lesson_id;
	$save_state($state);
	update_post_meta($lesson_id, '_kklidi_members_lms_test_run', $run_token);
	update_post_meta($lesson_id, KKLIDI_LMS_Meta_Keys::LESSON_COURSE_ID, $course_id);
	KKLIDI_LMS_Post_Types::clear_lesson_cache();

	$product = new WC_Product_Simple();
	$product->set_name('AUTH-LMS-001 Product ' . $run_token);
	$product->set_status('publish');
	$product->set_regular_price('1000');
	$product->set_virtual(true);
	$product_id = $product->save();
	if (!$product_id) {
		exit('Synthetic LMS product creation failed.');
	}
	$state['product_id'] = (int) $product_id;
	$save_state($state);
	update_post_meta($product_id, '_kklidi_members_lms_test_run', $run_token);
	update_post_meta($product_id, KKLIDI_LMS_Meta_Keys::PRODUCT_COURSE_IDS, array($course_id));
	update_post_meta($product_id, KKLIDI_LMS_Meta_Keys::PRODUCT_ACCESS_TYPE, 'unlimited');
	KKLIDI_LMS_Product_Course_Map::clear_cache();

	$order = wc_create_order(array(
		'customer_id' => $state['user_ids']['student'],
		'created_via' => 'auth-lms-001',
	));
	if (is_wp_error($order)) {
		exit('Synthetic LMS order creation failed.');
	}
	$state['order_id'] = (int) $order->get_id();
	$save_state($state);
	$item_id = $order->add_product($product, 1);
	$item = $order->get_item($item_id);
	if (!$item instanceof WC_Order_Item_Product) {
		exit('Synthetic LMS order item creation failed.');
	}
	KKLIDI_LMS_WooCommerce::capture_order_item_entitlement(
		$item,
		'auth-lms-001',
		array('product_id' => $product_id, 'variation_id' => 0),
		$order
	);
	$item->save();
	$order->calculate_totals();
	$order->set_status('completed');
	$order->update_meta_data('_kklidi_members_lms_test_run', $run_token);
	$order->save();

	$first_reconcile = KKLIDI_LMS_WooCommerce::reconcile_order($state['order_id']);
	$enrollment = KKLIDI_LMS_Enrollments::get_by_order(
		$state['user_ids']['student'],
		$course_id,
		$state['order_id']
	);
	if (!$enrollment || $first_reconcile['failed'] !== 0) {
		exit('Synthetic LMS Woo entitlement creation failed.');
	}
	$state['enrollment_id'] = (int) $enrollment->id;
	$second_reconcile = KKLIDI_LMS_WooCommerce::reconcile_order($state['order_id']);
	$state['reconcile'] = array(
		'first' => $first_reconcile,
		'second' => $second_reconcile,
		'count_by_order' => KKLIDI_LMS_Enrollments::count_by_order($state['order_id']),
	);
	$save_state($state);

	if (!KKLIDI_LMS_Progress::record_lesson(
		$state['user_ids']['student'],
		$lesson_id,
		100,
		180,
		300,
		true,
		true
	)) {
		exit('Synthetic LMS progress creation failed.');
	}
	global $wpdb;
	$state['progress_id'] = (int) $wpdb->get_var($wpdb->prepare(
		'SELECT id FROM ' . kklidi_lms_table('progress') . ' WHERE user_id = %d AND lesson_id = %d',
		$state['user_ids']['student'],
		$lesson_id
	));
	$save_state($state);

	$certificate = KKLIDI_LMS_Certificates::maybe_issue(
		$state['user_ids']['student'],
		$course_id,
		$state['enrollment_id'],
		'AUTH-LMS-001'
	);
	if (!$certificate || empty($certificate->id)) {
		exit('Synthetic LMS certificate creation failed.');
	}
	$state['certificate_id'] = (int) $certificate->id;
	$save_state($state);

	$mail_attempts = 0;
	add_filter('pre_wp_mail', static function () use (&$mail_attempts) {
		$mail_attempts++;
		return true;
	}, PHP_INT_MAX);
	$question_id = KKLIDI_LMS_Private_Questions::create(
		$state['user_ids']['student'],
		$course_id,
		$lesson_id,
		'AUTH-LMS-001 ' . $run_token,
		'Synthetic private question.',
		array()
	);
	if (is_wp_error($question_id) || !$question_id) {
		exit('Synthetic LMS question creation failed.');
	}
	$state['question_id'] = (int) $question_id;
	$state['mail_attempts_sunk'] = $mail_attempts;
	$save_state($state);

	echo wp_json_encode(array(
		'run_token' => $run_token,
		'user_ids' => $state['user_ids'],
		'course_id' => $state['course_id'],
		'lesson_id' => $state['lesson_id'],
		'product_id' => $state['product_id'],
		'order_id' => $state['order_id'],
		'enrollment_id' => $state['enrollment_id'],
		'progress_id' => $state['progress_id'],
		'certificate_id' => $state['certificate_id'],
		'question_id' => $state['question_id'],
		'classroom_url' => KKLIDI_LMS_Frontend_Utils::classroom_url(),
		'course_url' => get_permalink($state['course_id']),
		'lesson_url' => get_permalink($state['lesson_id']),
		'reconcile' => $state['reconcile'],
	), JSON_UNESCAPED_SLASHES);
	exit;
}

$state = get_option($state_key, false);
if (!is_array($state) || ($state['run_token'] ?? '') !== $run_token) {
	exit('Fixture state is unavailable.');
}

if ($fixture_action === 'student-cookie' || $fixture_action === 'outsider-cookie') {
	$role_key = $fixture_action === 'student-cookie' ? 'student' : 'outsider';
	$user_id = (int) ($state['user_ids'][$role_key] ?? 0);
	$expiration = time() + (15 * MINUTE_IN_SECONDS);
	$manager = WP_Session_Tokens::get_instance($user_id);
	$token = $manager->create($expiration);
	$fingerprint = hash('sha256', 'auth-lms-001|' . $run_token . '|' . $role_key);
	if (function_exists('kklidi_dl_register_device')
		&& !kklidi_dl_has_registered_device($user_id, $fingerprint)
		&& !kklidi_dl_register_device($user_id, $fingerprint)) {
		exit('Synthetic device registration failed.');
	}
	echo wp_json_encode(array(
		'cookies' => array(
			array(
				'name' => LOGGED_IN_COOKIE,
				'value' => wp_generate_auth_cookie($user_id, $expiration, 'logged_in', $token),
			),
			array('name' => 'kklidi_dl_fp', 'value' => $fingerprint),
			array(
				'name' => function_exists('kklidi_dl_fingerprint_sig_cookie_name') ? kklidi_dl_fingerprint_sig_cookie_name() : '',
				'value' => function_exists('kklidi_dl_sign_fingerprint') ? kklidi_dl_sign_fingerprint($user_id, $fingerprint) : '',
			),
		),
		'expires' => $expiration,
	));
	exit;
}

if ($fixture_action === 'members-off') {
	deactivate_plugins($members_plugin, true);
	echo wp_json_encode(array(
		'members_active' => is_plugin_active($members_plugin),
		'lms_active' => defined('KKLIDI_LMS_VERSION'),
		'student_access' => KKLIDI_LMS_Enrollments::can_access((int) $state['user_ids']['student'], (int) $state['course_id']),
		'outsider_access' => KKLIDI_LMS_Enrollments::can_access((int) $state['user_ids']['outsider'], (int) $state['course_id']),
	), JSON_UNESCAPED_SLASHES);
	exit;
}

if ($fixture_action === 'members-on') {
	$activated = activate_plugin($members_plugin);
	if (is_wp_error($activated)) {
		exit('Members activation failed.');
	}
	echo wp_json_encode(array('members_active' => is_plugin_active($members_plugin)));
	exit;
}

if ($fixture_action === 'probe') {
	global $wpdb;
	$student_id = (int) $state['user_ids']['student'];
	$outsider_id = (int) $state['user_ids']['outsider'];
	$course_id = (int) $state['course_id'];
	$lesson_id = (int) $state['lesson_id'];
	$enrollment = KKLIDI_LMS_Enrollments::get($student_id, $course_id);
	$order = wc_get_order((int) $state['order_id']);
	$progress = $wpdb->get_row($wpdb->prepare(
		'SELECT * FROM ' . kklidi_lms_table('progress') . ' WHERE id = %d',
		(int) $state['progress_id']
	));
	$certificate = KKLIDI_LMS_Certificates::get_for_user_course($student_id, $course_id);
	$question = KKLIDI_LMS_Private_Questions::get((int) $state['question_id']);

	wp_set_current_user($student_id);
	$student_courses_html = do_shortcode('[kklidi_lms_my_courses]');
	$_GET['kklidi_lms_classroom_tab'] = 'profile';
	$profile_html = do_shortcode('[kklidi_lms_my_classroom]');
	unset($_GET['kklidi_lms_classroom_tab']);
	wp_set_current_user($outsider_id);
	$outsider_courses_html = do_shortcode('[kklidi_lms_my_courses]');
	wp_set_current_user(0);

	echo wp_json_encode(array(
		'wordpress_user_id' => get_user_by('id', $student_id) ? $student_id : 0,
		'enrollment_user_id' => $enrollment ? (int) $enrollment->user_id : 0,
		'enrollment_course_id' => $enrollment ? (int) $enrollment->course_id : 0,
		'enrollment_order_id' => $enrollment ? (int) $enrollment->order_id : 0,
		'enrollment_source' => $enrollment ? (string) $enrollment->source : '',
		'order_user_id' => $order ? (int) $order->get_user_id() : 0,
		'order_enrollment_count' => KKLIDI_LMS_Enrollments::count_by_order((int) $state['order_id']),
		'progress_user_id' => $progress ? (int) $progress->user_id : 0,
		'progress_course_id' => $progress ? (int) $progress->course_id : 0,
		'progress_lesson_id' => $progress ? (int) $progress->lesson_id : 0,
		'progress_percent' => KKLIDI_LMS_Progress::percent($student_id, $course_id),
		'certificate_user_id' => $certificate ? (int) $certificate->user_id : 0,
		'certificate_course_id' => $certificate ? (int) $certificate->course_id : 0,
		'question_student_user_id' => $question ? (int) $question->student_user_id : 0,
		'question_course_id' => $question ? (int) $question->course_id : 0,
		'student_access' => KKLIDI_LMS_Enrollments::can_access($student_id, $course_id),
		'outsider_access' => KKLIDI_LMS_Enrollments::can_access($outsider_id, $course_id),
		'student_can_view_question' => $question ? KKLIDI_LMS_Private_Questions::can_view($question, $student_id) : false,
		'outsider_can_view_question' => $question ? KKLIDI_LMS_Private_Questions::can_view($question, $outsider_id) : true,
		'student_course_visible' => strpos($student_courses_html, 'AUTH-LMS-001 ' . $run_token) !== false,
		'outsider_course_hidden' => strpos($outsider_courses_html, 'AUTH-LMS-001 ' . $run_token) === false,
		'login_uses_members' => strpos(wp_login_url(KKLIDI_LMS_Frontend_Utils::classroom_url()), 'kklidi_members_login=1') !== false,
		'direct_lms_profile_form_present' => strpos($profile_html, 'kklidi-lms-classroom-profile-form') !== false,
		'members_style_on_lms' => wp_style_is('kklidi-members-frontend', 'enqueued'),
		'mail_attempts_sunk' => (int) ($state['mail_attempts_sunk'] ?? 0),
		'members_active' => is_plugin_active($members_plugin),
	), JSON_UNESCAPED_SLASHES);
	exit;
}

global $wpdb;
$question_id = (int) ($state['question_id'] ?? 0);
if ($question_id) {
	$wpdb->delete(kklidi_lms_table('private_question_attachments'), array('question_id' => $question_id), array('%d'));
	$wpdb->delete(kklidi_lms_table('private_question_messages'), array('question_id' => $question_id), array('%d'));
	$wpdb->delete(kklidi_lms_table('private_questions'), array('id' => $question_id), array('%d'));
}
foreach (array(
	'certificates' => 'certificate_id',
	'progress' => 'progress_id',
	'enrollments' => 'enrollment_id',
) as $table_key => $state_key_name) {
	$record_id = (int) ($state[$state_key_name] ?? 0);
	if ($record_id) {
		$wpdb->delete(kklidi_lms_table($table_key), array('id' => $record_id), array('%d'));
	}
}
$order = wc_get_order((int) ($state['order_id'] ?? 0));
if ($order) {
	$order->delete(true);
}
$product = wc_get_product((int) ($state['product_id'] ?? 0));
if ($product) {
	$product->delete(true);
}
$course_id = (int) ($state['course_id'] ?? 0);
$synthetic_user_ids = array_values(array_filter(array_map('intval', $state['user_ids'] ?? array())));
if ($course_id && $synthetic_user_ids) {
	$placeholders = implode(',', array_fill(0, count($synthetic_user_ids), '%d'));
	$wpdb->query($wpdb->prepare(
		'DELETE FROM ' . kklidi_lms_table('activity') . " WHERE course_id = %d AND user_id IN ($placeholders)",
		array_merge(array($course_id), $synthetic_user_ids)
	));
}
$allow_owned_hard_delete = static function ($allowed, WP_Post $post) use ($run_token): bool {
	return get_post_meta($post->ID, '_kklidi_members_lms_test_run', true) === $run_token
		? true
		: (bool) $allowed;
};
add_filter('kklidi_lms_allow_hard_delete', $allow_owned_hard_delete, PHP_INT_MAX, 2);
foreach (array('lesson_id', 'course_id') as $post_key) {
	if (!isset($cleanup_previous_user_id)) {
		$cleanup_previous_user_id = get_current_user_id();
		$cleanup_admin_ids = get_users(array(
			'role' => 'administrator',
			'number' => 1,
			'fields' => 'ids',
		));
		if ($cleanup_admin_ids === array()) {
			exit('A sandbox administrator is required for LMS fixture cleanup.');
		}
		wp_set_current_user((int) $cleanup_admin_ids[0]);
	}
	$post_id = (int) ($state[$post_key] ?? 0);
	if ($post_id) {
		wp_delete_post($post_id, true);
	}
}
remove_filter('kklidi_lms_allow_hard_delete', $allow_owned_hard_delete, PHP_INT_MAX);
if (isset($cleanup_previous_user_id)) {
	wp_set_current_user((int) $cleanup_previous_user_id);
}
require_once ABSPATH . 'wp-admin/includes/user.php';
if (defined('KKLIDI_DL_TABLE') && $synthetic_user_ids) {
	$device_placeholders = implode(',', array_fill(0, count($synthetic_user_ids), '%d'));
	$wpdb->query($wpdb->prepare(
		'DELETE FROM ' . $wpdb->prefix . KKLIDI_DL_TABLE . " WHERE user_id IN ($device_placeholders)",
		$synthetic_user_ids
	));
}
foreach ($synthetic_user_ids as $user_id) {
	wp_delete_user($user_id);
}
foreach ($state['options'] as $name => $snapshot) {
	$restore_option($name, $snapshot);
}
if (!empty($state['members_was_active']) && !is_plugin_active($members_plugin)) {
	$activated = activate_plugin($members_plugin);
	if (is_wp_error($activated)) {
		exit('Members restoration failed.');
	}
}
KKLIDI_LMS_Enrollments::clear_all_cache();
KKLIDI_LMS_Post_Types::clear_lesson_cache();
delete_option($state_key);
$owned_postmeta_remaining = (int) $wpdb->get_var($wpdb->prepare(
	"SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE meta_key = %s AND meta_value = %s",
	'_kklidi_members_lms_test_run',
	$run_token
));
$device_remaining = 0;
if (defined('KKLIDI_DL_TABLE') && $synthetic_user_ids) {
	$device_placeholders = implode(',', array_fill(0, count($synthetic_user_ids), '%d'));
	$device_remaining = (int) $wpdb->get_var($wpdb->prepare(
		'SELECT COUNT(*) FROM ' . $wpdb->prefix . KKLIDI_DL_TABLE . " WHERE user_id IN ($device_placeholders)",
		$synthetic_user_ids
	));
}

echo wp_json_encode(array(
	'cleaned' => true,
	'run_token' => $run_token,
	'users_remaining' => count(array_filter($synthetic_user_ids, static function (int $user_id): bool {
		return (bool) get_user_by('id', $user_id);
	})),
	'course_remaining' => $course_id ? (bool) get_post($course_id) : false,
	'lesson_remaining' => !empty($state['lesson_id']) ? (bool) get_post((int) $state['lesson_id']) : false,
	'owned_postmeta_remaining' => $owned_postmeta_remaining,
	'device_remaining' => $device_remaining,
	'state_remaining' => get_option($state_key, false) !== false,
	'members_active' => is_plugin_active($members_plugin),
), JSON_UNESCAPED_SLASHES);
