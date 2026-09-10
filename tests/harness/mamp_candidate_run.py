"""Run all fixed MAMP gates against the current release archive, then restore the plugin."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SANDBOX = Path('C:/MAMP/htdocs/kklidi-members-mamp-sandbox')
PLUGIN = SANDBOX / 'wp-content/plugins/kklidi-members'
PLUGIN_PARENT = PLUGIN.parent
PHP = Path('C:/MAMP/bin/php/php8.3.1/php.exe')
VERSION = re.search(r'\* Version: (\d+\.\d+\.\d+)',
                    (ROOT / 'kklidi-members.php').read_text(encoding='utf-8')).group(1)
ARCHIVE = ROOT / ('dist/kklidi-members-' + VERSION + '.zip')
RUNNERS = ('mamp_route_run.py', 'mamp_https_run.py', 'mamp_lms_run.py',
           'mamp_woo_run.py', 'mamp_kboard_run.py', 'mamp_race_run.py',
           'mamp_timing_run.py', 'mamp_mail_sender_run.py')
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


def php_json(code):
    result = subprocess.run([str(PHP), '-r', code], capture_output=True, timeout=90,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or not result.stdout:
        raise RuntimeError('WordPress candidate command failed')
    return json.loads(result.stdout)


def digest(root):
    rows = [(path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
            for path in sorted(item for item in root.rglob('*') if item.is_file())]
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()


def main():
    token = secrets.token_hex(6)
    staging = PLUGIN_PARENT / ('.kklidi-members-candidate-' + token)
    original = staging / 'original'
    extracted_root = staging / 'package'
    report = {'run_id': 'mamp-candidate-' + token, 'status': 'FAIL', 'version': VERSION,
              'archive': ARCHIVE.name}
    initial_active = False
    original_moved = False
    original_digest = ''
    try:
        if SANDBOX.resolve() != SANDBOX or PLUGIN.resolve() != PLUGIN \
                or staging.parent.resolve() != PLUGIN_PARENT.resolve() \
                or not ARCHIVE.is_file() or staging.exists():
            raise RuntimeError('Fixed candidate paths or archive are unavailable')
        staging.mkdir()
        initial = php_json(STATUS)
        initial_active = bool(initial['active'])
        original_digest = digest(PLUGIN)
        with zipfile.ZipFile(ARCHIVE) as package:
            names = package.namelist()
            if not names or any(not name.startswith('kklidi-members/')
                                or '..' in Path(name).parts for name in names):
                raise RuntimeError('Unsafe release archive layout')
            package.extractall(extracted_root)
        candidate = extracted_root / 'kklidi-members'
        php_json(DEACTIVATE)
        os.replace(PLUGIN, original)
        original_moved = True
        os.replace(candidate, PLUGIN)
        activated = php_json(ACTIVATE)
        if activated != {'active': True, 'version': VERSION}:
            raise RuntimeError('Candidate activation failed')
        report['archive_sha256'] = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
        report['gates'] = {}
        for runner in RUNNERS:
            result = subprocess.run([os.fspath(Path(os.sys.executable)), os.fspath(HERE / runner)],
                                    capture_output=True, timeout=300,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode or not result.stdout:
                report['gates'][runner] = {
                    'status': 'FAIL',
                    'returncode': result.returncode,
                    'stdout_tail': result.stdout.decode('utf-8', errors='replace')[-2000:],
                    'stderr_tail': result.stderr.decode('utf-8', errors='replace')[-4000:],
                }
                raise RuntimeError('MAMP gate failed: ' + runner)
            child = json.loads(result.stdout.splitlines()[-1])
            report['gates'][runner] = {'run_id': child.get('run_id'),
                                       'status': child.get('status')}
            if child.get('status') != 'PASS':
                raise RuntimeError('MAMP gate did not pass: ' + runner)
        report['status'] = 'PASS'
    finally:
        if original_moved:
            if PLUGIN.exists():
                try:
                    php_json(DEACTIVATE)
                except Exception:
                    pass
                used = staging / 'used-candidate'
                os.replace(PLUGIN, used)
            if original.exists():
                os.replace(original, PLUGIN)
            if initial_active:
                php_json(ACTIVATE)
            report['original_restored'] = digest(PLUGIN) == original_digest
            if not report['original_restored']:
                report['status'] = 'FAIL'
        if staging.is_dir() and staging.parent.resolve() == PLUGIN_PARENT.resolve() \
                and staging.name.startswith('.kklidi-members-candidate-'):
            shutil.rmtree(staging)
        report['temporary_directory_removed'] = not staging.exists()
        if not report['temporary_directory_removed']:
            report['status'] = 'FAIL'
        destination = ROOT / '.harness/reports' / (report['run_id'] + '.json')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report))


if __name__ == '__main__':
    main()
