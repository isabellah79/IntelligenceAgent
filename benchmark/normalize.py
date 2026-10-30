"""Deterministic clause parsing and matching.

Everything here is rule-based and offline: registry criteria text is split into
clauses, mapped to lexicon concepts, and compared with a concept-plus-token
overlap score. A model judge would handle paraphrase better; this is the part of
the benchmark that must stay reproducible and auditable.

Two ideas do the work:

* A *clause* is one eligibility statement. Registry criteria arrive as numbered
  lines, so splitting is mostly a matter of respecting the numbering.
* A clause *matches* another when they share concepts and do not contradict on
  polarity or on a number. The match carries its basis so a reviewer can see
  whether it was concept-backed or only lexical.
"""
from __future__ import annotations

import re

from .lexicon import COMPILED, NEGATIONS, STOPWORDS

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+./-]*")
_NUMBER = re.compile(r"(?<![a-zA-Z0-9/])\d+(?:\.\d+)?(?![a-zA-Z0-9/])")
# A criterion line begins with "1.", "1)", "-", "*", or a bullet character.
_ITEM_START = re.compile(r"^\s*(?:\d{1,2}[.)]|[-*•·])\s+")
_CONCEPT_THRESHOLD = 0.72


def tokenize(text: str) -> list[str]:
    """Lower-case word tokens with stopwords removed."""
    return [t for t in _TOKEN.findall((text or "").lower()) if t not in STOPWORDS and len(t) > 1]


