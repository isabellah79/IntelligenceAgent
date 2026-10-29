# Trial Intelligence Agent

Prototype work toward an agent that forecasts whether phase 2/3 trials meet their primary endpoint, using only information public before the readout.

## Layout

- `milestone1/`: local population-design lab for HR+/HER2− metastatic breast cancer after endocrine + CDK4/6 progression. Compare three candidate subgroups per treatment, with cited inclusion/exclusion drafts, reasons, pros/cons and population-specific conditional PFS scenarios. Gemini 3.8 Flash reviews population choices and criteria through Vertex AI. Run `python3 -m milestone1.server`; see [demo instructions](milestone1/README.md). Earlier individual-case records remain available in an archived view.
- `sponsor_lookup/`: the breast cancer company list, built in four reviewed steps.
  - `step1_sponsors.xlsx`: sponsors of the 625 recruiting phase 2 breast cancer trials.
  - `step2_companies.xlsx`: sponsors merged to parent companies, with tickers and size tags.
  - `step3_active_check.xlsx`: which US small/mid-cap companies still run company-led breast programs.
  - `step4_final_breast_companies.xlsx`: the final company table and upcoming readout events.
- `forecast/forecast.py`: the two-method single-trial forecast (reference class with odds adjustments, plus an effect-size model). Standard library only.
- `forecast/cases/`: inputs for each worked example.
  - `bria_abc.json`: BriaCell Bria-ABC phase 3, live forecast as of 2026-10-23 (about 8%).
  - `viktoria1_wt.json`: Celcuity VIKTORIA-1 backtest as of 2025-07-27 (65%; actual YES).

## Run

```
python forecast/forecast.py forecast/cases/bria_abc.json
python forecast/forecast.py forecast/cases/viktoria1_wt.json
```

## Caveats

- The adjustment factors and scenario weights are hand-set judgment calls. The next step is to learn them from many past readouts.
- The VIKTORIA-1 result was public before the model's training cutoff, so that backtest checks the mechanics, not predictive skill.
- Tickers, sizes and some figures in the sponsor files come from model knowledge or search summaries (sec.gov and clinicaltrials.gov were blocked); see each file's notes.
