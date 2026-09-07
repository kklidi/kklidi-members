"""Export only non-sensitive aggregate verification evidence for source control."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main():
    reports = ROOT / '.harness/reports'
    latest = json.loads((reports / 'latest.json').read_text(encoding='utf-8'))
    assert latest['status'] == 'PASS'
    contracts = {name: [{'status': row['status'], **{key: row[key] for key in
        ('parallel_processes', 'parallel_calls', 'parallel_allowed') if key in row}}
        for row in rows] for name, rows in latest['mvp_contracts'].items()}
    selected = {}
    for filename in ('mamp-lms-4f91a2c6d8be.json', 'mamp-kboard-394cb2f1d392.json', 'mamp-woo-be0342cba88e.json'):
        data = json.loads((reports / filename).read_text(encoding='utf-8'))
        selected[data['run_id']] = {key: data[key] for key in ('status', 'transport', 'modes',
            'passed', 'cleanup', 'not_run', 'browser_javascript', 'checkout_login_post',
            'cart_preserved', 'rendered_member_order', 'guest_order_not_claimed',
            'woo_device_allowed', 'woo_device_blocked') if key in data}
    output = {'release': '0.5.0', 'synthetic_run': latest['run_id'], 'execution_status': latest['status'],
        'production_acceptance': 'PARTIAL', 'contracts': contracts, 'integration': selected,
        'performance': latest['mvp_contracts'].get('AUTH-PERF-003', []),
        'scope_note': 'HTTP/PHP evidence; interactive browser JavaScript and deployment policy gates remain open.'}
    destination = ROOT / 'docs/evidence/0.5.0.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Aggregate release evidence exported: ' + latest['run_id'])

if __name__ == '__main__': main()
