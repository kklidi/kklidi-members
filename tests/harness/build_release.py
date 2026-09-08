"""Build an installable plugin ZIP from an explicit production allowlist."""
import gettext
import hashlib
import json
from pathlib import Path
import re
import zipfile
from run import PACKAGE_FILES

ROOT = Path(__file__).resolve().parents[2]

def build():
    source = (ROOT / 'kklidi-members.php').read_text(encoding='utf-8')
    version = re.search(r'\* Version: (\d+\.\d+\.\d+)', source).group(1)
    assert "define('KKLIDI_MEMBERS_VERSION', '" + version + "');" in source
    with (ROOT / 'languages/kklidi-members-ko_KR.mo').open('rb') as stream:
        translation = gettext.GNUTranslations(stream)
        assert version in translation.info()['project-id-version']
        assert translation.gettext('Log in') != 'Log in'
    messages = set()
    for directory in ('includes', 'templates'):
        for path in (ROOT / directory).rglob('*.php'):
            messages.update(re.findall(
                r"(?:__|_e|esc_html__|esc_attr__|esc_html_e|esc_attr_e)\(\s*'([^']*)'\s*,\s*'kklidi-members'",
                path.read_text(encoding='utf-8')))
    missing = sorted(message for message in messages
        if message != 'KKLIDI Members' and translation.gettext(message) == message)
    assert not missing, 'Missing Korean translations: ' + repr(missing)
    release_doc = 'docs/RELEASE-' + version + '.md'
    files = sorted(set(PACKAGE_FILES + ['README.md', 'readme.txt', 'CHANGELOG.md',
        'docs/PRODUCT.md', 'docs/ARCHITECTURE.md', 'docs/SECURITY.md', 'docs/MIGRATION.md',
        'docs/HARNESS_PLAN.md', 'docs/UI_UX.md', 'docs/OPERATIONS.md', release_doc]))
    assert all(not path.startswith(('tests/', '.harness/')) for path in files)
    assert all(not path.startswith('docs/evidence/') for path in files)
    assert all((ROOT / path).is_file() for path in files)
    destination = ROOT / 'dist'
    destination.mkdir(exist_ok=True)
    archive = destination / ('kklidi-members-' + version + '.zip')
    manifest = {}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
        for name in files:
            data = (ROOT / name).read_bytes()
            info = zipfile.ZipInfo('kklidi-members/' + name, date_time=(2026, 9, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(info, data)
            manifest[name] = hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        assert len(package.namelist()) == len(files)
    report = {'version': version, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'files': manifest, 'test_code_in_package': False, 'korean_translation': 'PASS',
              'source_strings_checked': len(messages)}
    (destination / ('kklidi-members-' + version + '.manifest.json')).write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'version': version, 'files': len(files), 'archive_sha256': report['archive_sha256']}))

if __name__ == '__main__': build()
