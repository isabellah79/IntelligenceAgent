"""Producers: what generates the option sets the benchmark grades.

A benchmark without a baseline cannot say whether the agent is good; the plan
names four comparisons. Each producer here returns a normalised option set:

* ``demo``        — the milestone 1 harness (curated population library).
* ``original``    — baseline 1: the trial's original protocol criteria.
* ``single_pass`` — baseline 2: one model call, no tools, no comparison.
* ``one_option``  — baseline 3: the agent with tools but a single option.
* ``autotrial``   — baseline 4: one option written to resemble existing trials.

Live baselines use the demo's configured provider (including Vertex Gemini).
Offline runs make no model calls. All generated baselines receive the same catalog.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone

from .schema import normalise_option_set
from .sources import SourceCatalog

SYSTEM = """You design clinical-trial patient populations.
Given a trial context, propose a patient population for it and write the inclusion and exclusion criteria.
Every claim, criterion and estimate must cite a source id from the supplied catalog, and only from it.
Write at least two specific pros and cons per population, reasons for substantive criteria,
and one cited defense for each population. Mark missing estimates unavailable; never invent an eligible-pool share.
Explain source-to-target limitations and distinguish hypotheses from established findings.
Return ONLY JSON:
{"options":[{"option_id":"...","population":"one line","axes":["named axis"],
  "inclusion":[{"text":"...","reason":"why this criterion is needed","purpose":"scope|efficacy|evidence_alignment|safety|generalizability|design","source_ids":["CATALOG_ID"]}],
  "exclusion":[{"text":"...","purpose":"...","source_ids":["CATALOG_ID"]}],
  "pros":[{"text":"...","source_ids":["CATALOG_ID"]}],
  "cons":[{"text":"...","source_ids":["CATALOG_ID"]}],
  "defense":[{"text":"why this subgroup is worth studying, including uncertainty","source_ids":["CATALOG_ID"]}],
  "estimates":{"eligible_share":{"status":"unavailable","reason":"No denominator data supplied"},
               "endpoint_forecast":{"status":"unavailable","reason":"No explicit population-specific forecast supplied"}},
  "references":[{"source_id":"CATALOG_ID","supports":"..."}]}],
 "recommendation":{"option_id":"...","defense":[{"text":"...","source_ids":["CATALOG_ID"]}]}}
Do not invent studies, thresholds, doses or effect estimates."""


def _catalog_block(catalog: SourceCatalog) -> str:
    rows = [dict(id=k, title=v.get("title", ""), scope=v.get("scope", ""),
                 scientific_facts=v.get("scientific_facts")) for k, v in catalog.records.items()]
    return json.dumps(rows, ensure_ascii=False, indent=0)


def _ask(system: str, user: str, max_tokens: int = 8000) -> dict:
    from milestone1.llm import generate
    text, metadata = generate(system, user, max_tokens=max_tokens)
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    payload = json.loads(text)
    payload["provenance"] = _provenance("general_llm", model=metadata["model"], provider=metadata["provider"],
                                        reported_model=metadata.get("reported_model"), usage=metadata.get("usage"))
    return payload


def _provenance(agent: str, model: str | None = None, **extra) -> dict:
    return dict(agent=agent,
                model=model or "none",
                created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                tools=extra.pop("tools", []), **extra)


# -- the demo ---------------------------------------------------------------

def from_demo(treatment_id: str = "elacestrant", catalog: SourceCatalog | None = None, result: dict | None = None) -> dict:
    """One demo treatment rendered as an option set."""
    from milestone1.populations import propose

    result = result if result is not None else propose(focus_treatment_id=treatment_id)
    treatment = next(t for t in result["treatments"] if t["id"] == treatment_id)
    options = []
    for population in treatment["populations"]:
        options.append(dict(
            option_id=population["id"],
            population=population["title"],
            axes=[population.get("axis")] if population.get("axis") else [],
            inclusion=population["inclusion"],
            exclusion=population["exclusion"],
            pros=population["pros"],
            cons=population["cons"],
            defense=[population["benefit_statement"]],
            protocol_pending=population["protocol_pending"],
            evidence_context=dict(transfer=population["transfer"], status=population["kind"],
                                  note=population.get("scope_note")),
            estimates=_demo_estimates(population),
            references=[dict(source_id=s, supports=population.get("source_ids", []))
                        for s in population.get("source_ids", [])],
        ))
    return normalise_option_set(dict(
        trial=dict(case_id=treatment_id, nct_id=None, source_trial_names=sorted({p["effect"].get("trial", "") for p in treatment["populations"] if p.get("effect")}),
                   condition=result["context"]["parent_population"], phase="phase 2/3 setting",
                   drug=treatment["title"], primary_endpoint="PFS", line_of_therapy="post-CDK4/6"),
        options=options,
        recommendation=dict(option_id=treatment["starting_population_id"],
                            defense=[dict(text=population.get("benefit_statement", {}).get("text", ""),
                                          source_ids=population.get("benefit_statement", {}).get("source_ids", []))
                                     for population in treatment["populations"]
                                     if population["id"] == treatment["starting_population_id"]]),
        provenance=_provenance("demo", model="curated", tools=["population_library"])))


def _demo_estimates(population: dict) -> dict:
    """The demo's forecast, expressed as the plan's range estimates."""
    forecast = population.get("forecast") or {}
    score = forecast.get("score")
    return dict(
        eligible_share=dict(status="unavailable", reason="No population-prevalence estimate is supplied."),
        endpoint_forecast=dict(status="available" if score is not None else "unavailable",
            score=score, method_a=forecast.get("method_a"), method_b=forecast.get("method_b"),
            assumed_hr=forecast.get("assumed_hr"), comparator=forecast.get("comparator"),
            text=forecast.get("effect_origin") or forecast.get("unavailable_reason") or "",
            reason=forecast.get("unavailable_reason"), interpretation=forecast.get("interpretation"),
            source_ids=population.get("source_ids", []), score_type=forecast.get("score_type")))


# -- baselines --------------------------------------------------------------

def original_criteria(trial_id: str, pair: dict) -> dict:
    """Baseline 1: the protocol's own original criteria, as one option."""
    return normalise_option_set(dict(
        trial=dict(nct_id=pair.get("nct_id"), condition=pair.get("title", ""), phase=pair.get("phase", ""),
                   drug="", primary_endpoint="", line_of_therapy=""),
        options=[dict(option_id=f"{trial_id}__original", population="Original protocol population",
                      axes=["none (baseline)"],
                      inclusion=[dict(text=c, purpose=None, source_ids=[]) for c in _criteria_lines(pair.get("original_inclusion", ""))],
                      exclusion=[dict(text=c, purpose=None, source_ids=[]) for c in _criteria_lines(pair.get("original_exclusion", ""))],
                      unclassified_criteria=[dict(text=c, purpose=None, source_ids=[]) for c in _criteria_lines(pair.get("original_criteria", ""))]
                          if "original_inclusion" not in pair else [], pros=[], cons=[],
                      estimates={}, references=[])],
        recommendation=dict(option_id=f"{trial_id}__original", defense=[]),
        provenance=_provenance("original", model="none")))


