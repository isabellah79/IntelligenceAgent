"""Connect the original forecast prototype without reinterpreting its target."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

from forecast.forecast import forecast_case

EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "forecast" / "cases"
EXAMPLES = {
    "viktoria1_wt": dict(title="VIKTORIA-1 · historical mechanics check", file="viktoria1_wt.json",
                        option_id="gedatolisib", source_ids=["GEDA-LABEL"],
                        caveat="PIK3CA wild-type trial. Outcome already known; source file acknowledges leakage. This does not validate prediction skill."),
    "bria_abc": dict(title="Bria-ABC · original worked example", file="bria_abc.json", option_id=None,
                     source_ids=[], caveat="Cancer-vaccine OS trial; not a forecast for the post-CDK4/6 regimens in this demo. No current outcome check is performed."),
}


def examples():
    result = {}
    for key, info in EXAMPLES.items():
        case = json.loads((EXAMPLE_DIR / info["file"]).read_text())
        result[key] = {**info, "case": case, "result": forecast_case(case)}
    return result


def evaluate_forecast(case, option_id=None):
    result = forecast_case(case)
    exact = next(((key, item) for key, item in examples().items() if item["case"] == case), None)
    result["input"] = deepcopy(case)
    result["option_id"] = option_id
    result["source_ids"] = []
    result["included_in_treatment_score"] = False
    result["as_of_in_future"] = date.fromisoformat(case["as_of"]) > date.today()
    if exact:
        key, item = exact
        result.update(example_id=key, provenance="Unchanged original worked example",
                      source_ids=item["source_ids"], interpretation=item["caveat"])
        if option_id != item["option_id"]:
            result["interpretation"] += " The selected treatment differs from the example; this trial forecast cannot be transferred to that treatment."
        if case.get("outcome") in (0, 1):
            result["historical_outcome"] = case["outcome"]
    else:
        result.update(example_id=None, provenance="User-edited analyst assumptions",
                      interpretation="A hypothetical trial calculation. Priors, odds factors, effect scenarios and event assumptions need independent justification. Any copied outcome is ignored.")
    result["limitations"] = [
        "Methods A and B are averaged equally, as in forecast.py; this blend has not been calibrated.",
        "Method B uses a proportional-hazards, 1:1 allocation, normal-approximation model. It is not valid for every design or endpoint.",
        "No confidence interval is estimated. Method disagreement is not a statistical uncertainty interval.",
        "No observed treatment HR is automatically inserted as a prospective true-effect assumption.",
        "A trial-endpoint forecast does not estimate clinical benefit or determine which treatment to prescribe.",
    ]
    return result
