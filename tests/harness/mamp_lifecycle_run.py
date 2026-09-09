"""Install/update/reinstall/deactivate lifecycle gate for the fixed MAMP sandbox."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SANDBOX = Path('C:/MAMP/htdocs/kklidi-members-mamp-sandbox')
PLUGIN = SANDBOX / 'wp-content/plugins/kklidi-members'
PHP = 'C:/MAMP/bin/php/php8.3.1/php.exe'
PREVIOUS_VERSION = '0.7.19'
CURRENT_VERSION = re.search(
    r'\* Version: (\d+\.\d+\.\d+)',
    (ROOT / 'kklidi-members.php').read_text(encoding='utf-8'),
).group(1)
ALLOWED_INITIAL_VERSIONS = ('0.7.0', PREVIOUS_VERSION, CURRENT_VERSION)
OLD_ARCHIVE = ROOT / ('dist/kklidi-members-' + PREVIOUS_VERSION + '.zip')
NEW_ARCHIVE = ROOT / ('dist/kklidi-members-' + CURRENT_VERSION + '.zip')

STATUS = r'''require "C:/MAMP/htdocs/kklidi-members-mamp-sandbox/wp-load.php";
require_once ABSPATH."wp-admin/includes/plugin.php";
echo wp_json_encode(array("active"=>is_plugin_active("kklidi-members/kklidi-members.php"),
"version"=>defined("KKLIDI_MEMBERS_VERSION")?KKLIDI_MEMBERS_VERSION:null));'''
ACTIVATE = r'''require "C:/MAMP/htdocs/kklidi-members-mamp-sandbox/wp-load.php";
require_once ABSPATH."wp-admin/includes/plugin.php";
$r=activate_plugin("kklidi-members/kklidi-members.php");
if(is_wp_error($r)){fwrite(STDERR,$r->get_error_message());exit(2);}
echo wp_json_encode(array("active"=>is_plugin_active("kklidi-members/kklidi-members.php"),
"version"=>KKLIDI_MEMBERS_VERSION));'''
DEACTIVATE = r'''require "C:/MAMP/htdocs/kklidi-members-mamp-sandbox/wp-load.php";
require_once ABSPATH."wp-admin/includes/plugin.php";
deactivate_plugins("kklidi-members/kklidi-members.php",true,false);
echo wp_json_encode(array("active"=>is_plugin_active("kklidi-members/kklidi-members.php")));'''
PROTECTED = r'''require "C:/MAMP/htdocs/kklidi-members-mamp-sandbox/wp-load.php";
global $wpdb;$rows=array();$core_content=array($wpdb->posts,$wpdb->postmeta,$wpdb->comments,$wpdb->commentmeta);
$domain_pattern='/^'.preg_quote($wpdb->prefix,'/').'(?:kklidi_lms_|kboard_|woocommerce_|wc_(?:orders|order_|customer_lookup|download_log|product_|tax_|webhooks))/';
foreach($wpdb->get_col("SHOW TABLES") as $table){
$is_domain=in_array($table,$core_content,true)||preg_match($domain_pattern,$table);
if(!$is_domain||$table===$wpdb->prefix."woocommerce_sessions"){continue;}
$safe=str_replace("`","``",$table);$result=$wpdb->get_row("CHECKSUM TABLE `{$safe}`",ARRAY_A);
$rows[$table]=$result["Checksum"]??null;}ksort($rows);
echo wp_json_encode(array("users"=>$wpdb->get_col("SELECT ID FROM {$wpdb->users} ORDER BY ID"),
"domain"=>hash("sha256",wp_json_encode($rows)),"tables"=>$rows));'''


def php_json(code):
    result = subprocess.run([PHP, '-d', 'display_errors=stderr', '-r', code],
                            capture_output=True, timeout=60,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('WordPress lifecycle command failed')
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError('WordPress lifecycle command returned invalid JSON') from error


def tree_digest(root):
    rows = []
    for path in sorted(item for item in root.rglob('*') if item.is_file()):
        rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest(), len(rows)


def extract(archive, destination):
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        if not names or any(not name.startswith('kklidi-members/') or '..' in Path(name).parts
                            for name in names):
            raise RuntimeError('Release archive has an unsafe layout')
        package.extractall(destination)
    extracted = destination / 'kklidi-members'
    if not (extracted / 'kklidi-members.php').is_file():
        raise RuntimeError('Release archive has no plugin entry file')
    return extracted


def assert_plugin_parent_writable(token):
    probe = PLUGIN.parent / ('.kklidi-members-lifecycle-' + token + '.probe')
    try:
        with probe.open('x', encoding='ascii') as stream:
            stream.write(token)
    except OSError as error:
        raise RuntimeError('MAMP plugin directory is not writable; grant access before lifecycle mutation') from error
    finally:
        if probe.exists():
            probe.unlink()


def move_same_volume(source, destination):
    source = source.resolve(strict=True)
    parent = destination.parent.resolve(strict=True)
    if source.drive.casefold() != parent.drive.casefold() or destination.exists():
        raise RuntimeError('Lifecycle move must stay on one volume and target an absent path')
    os.replace(source, destination)


def main():
    token = secrets.token_hex(6)
    report = {'run_id': 'mamp-lifecycle-' + token, 'status': 'FAIL',
              'sandbox': 'fixed dedicated MAMP sandbox'}
    destination = ROOT / '.harness/reports' / (report['run_id'] + '.json')
    initial_active = False
    original_moved = False
    original_digest = None
    temp_root = Path(tempfile.mkdtemp(prefix='kklidi-members-lifecycle-')).resolve()
    original = temp_root / 'original'
    try:
        if SANDBOX.resolve() != SANDBOX or PLUGIN.resolve() != PLUGIN:
            raise RuntimeError('Fixed MAMP sandbox path mismatch')
        if not OLD_ARCHIVE.is_file() or not NEW_ARCHIVE.is_file():
            raise RuntimeError('Lifecycle release archives are missing')
        assert_plugin_parent_writable(token)
        report['old_archive_sha256'] = hashlib.sha256(OLD_ARCHIVE.read_bytes()).hexdigest()
        report['new_archive_sha256'] = hashlib.sha256(NEW_ARCHIVE.read_bytes()).hexdigest()
        initial = php_json(STATUS)
        initial_active = initial['active']
        if initial.get('version') not in ALLOWED_INITIAL_VERSIONS:
            raise RuntimeError('Sandbox must start at an approved baseline, previous or current Members version')
        report['initial_version'] = initial.get('version')
        protected_before = php_json(PROTECTED)
        original_digest, original_files = tree_digest(PLUGIN)

        fresh = extract(NEW_ARCHIVE, temp_root / 'fresh')
        old = extract(OLD_ARCHIVE, temp_root / 'old')
        update = extract(NEW_ARCHIVE, temp_root / 'update')
        reinstall = extract(NEW_ARCHIVE, temp_root / 'reinstall')

        php_json(DEACTIVATE)
        move_same_volume(PLUGIN, original)
        original_moved = True

        move_same_volume(fresh, PLUGIN)
        fresh_result = php_json(ACTIVATE)
        if fresh_result != {'active': True, 'version': CURRENT_VERSION}:
            raise RuntimeError('New installation activation failed')

        php_json(DEACTIVATE)
        move_same_volume(PLUGIN, temp_root / 'used-fresh')
        move_same_volume(old, PLUGIN)
        old_result = php_json(ACTIVATE)
        if old_result != {'active': True, 'version': PREVIOUS_VERSION}:
            raise RuntimeError('Previous release setup for update failed')
        move_same_volume(PLUGIN, temp_root / 'used-old')
        move_same_volume(update, PLUGIN)
        update_result = php_json(STATUS)
        if update_result != {'active': True, 'version': CURRENT_VERSION}:
            raise RuntimeError('Previous-to-current update failed')

        php_json(DEACTIVATE)
        move_same_volume(PLUGIN, temp_root / 'used-update')
        move_same_volume(reinstall, PLUGIN)
        reinstall_result = php_json(ACTIVATE)
        if reinstall_result != {'active': True, 'version': CURRENT_VERSION}:
            raise RuntimeError('Current-version reinstall failed')

        off = php_json(DEACTIVATE)
        with urllib.request.urlopen(
                'http://localhost:8888/kklidi-members-mamp-sandbox/', timeout=30) as response:
            inactive_http = response.status
            inactive_body = response.read().decode('utf-8')
        reactivate = php_json(ACTIVATE)
        if off['active'] or inactive_http != 200 or 'Fatal error' in inactive_body:
            raise RuntimeError('Inactive Core fallback failed')
        if reactivate != {'active': True, 'version': CURRENT_VERSION}:
            raise RuntimeError('Reactivation failed')
        protected_after = php_json(PROTECTED)
        if protected_after != protected_before:
            report['protected_tables_before'] = protected_before.get('tables', {})
            report['protected_tables_after'] = protected_after.get('tables', {})
            raise RuntimeError('Lifecycle changed protected users or domain tables')

        report.update(status='PASS', new_install=CURRENT_VERSION,
                      update=PREVIOUS_VERSION + '->' + CURRENT_VERSION,
                      reinstall=CURRENT_VERSION, deactivate_http=inactive_http,
                      deactivate_fatal_error=False, reactivate=True,
                      wordpress_user_ids_preserved=True, domain_fingerprint_preserved=True,
                      protected_table_count=len(protected_before.get('tables', {})),
                      original_files=original_files)
    finally:
        if original_moved:
            if PLUGIN.exists():
                try:
                    php_json(DEACTIVATE)
                except Exception:
                    pass
                move_same_volume(PLUGIN, temp_root / 'used-final')
            if original.exists():
                move_same_volume(original, PLUGIN)
            if initial_active and PLUGIN.exists():
                php_json(ACTIVATE)
            restored_digest, restored_files = tree_digest(PLUGIN)
            report['original_restored'] = (restored_digest == original_digest)
            report['restored_files'] = restored_files
            if not report['original_restored']:
                report['status'] = 'FAIL'
        if temp_root.parent == Path(tempfile.gettempdir()).resolve() \
                and temp_root.name.startswith('kklidi-members-lifecycle-'):
            shutil.rmtree(temp_root)
        report['temporary_directory_removed'] = not temp_root.exists()
        if not report['temporary_directory_removed']:
            report['status'] = 'FAIL'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report))


if __name__ == '__main__':
    main()