def _criteria_lines(text: str) -> list[str]:
    return [line.strip(" *-") for line in (text or "").splitlines() if len(line.strip()) > 3]


def single_pass(context: dict, catalog: SourceCatalog) -> dict:
    """Baseline 2: one call, no tools, one option, no comparison."""
    user = json.dumps(dict(task="Propose one patient population for this trial.",
                           context=context, catalog=_catalog_block(catalog)), ensure_ascii=False)
    payload = _ask(SYSTEM, user)
    payload["options"] = payload.get("options", [])[:1]
    if payload["options"]:
        payload["recommendation"] = dict(option_id=payload["options"][0]["option_id"],
                                         defense=payload.get("recommendation", {}).get("defense", []))
    payload.update(trial=context, provenance={**payload.get("provenance", {}), "agent":"single_pass", "tools":[]})
    return normalise_option_set(payload)


def one_option(context: dict, catalog: SourceCatalog, demo_set: dict | None = None) -> dict:
    """Baseline 3: the agent's tools and criteria-writing, but only one option."""
    if demo_set is None:
        demo_set = single_pass(context, catalog)
    best = demo_set["recommendation"].get("option_id")
    chosen = next((o for o in demo_set["options"] if o["option_id"] == best), next(iter(demo_set["options"]), None))
    out = deepcopy(demo_set)
    out["options"] = [deepcopy(chosen)] if chosen else []
    out["recommendation"] = dict(option_id=chosen["option_id"] if chosen else None,
                                 defense=demo_set["recommendation"].get("defense", []))
    out["provenance"] = _provenance("one_option", model=demo_set.get("provenance", {}).get("model"),
                                     tools=["population_library"], method="selection ablation; not a fresh tool-using model run")
    return out


def autotrial_style(context: dict, catalog: SourceCatalog) -> dict:
    """Baseline 4: imitate existing trials' criteria; no alternatives, no defense."""
    user = json.dumps(dict(task="Write the eligibility criteria that breast cancer trials of this kind "
                                "typically contain. Imitate the usual wording. One population only.",
                           context=context, catalog=_catalog_block(catalog)), ensure_ascii=False)
    payload = _ask(SYSTEM, user)
    payload["options"] = payload.get("options", [])[:1]
    payload["recommendation"] = {}
    payload.update(trial=context, provenance={**payload.get("provenance", {}), "agent":"autotrial_style_prompt", "tools":[]})
    return normalise_option_set(payload)


def general_llm(context: dict, catalog: SourceCatalog) -> dict:
    """Fair general-model baseline: same task, catalog and option count as the agent."""
    payload = _ask(SYSTEM, json.dumps(dict(task="Propose and defend three differentiated candidate populations; recommend a starting point conditionally.",
                                         context=context, catalog=_catalog_block(catalog)), ensure_ascii=False))
    payload["trial"] = context
    return normalise_option_set(payload)


def from_result(result: dict, treatment_id: str | None = None) -> dict:
    """Adapt a saved demo/Gemini response, retaining exactly the reviewed text."""
    if result.get("task") != "population_design":
        return normalise_option_set(result)
    treatment_id = treatment_id or result["focus_treatment_id"]
    out = from_demo(treatment_id, result=result)
    review = result.get("model_review")
    if review and review.get("treatment_id") == treatment_id:
        rec = review.get("recommendation") or {}
        out["recommendation"] = dict(option_id=rec.get("population_id"), defense=[dict(text=rec.get("reason", ""), source_ids=rec.get("source_ids", []))])
        out["provenance"].update(agent="saved_gemini_review", model=result.get("model_metadata", {}).get("model"),
                                 created=result.get("created_at"), tools=["population_library"],
                                 review_scope="Recommendation evaluated; criterion proposals are not silently applied.")
    return normalise_option_set(out)
