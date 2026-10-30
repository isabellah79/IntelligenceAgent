"""Small clinical lexicon for deterministic clause matching.

Matching two eligibility clauses with no model means mapping both to the same
concepts. This module holds only the concept map and the stopword list; the
matching arithmetic lives in ``normalize.py``.

The lexicon deliberately encodes *concepts that change who is eligible*, not
every word a clause can contain. A clause whose wording is a paraphrase of a
lexicon concept matches; a clause using vocabulary this map does not know falls
back to lexical overlap and may be missed. ``normalize.match_clause`` reports
the match basis so a low-confidence match is visible rather than silent.
"""

# concept -> regex alternates. Order matters only for readability.
CONCEPTS = {
    "her2_low": r"her2[\s-]?low|ihc 1\+|ihc 2\+/ish[\s-]?(neg|negative)",
    "her2_ultralow": r"her2[\s-]?ultra[\s-]?low|ihc 0 with (membrane|partial membrane) staining",
    "her2_zero": r"ihc 0 (without|no) membrane|her2[\s-](zero|0)\b",
    "esr1": r"\besr1\b|\besr-?1 mutation|esr1[- ]mut",
    "pik3ca": r"\bpik3ca\b|\bpik3ca[- ]mut",
    "akt1": r"\bakt1\b",
    "pten": r"\bpten\b",
    "brca": r"\bbrca\s*[12]?\b|germline brca|brca[- ]mut",
    "hr_positive": r"hr[\s-]?(positive|\+)|er[\s-]?(positive|\+)|estrogen receptor[\s-]positive|hormone receptor[\s-]positive",
    "cns_brain_mets": r"brain metast|central nervous system|\bcns\b|leptomeningeal",
    "visceral_crisis": r"visceral crisis",
    "performance_status": r"\becog\b|performance status|karnofsky|\bps\s*[0-9]",
    "prior_cdk": r"cdk4/6|cdk 4/6|palbociclib|ribociclib|abemaciclib",
    "prior_endocrine": r"endocrine therapy|aromatase inhibitor|fulvestrant|antiestrogen|hormone therapy",
    "prior_chemo": r"chemotherapy|cytotoxic",
    "prior_adc": r"antibody[\s-]drug conjugate|\badc\b|deruxtecan|sacituzumab|govitecan",
    "her2_positive": r"her2[\s-]?(positive|amplified)|her2 3\+|ihc 3\+",
    "prior_lines": r"prior [a-z\- ]{0,20}lines?\b|\d+\s*prior lines?|lines of (therapy|treatment)|number of prior|prior (systemic )?(regimen|therapy)",
    "measurable_disease": r"measurable disease|recist|evaluable disease",
    "organ_function": r"bone marrow|absolute neutrophil|neutrophil count|platelet count|hemoglobin|creatinine|bilirubin|\bast\b|\balt\b|hepatic|renal function",
    "infection": r"\bhiv\b|hepatitis [bc]|active infection|tuberculosis",
    "cardiac": r"qtc|cardiac|ejection fraction|myocard",
    "pregnancy": r"pregnan|contracept|lactat|breastfeed",
    "washout": r"washout|washed out|prior therapy within|within [0-9]+ (weeks|days) (before|prior)",
    "surgery": r"surgery|surgical|radiotherapy|radiation therapy",
    "vaccine": r"live vaccine|live attenuated",
    "age": r"\bage\b|[0-9]{2} years",
    "consent": r"informed consent|able to (provide|give) consent",
    "ild": r"interstitial lung disease|\bild\b|pneumonitis",
    "brain_treatment": r"brain (metastases|mets).*(treated|stable|radiat)|stable brain",
    "life_expectancy": r"life expectancy",
    "other_malignancy": r"other (malignanc|invasive cancer)|prior malignancy",
}

COMPILED = {name: __import__("re").compile(pattern) for name, pattern in CONCEPTS.items()}

# Direction / strength words that a support check must not ignore.
NEGATIONS = ("not", "no", "none", "without", "negative", "absence", "excluded", "exclude", "never",
             "neither", "nor", "unless")
HEDGES = ("may", "might", "consider", "selected", "selected patients", "possibly", "potential",
          "exploratory", "hypothesis")

STOPWORDS = frozenset("""
a an the and or of to in on for with without at by from as is are was were be been being
any all other than that this these those prior previous must have has had takes take at least
more less one two three four five six seven eight nine ten <= >= < > = + - / ( ) [ ] , . ; : ' " %
""".split())

# Clause roles used by the scorer. A criterion tagged "scope" defines the parent
# population and is never scored as an amendment edit.
SUBSTANTIVE_TAGS = frozenset({"efficacy", "evidence_alignment", "safety", "generalizability", "design"})
