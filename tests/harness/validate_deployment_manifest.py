"""Validate the owner, backup and rollback evidence required for a real deployment."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
CURRENT_MEMBERS_VERSION = re.search(
    r'\* Version: (\d+\.\d+\.\d+)',
    (ROOT / 'kklidi-members.php').read_text(encoding='utf-8'),
).group(1)

OWNER_KEYS = {
    'members_runtime', 'wordpress_privacy', 'woocommerce', 'lms',
    'payout', 'site_content', 'rollback',
}
ROUTE_OWNERS = {
    'members_account': 'members_runtime',
    'woocommerce_orders': 'woocommerce',
    'lms_learning': 'lms',
    'payout_settlement': 'payout',
    'site_application_pages': 'site_content',
    'kboard_temporary': 'site_content',
}
SENSITIVE_KEY = re.compile(r'(password|passwd|secret|token|credential)', re.I)
PLACEHOLDER = re.compile(r'(required|placeholder|example|tbd|unknown)', re.I)


def contains_sensitive_key(value):
    if isinstance(value, dict):
        return any(SENSITIVE_KEY.search(str(key)) or contains_sensitive_key(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(contains_sensitive_key(item) for item in value)
    return False


def present(value):
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER.search(value)


def inspect(manifest):
    environment = manifest.get('environment', {})
    parsed = urllib.parse.urlsplit(str(environment.get('base_url', '')))
    owners = manifest.get('owners', {})
    routes = manifest.get('route_owners', {})
    backup = manifest.get('backup', {})
    rollback = manifest.get('rollback', {})
    observation = manifest.get('observation', {})
    decisions = manifest.get('policy_decisions', {})
    versions = manifest.get('versions', {})
    try:
        datetime.fromisoformat(str(backup.get('created_at_utc', '')).replace('Z', '+00:00'))
        backup_time = True
    except ValueError:
        backup_time = False
    checks = {
        'schema_version': manifest.get('schema_version') == 1,
        'no_credentials': not contains_sensitive_key(manifest),
        'environment_kind': environment.get('kind') in ('staging', 'production'),
        'trusted_https_url': parsed.scheme == 'https' and bool(parsed.hostname)
            and not parsed.hostname.endswith('.invalid')
            and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
        'single_site': environment.get('single_site') is True,
        'versions_recorded': all(present(versions.get(key))
            for key in ('wordpress', 'php', 'members')),
        'supported_runtime': versions.get('wordpress') == '7.1'
            and versions.get('php') == '8.3'
            and versions.get('woocommerce') in ('11.1.0', 'disabled'),
        'current_members_version': versions.get('members') == CURRENT_MEMBERS_VERSION,
        'owners_assigned': set(owners) == OWNER_KEYS and all(present(value) for value in owners.values()),
        'route_owners_match_contract': routes == ROUTE_OWNERS,
        'backup_hash': bool(re.fullmatch(r'[a-f0-9]{64}', str(backup.get('artifact_sha256', '')))),
        'backup_time': backup_time,
        'restore_tested': backup.get('restore_tested') is True
            and present(backup.get('restore_test_evidence')),
        'bounded_rollback': rollback.get('full_database_restore_for_feature_rollback') is False
            and rollback.get('members_enabled') in ('restore_previous_release', 'keep_current_release')
            and rollback.get('registration_mutations_blocked_if_policy_guard_absent') is True,
        'observation_window': int(observation.get('minimum_days', 0) or 0) >= 14
            and observation.get('actual_recovery_required') is True
            and (
                (versions.get('woocommerce') == '11.1.0'
                 and observation.get('actual_order_required') is True)
                or (versions.get('woocommerce') == 'disabled'
                    and observation.get('actual_order_required') is False)
            ),
        'conservative_policies': decisions == {
            'marketing_collection': 'disabled_until_purpose_and_withdrawal_are_approved',
            'display_name_uniqueness': 'duplicates_allowed',
            'legacy_email_state': 'legacy_unknown',
        },
    }
    return {
        'status': 'READY' if all(checks.values()) else 'BLOCKED',
        'checks': checks,
        'failed': [name for name, passed in checks.items() if not passed],
        'environment': environment.get('kind', 'unspecified'),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    report = inspect(manifest)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'READY' else 2)


if __name__ == '__main__':
    main()
