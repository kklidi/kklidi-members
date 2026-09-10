"""Executable AUTH-MAIL-SENDER-001 verification for the fixed MAMP sandbox."""
import json
from pathlib import Path
import secrets
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PHP = Path('C:/MAMP/bin/php/php8.3.1/php.exe')


def call(action, token):
    result = subprocess.run(
        [str(PHP), '-d', 'display_errors=stderr', str(HERE / 'mamp_mail_sender_case.php'), action, token],
        capture_output=True, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).decode('utf-8', errors='replace')[-2000:]
        raise RuntimeError(f'Mail sender fixture failed: {action}: {detail}')
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f'Mail sender fixture returned invalid JSON: {action}') from error


def main():
    token = secrets.token_hex(6)
    report = {
        'run_id': 'mamp-mail-sender-' + token,
        'contract': 'AUTH-MAIL-SENDER-001',
        'status': 'FAIL',
        'environment': 'fixed dedicated MAMP sandbox',
    }
    setup_done = False
    try:
        if not PHP.is_file():
            raise RuntimeError('MAMP PHP executable is unavailable')
        setup = call('setup', token)
        setup_done = True
        probe = call('probe', token)
        if probe.get('accepted') is not True:
            raise RuntimeError('MAMP wp_mail sender probe was not accepted: ' + repr(probe))
        report.update(
            status='PASS',
            wp_mail_request_accepted=True,
            mailbox_sink_attempts=probe.get('sink_attempts', 0),
            members_scoped_from=probe.get('scoped_from', False),
            plain_text=probe.get('plain_text', False),
            footer_applied=probe.get('footer_applied', False),
            account_mail_audit=probe.get('account_mail_audit'),
            external_mailbox_delivery=probe.get('external_mailbox_delivery', False),
            fixture_user_id=setup.get('user_id'),
        )
    finally:
        if setup_done:
            try:
                report['cleanup'] = call('cleanup', token)
                if report['cleanup'].get('cleaned') is not True:
                    report['status'] = 'FAIL'
            except Exception as error:
                report['cleanup_error'] = str(error)
                report['status'] = 'FAIL'
        destination = ROOT / '.harness/reports' / (report['run_id'] + '.json')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report))


if __name__ == '__main__':
    main()
