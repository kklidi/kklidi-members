<?php
// CLI-only setup for the post-activation MVP behavior contracts.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || realpath(dirname($root)) !== realpath(dirname(getenv('KKH_DATA')))
    || @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) {
    exit('Invalid harness root.');
}
require $root . '/wp-load.php';
require_once WP_PLUGIN_DIR . '/kklidi-members/includes/Consent/Documents.php';
use KKLIDI\Members\Consent\Documents;

$documents = array(
    'service' => Documents::save('service', 'mvp-service-v1', '<p>합성 서비스 약관</p>'),
    'privacy' => Documents::save('privacy', 'mvp-privacy-v1', '<p>합성 개인정보 처리방침</p>'),
    'marketing' => Documents::save('marketing', 'mvp-marketing-v1', '<p>합성 선택 마케팅 동의</p>'),
);
foreach ($documents as $document) {
    if (is_wp_error($document)) { exit('Document setup failed.'); }
}
update_option('users_can_register', 1);
update_option('kklidi_members_registration_enabled', '1', false);
update_option('kklidi_members_own_login_url', '1', false);
update_option('kklidi_members_own_register_url', '1', false);
echo json_encode(array('required_ready' => Documents::required_ready(),
    'registration_enabled' => get_option('kklidi_members_registration_enabled'),
    'users_can_register' => (bool) get_option('users_can_register')));
