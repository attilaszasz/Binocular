"""Summarize independently produced QC browser/coverage artifacts."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path('/workspace/Binocular')
out = root / 'artifacts/00037-qc'
results = root / 'frontend/test-results'
audits = []
networks = []
for path in sorted(results.rglob('*.json')):
    if path.name.endswith('-axe.json'):
        data = json.loads(path.read_text())
        audits.append({'path': str(path.relative_to(results)), 'violations': len(data['violations']), 'incomplete': len(data['incomplete']), 'passes': len(data['passes'])})
    elif path.name == 'ordinary-form-network.json':
        networks.append({'path': str(path.relative_to(results)), **json.loads(path.read_text())})
summary = {'axe_audits': len(audits), 'violations': sum(a['violations'] for a in audits), 'incomplete': sum(a['incomplete'] for a in audits), 'audits': audits, 'ordinary_form_network': networks}
(out / 'playwright-evidence-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
coverage = ET.parse(out / 'backend-coverage.xml').getroot()
print('Backend coverage:', coverage.attrib)
files = sorted(({'file': c.attrib['filename'], 'line_rate': float(c.attrib['line-rate']), 'covered': sum(int(l.attrib['hits']) > 0 for l in c.findall('./lines/line')), 'total': len(c.findall('./lines/line'))} for c in coverage.findall('.//class')), key=lambda x: x['line_rate'])
print('Lowest backend coverage:', json.dumps(files[:10], indent=2))
print('Browser evidence:', json.dumps(summary, indent=2))
