<?php
/**
 * Read-only structural audit for the fixed ns_0727 reference site.
 *
 * This script does not bootstrap WordPress or print credentials/content. It opens a
 * read-only transaction and reports only plugin names, page routing metadata,
 * shortcode names, and menu visibility metadata needed for D06 ownership review.
 */

if (PHP_SAPI !== 'cli') {
	exit(1);
}

$root = 'C:/MAMP/htdocs/ns_0727';
$config = $root . '/wp-config.php';
if (str_replace('\\', '/', (string) realpath($root)) !== $root || !is_file($config)) {
	exit('Fixed reference site unavailable.');
}

$source = (string) file_get_contents($config);
$read_define = static function (string $name) use ($source): string {
	$pattern = "/define\\(\\s*['\"]" . preg_quote($name, '/') . "['\"]\\s*,\\s*['\"]([^'\"]*)['\"]\\s*\\)/";
	if (!preg_match($pattern, $source, $matches)) {
		exit('Unsupported reference configuration.');
	}
	return $matches[1];
};
if (!preg_match('/\\$table_prefix\\s*=\\s*[\'\"]([A-Za-z0-9_]+)[\'\"]\\s*;/', $source, $prefix_match)) {
	exit('Unsupported reference table prefix.');
}

$db = new mysqli($read_define('DB_HOST'), $read_define('DB_USER'), $read_define('DB_PASSWORD'), $read_define('DB_NAME'));
if ($db->connect_errno) {
	exit('Reference database unavailable.');
}
$db->set_charset('utf8mb4');
$db->query('SET SESSION TRANSACTION READ ONLY');
$db->begin_transaction();
$prefix = $prefix_match[1];

$query = static function (mysqli $db, string $sql): array {
	$result = $db->query($sql);
	if (!$result) {
		exit('Reference query failed.');
	}
	return $result->fetch_all(MYSQLI_ASSOC);
};

$option_rows = $query($db, "SELECT option_name, option_value FROM {$prefix}options WHERE option_name IN ('active_plugins','stylesheet','template')");
$options = array_column($option_rows, 'option_value', 'option_name');
$active = isset($options['active_plugins']) ? unserialize($options['active_plugins'], array('allowed_classes' => false)) : array();
$active_slugs = array_values(array_map(static fn(string $plugin): string => strtok($plugin, '/'), is_array($active) ? $active : array()));

$page_ids = array(2640, 10601, 10603, 10987, 11278);
$pages = $query($db, "SELECT ID, post_title, post_name, post_type, post_status, post_parent, post_content FROM {$prefix}posts WHERE ID IN (2640,10601,10603,10987,11278) ORDER BY ID");
$page_meta = $query($db, "SELECT post_id, meta_key, meta_value FROM {$prefix}postmeta WHERE post_id IN (2640,10601,10603,10987,11278) AND (meta_key LIKE 'cosmosfarm_members_page_restriction%' OR meta_key IN ('_wp_page_template')) ORDER BY post_id, meta_key");
$meta_by_page = array_fill_keys($page_ids, array());
foreach ($page_meta as $row) {
	$value = $row['meta_value'];
	$decoded = @unserialize($value, array('allowed_classes' => false));
	$meta_by_page[(int) $row['post_id']][$row['meta_key']] = $decoded !== false || $value === 'b:0;' ? $decoded : $value;
}
$safe_pages = array();
foreach ($pages as $page) {
	preg_match_all('/\\[([A-Za-z0-9_-]+)/', $page['post_content'], $shortcode_matches);
	$safe_pages[] = array(
		'id' => (int) $page['ID'],
		'title' => $page['post_title'],
		'slug' => $page['post_name'],
		'type' => $page['post_type'],
		'status' => $page['post_status'],
		'parent' => (int) $page['post_parent'],
		'shortcodes' => array_values(array_unique($shortcode_matches[1])),
		'meta' => $meta_by_page[(int) $page['ID']],
	);
}

$menu_items = $query($db, "SELECT p.ID, p.post_title, p.post_status, pm.meta_key, pm.meta_value FROM {$prefix}posts p JOIN {$prefix}postmeta pm ON pm.post_id=p.ID WHERE p.ID IN (9298,10608,10609) AND (pm.meta_key LIKE '_menu_item_%' OR pm.meta_key LIKE '%wpmem%') ORDER BY p.ID, pm.meta_key");
$safe_menu_items = array();
foreach ($menu_items as $row) {
	$id = (int) $row['ID'];
	if (!isset($safe_menu_items[$id])) {
		$safe_menu_items[$id] = array('id' => $id, 'title' => $row['post_title'], 'status' => $row['post_status'], 'meta' => array());
	}
	$value = $row['meta_value'];
	if ($row['meta_key'] === '_menu_item_url') {
		$parts = parse_url($value);
		$value = isset($parts['path']) ? $parts['path'] : '';
	}
	$safe_menu_items[$id]['meta'][$row['meta_key']] = $value;
}

$db->rollback();
$db->close();

echo json_encode(array(
	'reference' => 'ns_0727',
	'database_mode' => 'read_only_transaction_rolled_back',
	'active_plugin_slugs' => $active_slugs,
	'theme' => array('template' => $options['template'] ?? '', 'stylesheet' => $options['stylesheet'] ?? ''),
	'pages' => $safe_pages,
	'menu_items' => array_values($safe_menu_items),
), JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
