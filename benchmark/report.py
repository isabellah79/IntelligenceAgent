"""Readable local scorecard with defense, forecasts, and references kept distinct."""
from __future__ import annotations


def _cell(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def render_markdown(report):
    lines = ["# Scientific population defense benchmark — provisional", "",
             "The defense grade emphasizes evidence strength, population applicability, selection justification and tradeoffs. Endpoint forecasts use separate clinical/design assumptions. Neither establishes which subgroup benefits more.", "",
             "The rubric is not yet calibrated against oncologist grades. Equal-quality defenses can tie; the evaluator does not force a ranking.", ""]
    sources = report.get("sources", {})
    first = next((c for c in report["cases"] if "error" not in c and c["defense_rubric"]["populations"]), None)
    if first:
        config=report.get('scientific_config')
        if config:
            lines += ["## Scientific grading", "",
                      f"Final defense = {100*config['scientific_share']:.0f}% scientific assessment + {100*(1-config['scientific_share']):.0f}% completeness. Endpoint forecasts contribute zero weight.", "",
                      "| Scientific dimension | Weight within scientific assessment |", "|---|---:|"]
            lines += [f"| {name.replace('_',' ').capitalize()} | {100*weight:.0f}% |" for name,weight in config['dimension_weights'].items()]
            lines += ["", "Each dimension uses an anchored 0–4 grade with cited reasons. The evidence bank was checked against primary/official sources; clinician adjudication is pending.", "",
                      "Missing scientific mappings produce **Unassessed**, never a completeness-only final score. Different ordinal profiles can produce equal totals.", ""]
        lines += ["## Current rule weights", "", "| Check | Weight |", "|---|---:|"]
        lines += [f"| {r['rule']} | {r['weight']} |" for r in first["defense_rubric"]["populations"][0]["results"]]
        lines += ["", "These are provisional analyst weights and must be fixed before held-out evaluation.", ""]
    for case in report["cases"]:
        if "error" in case:
            lines += [f"Producer error: {_cell(case['error'])}", ""]
            continue
        lines += [f"## {_cell(case['trial'].get('drug'))} · {_cell(case['option_set'])}", "",
                  "| Population | Defense /100 | Scientific /100 | Completeness /100 | Conditional endpoint forecast | References |",
                  "|---|---:|---:|---:|---|---|"]
        for population in case["defense_rubric"]["populations"]:
            forecast = population.get("endpoint_forecast") or {}
            endpoint = f"{forecast['score']:.3f} · {_cell(forecast.get('score_type'))}" if forecast.get("score") is not None else "Unavailable"
            refs = sorted({sid for row in case["reference_accuracy"]["pairs"] if row.get("option_id") == population["option_id"] for sid in row["source_ids"]})
            citations = ", ".join(f"[{sid}]({sources[sid]['url']})" if sources.get(sid, {}).get("url") else sid for sid in refs)
            science=population.get('scientific_assessment',{})
            for row in science.get('dimensions',[]):
                for sid in row['source_ids']:
                    if sid not in refs:
                        refs.append(sid)
            citations = ", ".join(f"[{sid}]({sources[sid]['url']})" if sources.get(sid, {}).get("url") else sid for sid in refs)
            grade=f"{100*population['score']:.1f}" if population.get('score') is not None else 'Unassessed'
            scientific_grade=f"{100*population['scientific_score']:.1f}" if population.get('scientific_score') is not None else 'Unassessed'
            lines.append(f"| {_cell(population['population'])} | {grade} | {scientific_grade} | {100*population.get('checklist_score',population.get('score',0)):.1f} | {endpoint} | {citations} |")
        lines += ["", "**Scientific reasons for each population:**", ""]
        for population in case['defense_rubric']['populations']:
            assessment=population.get('scientific_assessment',{})
            lines += [f"### {_cell(population['population'])}", ""]
            lines += [f"Assessment method: {_cell(assessment.get('method'))}; calibration pending.", ""]
            if assessment.get('score') is None:
                lines += [f"Unassessed: {_cell(assessment.get('reason'))}", ""]
            else:
                lines += ["| Dimension | Grade /4 | Reason | Evidence |", "|---|---:|---|---|"]
                for row in assessment['dimensions']:
                    citations=', '.join(f"[{sid}]({sources[sid].get('scientific_facts_url',sources[sid]['url'])})" for sid in row['source_ids'] if sources.get(sid,{}).get('url'))
                    lines.append(f"| {row['label']} | {row['grade']} | {_cell(row['reason'])} | {citations} |")
                lines += [""]
                for warning in assessment.get('limitations',[]):
                    lines += [f"Source-to-target limit: {_cell(warning)}", ""]
            failures='; '.join(r['rule'] for r in population['failures']) or 'No completeness failures detected'
            lines += [f"Completeness checks: {_cell(failures)}.", ""]
        lines += ["", "**Differences between populations:**", ""]
        for pair in case["defense_rubric"]["set_design"]["differentiation"]:
            changes = [f"{oid}: {_cell(row['text'])}" for oid, rows in pair["differences"].items() for row in rows]
            detail = "; ".join(changes) if changes else "No operational difference detected; changing an axis name alone is insufficient."
            lines.append(f"- {pair['left']} versus {pair['right']}: {detail}")
        lines += ["", "**Forecast assumptions:**", ""]
        for population in case["defense_rubric"]["populations"]:
            forecast = population.get("endpoint_forecast") or {}
            if forecast.get("score") is not None:
                lines.append(f"- {population['option_id']}: assumed HR {_cell(forecast.get('assumed_hr'))}; comparator {_cell(forecast.get('comparator'))}. {_cell(forecast.get('interpretation'))}")
            else:
                lines.append(f"- {population['option_id']}: {_cell(forecast.get('reason')) or 'No supplied endpoint forecast.'}")
        lines += ["", f"Historical match: {_cell(case['historical_match']['status'])}. {_cell(case['historical_match']['reason'])}", "",
                  f"Review status: {case['evaluation_gate']['status']}. Human source and clinical safety review remain pending.", ""]
        if case.get('science_judge_error'):
            lines += [f"Scientific judge failed: {_cell(case['science_judge_error'])}", ""]
    lines += ["## Evaluation coverage", "", f"Not evaluated: {', '.join(report['not_run'])}.", "",
              "Older scorecards use a different rubric and denominator and should not be compared numerically with this version.", ""]
    return "\n".join(lines)
