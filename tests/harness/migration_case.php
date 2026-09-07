<?php
// Execute the legacy consent migration contract only in the owned fixture.
if (PHP_SAPI !== 'cli') { exit(1); }
$root = getenv('KKH_ROOT');
if (!$root || @file_get_contents(dirname($root) . '/owner') !== getenv('KKH_RUN')) { exit('Invalid root.'); }
require $root . '/wp-load.php';
require_once WP_PLUGIN_DIR . '/kklidi-members/includes/Migration/LegacyConsentImporter.php';
use KKLIDI\Members\Migration\LegacyConsentImporter;

$users = get_users(array('role' => 'subscriber', 'orderby' => 'ID', 'order' => 'ASC', 'number' => 2));
if (count($users) !== 2) { exit('Fixture subscriber count changed.'); }
update_user_meta($users[0]->ID, 'policy_service', 'agree');
update_user_meta($users[0]->ID, 'policy_privacy', '');
update_user_meta($users[1]->ID, 'policy_service', 'agree');
update_user_meta($users[1]->ID, 'policy_privacy', 'agree');
$before_ids = get_users(array('fields' => 'ID', 'orderby' => 'ID', 'order' => 'ASC'));
global $wpdb;
$table = $wpdb->prefix . 'kklidi_mem_consents';
$before_rows = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table}");
$dry = LegacyConsentImporter::dry_run(0, 100);
$after_dry_rows = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table}");
$first = LegacyConsentImporter::import(0, 100);
$after_first_rows = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table}");
$second = LegacyConsentImporter::import(0, 100);
$after_second_rows = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table}");
$legacy_nulls = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table} WHERE action='legacy_import' AND document_version IS NULL AND document_hash IS NULL AND occurred_at_utc IS NULL");
echo wp_json_encode(array(
    'dry_eligible' => $dry['eligible'], 'dry_writes' => $after_dry_rows - $before_rows,
    'first_imported' => $first['imported'], 'first_writes' => $after_first_rows - $after_dry_rows,
    'second_imported' => $second['imported'], 'second_duplicates' => $second['duplicates'],
    'second_writes' => $after_second_rows - $after_first_rows,
    'legacy_null_rows' => $legacy_nulls,
    'ids_unchanged' => $before_ids === get_users(array('fields' => 'ID', 'orderby' => 'ID', 'order' => 'ASC')),
    'source_meta_unchanged' => get_user_meta($users[0]->ID, 'policy_service', true) === 'agree'
        && get_user_meta($users[0]->ID, 'policy_privacy', true) === ''
        && get_user_meta($users[1]->ID, 'policy_service', true) === 'agree'
        && get_user_meta($users[1]->ID, 'policy_privacy', true) === 'agree',
));
