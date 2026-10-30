"""Compare completed 0-4 oncologist grades with saved scientific model/rule grades.

No model requests. Each input is linked by exact frozen-file path and option_id.
Agreement diagnoses grader calibration; it is not clinical predictive validity.
"""
from __future__ import annotations
import argparse
import json
import hashlib
import re
from pathlib import Path
from statistics import mean
from .scientific import DIMENSIONS
from .dataset import resolve_frozen_input


def quadratic_kappa(left,right):
    if not left or len(left)!=len(right): return None
    n=len(left)
    observed=mean((a-b)**2/16 for a,b in zip(left,right))
    expected=sum((i-j)**2/16*(left.count(i)/n)*(right.count(j)/n) for i in range(5) for j in range(5))
    return round(1-observed/expected,4) if expected else None


def calibrate(humans,reports):
    if not isinstance(humans,list):
        raise ValueError('Use the JSON list from Export independent ratings, not the full review JSON')
    index={}
    portable={}
    for report in reports:
        for case in report['cases']:
            if 'error' in case: continue
            for pop in case['defense_rubric']['populations']:
                if pop.get('score') is None or pop['scientific_assessment'].get('score') is None: continue
                key=(str(Path(case['frozen_input']).resolve()),pop['option_id'])
                if key in index: raise ValueError('Duplicate model prediction for the same frozen population')
                index[key]={r['dimension']:r['grade'] for r in pop['scientific_assessment']['dimensions']}
                digest=case.get('frozen_input_sha256')
                frozen=Path(case['frozen_input'])
                if not digest and frozen.is_file():
                    digest=hashlib.sha256(frozen.read_bytes()).hexdigest()
                if digest:
                    portable_key=(digest,pop['option_id'])
                    if portable_key in portable:
                        raise ValueError('Duplicate prediction for the same portable frozen input')
                    portable[portable_key]=index[key]
    rows={d:dict(human=[],predicted=[]) for d in DIMENSIONS}
    for item in humans:
        if not isinstance(item,dict) or item.get('ratings_source') not in (None,'independent_before_ai'):
            raise ValueError('Assisted feedback is not an independent calibration label')
        grades=item.get('scientific_grades')
        if not isinstance(grades,dict) or set(grades)!=set(DIMENSIONS) or any(type(v) is not int or not 0<=v<=4 for v in grades.values()):
            raise ValueError('Complete all four scientific grades as integers 0-4 before calibration')
        digest=item.get('input_sha256')
        if digest:
            if not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest):
                raise ValueError('Invalid portable input SHA-256')
            prediction=portable.get((digest,item['option_id']))
        else:
            prediction=index.get((str(Path(item['file']).resolve()),item['option_id']))
        if prediction is None: raise ValueError('No exact saved scientific prediction matches a human-graded population')
        for d in DIMENSIONS:
            rows[d]['human'].append(grades[d]); rows[d]['predicted'].append(prediction[d])
    results={}
    for d,r in rows.items():
        pairs=list(zip(r['human'],r['predicted']))
        results[d]=dict(cases=len(pairs),mean_absolute_error=round(mean(abs(a-b) for a,b in pairs),4) if pairs else None,
            exact_agreement=round(mean(a==b for a,b in pairs),4) if pairs else None,
            within_one_grade=round(mean(abs(a-b)<=1 for a,b in pairs),4) if pairs else None,
            quadratic_weighted_kappa=quadratic_kappa(r['human'],r['predicted']))
    return dict(benchmark='scientific_defense_calibration_v3',populations=len(humans),dimensions=results,
                interpretation='Ordinal agreement against human assessment. Human adjudication, independent test cases and treatment-level grouping are still required.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--human-grades',required=True)
    parser.add_argument('--report',action='append',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args(argv)
    reports=[]
    for path in args.report:
        report=json.loads(Path(path).read_text())
        for case in report['cases']:
            if case.get('frozen_input'):
                case['frozen_input']=str(resolve_frozen_input(path,case['frozen_input']))
        reports.append(report)
    result=calibrate(json.loads(Path(args.human_grades).read_text()),reports)
    Path(args.out).write_text(json.dumps(result,indent=1))
    print(json.dumps(result,indent=1))


if __name__=='__main__': main()
