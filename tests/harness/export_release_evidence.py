"""Export only credential-free aggregate evidence for the current plugin version."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def newest(reports, pattern):
    matches = sorted(reports.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    assert matches, 'Missing report: ' + pattern
    return json.loads(matches[0].read_text(encoding='utf-8'))

def main():
    source = (ROOT / 'kklidi-members.php').read_text(encoding='utf-8')
    version = re.search(r'\* Version: (\d+\.\d+\.\d+)', source).group(1)
    reports = ROOT / '.harness/reports'
    synthetic = json.loads((reports / 'latest.json').read_text(encoding='utf-8'))
    assert synthetic['status'] == 'PASS'
    contracts = {name: [{'status': row['status'], **{key: row[key] for key in
        ('parallel_processes', 'parallel_calls', 'parallel_allowed') if key in row}}
        for row in rows] for name, rows in synthetic['mvp_contracts'].items()}

    integrations = {}
    for pattern in ('mamp-lms-*.json', 'mamp-kboard-*.json', 'mamp-woo-*.json',
                    'mamp-race-*.json', 'mamp-timing-*.json', 'browser-chrome-*.json'):
        data = newest(reports, pattern)
        assert data['status'] in ('PASS', 'PARTIAL')
        integrations[data['run_id']] = {key: value for key, value in data.items()
            if key != 'reset_bootstrap'}
    preflight = json.loads((reports / 'mamp-deployment-preflight.json').read_text(encoding='utf-8'))
    environment = json.loads((reports / 'mamp-environment-20260908.json').read_text(encoding='utf-8-sig'))
    d06 = json.loads((reports / 'reference-d06-20260908.json').read_text(encoding='utf-8-sig'))
    output = {
        'release': version,
        'synthetic_run': synthetic['run_id'],
        'execution_status': synthetic['status'],
        'production_acceptance': 'PARTIAL',
        'contracts': contracts,
        'integration': integrations,
        'performance': synthetic['mvp_contracts'].get('AUTH-PERF-003', []),
        'deployment_preflight': preflight,
        'local_environment': environment,
        'd06_reference_audit': d06,
        'scope_note': 'Local behavior/browser gates passed; production TLS, persistent cache/proxy outage, and production migration need an identified deployment environment.'
    }
    destination = ROOT / ('docs/evidence/' + version + '.json')
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Aggregate release evidence exported: ' + synthetic['run_id'])

if __name__ == '__main__':
    main()
