"""Build a single portable HTML5 oncology review form from frozen benchmark data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from .dataset import resolve_frozen_input

ASSETS = Path(__file__).with_name('review_page')


def script_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def prepare_data(report_path):
    report = json.loads(Path(report_path).read_text())
    cases = []
    used = set()
    for case in report['cases']:
        if 'error' in case:
            continue
        path = resolve_frozen_input(report_path, case['frozen_input'])
        raw = path.read_bytes()
        if case.get('frozen_input_sha256') and case['frozen_input_sha256'] != hashlib.sha256(raw).hexdigest():
            raise ValueError('Frozen review input does not match its recorded SHA-256')
        frozen = json.loads(raw)
        scored = {p['option_id']: p for p in case['defense_rubric']['populations']}
        populations = []
        for option in frozen['options']:
            grade = scored[option['option_id']]
            assessment = grade['scientific_assessment']
            sections = {name: option.get(name, []) for name in ('inclusion', 'exclusion', 'pros', 'cons', 'defense', 'protocol_pending')}
            for rows in sections.values():
                for row in rows:
                    used.update(row.get('source_ids', []))
            for row in assessment.get('dimensions', []):
                used.update(row['source_ids'])
            forecast = option.get('estimates', {}).get('endpoint_forecast', {})
            used.update(forecast.get('source_ids', []))
            populations.append(dict(option_id=option['option_id'], population=option['population'],
                axes=option.get('axes', []), **sections,
                source_context=assessment.get('source_facts', {}),
                ai=dict(defense_score=grade.get('score'), scientific_score=grade.get('scientific_score'),
                        checklist_score=grade.get('checklist_score'), dimensions=assessment.get('dimensions', []),
                        limitations=assessment.get('limitations', []), method=assessment.get('method'),
                        model=assessment.get('model_metadata', {}).get('reported_model') or assessment.get('model_metadata', {}).get('model'),
                        status=assessment.get('status')), forecast=forecast))
        cases.append(dict(case_id=case['trial']['case_id'], treatment=case['trial']['drug'],
                          parent_population=case['trial']['condition'], endpoint=case['trial']['primary_endpoint'],
                          input_id=path.name, input_sha256=hashlib.sha256(raw).hexdigest(),
                          populations=populations))
    if not cases:
        raise ValueError('No scored population cases are available for review')
    sources = {}
    for sid in sorted(used):
        source = report['sources'].get(sid)
        if not source:
            raise ValueError(f'Unknown review source: {sid}')
        url = source.get('url', '')
        if urlparse(url).scheme not in ('http', 'https'):
            raise ValueError(f'Unsafe or missing reference URL: {sid}')
        fact_url = source.get('scientific_facts_url', url)
        if urlparse(fact_url).scheme not in ('http', 'https'):
            raise ValueError(f'Unsafe scientific reference URL: {sid}')
        sources[sid] = dict(title=source['title'], url=url, scientific_url=fact_url)
    content = dict(schema_version='oncology-review-data-1.0', cases=cases, sources=sources,
                   config=report['scientific_config'], anchors=report['scientific_anchors'],
                   evidence_as_of=report['scientific_evidence']['evidence_as_of'],
                   evidence_review_status='Primary/official-source snapshot; oncologist adjudication pending')
    content['dataset_id'] = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return content


def build(report_path, out_path):
    data = prepare_data(report_path)
    css = (ASSETS / 'review.css').read_text()
    scripts = (ASSETS / 'state.js').read_text() + '\n' + (ASSETS / 'review.js').read_text()
    html = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="description" content="Portable oncology review form for treatment-specific trial populations after CDK4/6 progression.">
<title>Oncology population review</title>
<style>''' + css + '''</style></head>
<body><div id="app"></div><div id="toast" role="status" aria-live="polite"></div>
<noscript><p>This review form needs JavaScript enabled. It runs entirely in your browser, with no server or login.</p></noscript>
<script id="review-data" type="application/json">''' + script_json(data) + '''</script>
<script id="review-state" type="application/json">null</script>
<script>''' + scripts + '''</script></body></html>'''
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html)
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', default=str(Path(__file__).with_name('reports') / 'scientific-defense-v3-gemini.json'))
    parser.add_argument('--out', default=str(Path(__file__).with_name('reports') / 'oncology-review.html'))
    args = parser.parse_args(argv)
    data = build(args.report, args.out)
    print(f"Wrote {args.out}: {len(data['cases'])} treatments, {sum(len(c['populations']) for c in data['cases'])} populations. One self-contained file.")


if __name__ == '__main__':
    main()
