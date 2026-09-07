<?php
// CLI-only provisioning; no existing DB endpoint can be supplied by the runner.
if (PHP_SAPI !== 'cli') { exit(1); }
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
$port = (int) getenv('KKH_DB_PORT');
$run = getenv('KKH_RUN');
$name = getenv('KKH_DB');
if ($port < 20000 || !preg_match('/^[a-f0-9]{32}$/D', $run ?: '') || $name !== 'kklidi_harness_' . $run) {
    exit('Database guard rejected configuration.');
}
$db = new mysqli('127.0.0.1', 'root', '', '', $port);
$actual = realpath($db->query('SELECT @@datadir')->fetch_row()[0]);
$expected = realpath(getenv('KKH_DATA'));
if (!$expected || $actual !== $expected || file_get_contents(dirname($expected) . '/owner') !== $run) {
    exit('Server datadir ownership check failed.');
}
// Only after proving server ownership may this process write anything.
$password = $db->real_escape_string(getenv('KKH_DB_PASSWORD'));
$db->query("ALTER USER 'root'@'localhost' IDENTIFIED BY '$password'");
$db->query("CREATE DATABASE `$name` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
$db->query("CREATE USER 'harness'@'localhost' IDENTIFIED BY '$password'");
// Underscores are wildcard characters in database grants; escape them.
$grant = str_replace('_', '\\_', $name);
$db->query("GRANT ALL PRIVILEGES ON `$grant`.* TO 'harness'@'localhost'");
echo json_encode(['owned_datadir' => true, 'database_created' => true, 'mysql' => $db->server_info]);