def _fold(text: str) -> str:
    """Case- and whitespace-insensitive form, for an exact-match short circuit."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def numbers(text: str) -> set[float]:
    """Eligibility-relevant numbers in the text."""
    return {float(n) for n in _NUMBER.findall(text or "")}


def thresholds(text: str) -> set[tuple[str, str]]:
    """Retain comparison direction: ECOG <=2 and >=2 are different criteria."""
    folded = (text or "").lower().replace("≤", "<=").replace("≥", ">=").replace("–", "-")
    folded = re.sub(r"at least\s+", ">=", folded)
    folded = re.sub(r"(?:no more than|at most)\s+", "<=", folded)
    return set(re.findall(r"(<=|>=|<|>)\s*(\d+(?:\.\d+)?)", folded))


def selection_states(text: str) -> dict[str, str]:
    """Limited biomarker-state guard; shared gene names do not mean equal eligibility."""
    low = (text or "").lower()
    markers = concepts(text) & {"esr1", "pik3ca", "akt1", "pten", "brca"}
    inclusive = bool(re.search(r"unselected|regardless|with or without|both|altered and non|mutated and non", low))
    wild = bool(re.search(r"wild[- ]type|non[- ]mutat|non[- ]altered|no.{0,10}mutation", low))
    altered = bool(re.search(r"mutation|mutated|alteration|altered", low))
    state = "unselected" if inclusive else "wild_type" if wild else "altered" if altered else "unspecified"
    return {marker:state for marker in markers}


def concepts(text: str) -> set[str]:
    """Lexicon concepts present in the text."""
    low = (text or "").lower()
    return {name for name, pattern in COMPILED.items() if pattern.search(low)}


def is_negative(text: str) -> bool:
    """Heuristic polarity: does the clause state an exclusion or absence?"""
    low = re.sub(r"\bno more than\b|\bnot more than\b|\bnot less than\b", "", (text or "").lower())
    low = f" {low} "
    return any(f" {word} " in low or low.startswith(f"{word} ") for word in NEGATIONS)


# Registry criteria often open with these as their own line. They label a
# section and carry no eligibility content, so they never become clauses.
_SECTION_HEADER = re.compile(r"^\s*(inclusion|exclusion|key)\s+criteria\s*:?\s*$", re.IGNORECASE)


def split_clauses(text: str) -> list[str]:
    """Split registry criteria text into individual clauses.

    Numbered lines stay whole; a long unnumbered paragraph is split on
    sentence boundaries so one paragraph does not count as a single clause.
    Section headers such as "Inclusion Criteria:" are dropped.
    """
    clauses: list[str] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or _SECTION_HEADER.match(line):
            continue
        line = _ITEM_START.sub("", line)
        if len(line) <= 240 or not line.endswith("."):
            clauses.append(line)
            continue
        # Long sentence: break after ". " followed by a capital.
        parts = re.split(r"(?<=\.)\s+(?=[A-Z])", line)
        clauses.extend(p.strip() for p in parts if p.strip())
    return clauses


def clause_similarity(a: str, b: str) -> dict:
    """Overlap between two clauses, with the evidence behind it.

    ``score`` blends three views, because each alone misleads:

    * **concept coverage** — what share of the first clause's concepts the second
      contains. This is the question a support check asks: does the source carry
      the claim's content? Symmetric Jaccard alone would punish a short source
      for not restating a long claim.
    * **concept Jaccard** — do they talk about the same things at all.
    * **token coverage** — does the wording line up, for claims the lexicon
      does not fully cover.

    Returns the components so a caller can require a concept-backed match rather
    than relying on wording alone.
    """
    ca, cb = concepts(a), concepts(b)
    ta, tb = set(tokenize(a)), set(tokenize(b))
    concept_jaccard = len(ca & cb) / len(ca | cb) if ca | cb else 0.0
    concept_coverage = len(ca & cb) / len(ca) if ca else 0.0
    token_jaccard = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    token_coverage = len(ta & tb) / len(ta) if ta else 0.0
    shared_concepts = sorted(ca & cb)
    # Numbers are a strong signal when present, and a contradiction when equal
    # concepts appear with different thresholds (e.g. ">= 2 lines" vs ">= 1 line").
    na, nb = numbers(a), numbers(b)
    numeric_conflict = bool(na and nb and na != nb and shared_concepts)
    comparison_conflict = bool(thresholds(a) and thresholds(b) and thresholds(a) != thresholds(b) and shared_concepts)
    sa, sb = selection_states(a), selection_states(b)
    categorical_conflict = any(sa[k] != sb[k] and "unspecified" not in (sa[k], sb[k]) for k in sa.keys() & sb.keys())
    constraint_difference = bool(shared_concepts and (thresholds(a) or thresholds(b)) and thresholds(a) != thresholds(b))
    if ca or cb:
        score = 0.6 * concept_coverage + 0.2 * concept_jaccard + 0.2 * token_coverage
    else:
        # Neither clause carries a lexicon concept ("Assessment of ER and HER2
        # status as per local assessment"). Concept terms would be zero for a
        # perfect wording match, so fall back to wording alone.
        score = token_coverage
    if _fold(a) == _fold(b):
        score = 1.0
    if numeric_conflict or comparison_conflict or categorical_conflict:
        score *= 0.5
    if is_negative(a) != is_negative(b) and shared_concepts:
        score *= 0.5
    return dict(score=round(score, 4), concept_coverage=round(concept_coverage, 4),
                concept_jaccard=round(concept_jaccard, 4), token_jaccard=round(token_jaccard, 4),
                token_coverage=round(token_coverage, 4), shared_concepts=shared_concepts,
                numeric_conflict=numeric_conflict,
                comparison_conflict=comparison_conflict,
                categorical_conflict=categorical_conflict, constraint_difference=constraint_difference,
                polarity_conflict=is_negative(a) != is_negative(b))


def best_match(target: str, candidates: list[str]) -> dict:
    """The closest candidate clause to ``target``, or a null result."""
    if not candidates:
        return dict(index=None, score=0.0, basis="none", matched=False, shared_concepts=[])
    scored = [(clause_similarity(target, cand)["score"], i, cand) for i, cand in enumerate(candidates)]
    top_score, index, _ = max(scored, key=lambda row: (row[0], -row[1]))
    detail = clause_similarity(target, candidates[index])
    basis = "concept" if top_score >= _CONCEPT_THRESHOLD and detail["shared_concepts"] else "lexical"
    return dict(detail, index=index, basis=basis,
                matched=top_score >= _CONCEPT_THRESHOLD and not any(detail[k] for k in
                        ("numeric_conflict", "polarity_conflict", "comparison_conflict", "categorical_conflict", "constraint_difference")))


def contains_clause(target: str, candidates: list[str]) -> bool:
    """True when some candidate expresses the target restriction."""
    return best_match(target, candidates)["matched"]


def clause_delta(original: str, amended: str) -> dict:
    """Clauses added to and removed from a criteria text by an amendment."""
    before, after = split_clauses(original), split_clauses(amended)
    added = [c for c in after if not contains_clause(c, before)]
    removed = [c for c in before if not contains_clause(c, after)]
    return dict(added=added, removed=removed, before_count=len(before), after_count=len(after))


def option_text(option: dict) -> list[str]:
    """Every criterion string in one option, in a stable order."""
    rows = list(option.get("inclusion") or []) + list(option.get("exclusion") or [])
    out = []
    for row in rows:
        text = row.get("text") if isinstance(row, dict) else str(row)
        if text:
            out.append(text)
    return out


def scope_clauses(option: dict) -> list[str]:
    """Criteria that only restate the fixed parent population."""
    rows = list(option.get("inclusion") or []) + list(option.get("exclusion") or [])
    return [r["text"] for r in rows if isinstance(r, dict) and r.get("purpose") == "scope" and r.get("text")]


def distinguishing_clauses(option: dict) -> list[str]:
    """Criteria that make this option different from its parent population."""
    rows = list(option.get("inclusion") or []) + list(option.get("exclusion") or [])
    out = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("text"):
            continue
        if row.get("purpose") == "scope":
            continue
        out.append(row["text"])
    return out


def option_signature(option: dict) -> set[str]:
    """Concept set used to measure how distinct two options are."""
    sig: set[str] = set()
    for text in distinguishing_clauses(option):
        sig |= concepts(text)
    return sig


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0
