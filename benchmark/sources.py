"""Source catalog and existence checks for the reference-accuracy benchmark.

Two layers, deliberately separate:

* **Existence.** Does the cited source resolve to a real record? A PubMed PMID
  that 404s, or a source id the catalog does not know, is a fabricated or
  broken reference. This check is unambiguous and needs no judgement.
* **Support.** Does the source say what the claim says? That needs reading the
  source. In ``fetch`` mode this module pulls the abstract (Europe PMC, which
  is a real abstract, not a title) and the check compares against it. With no
  network it compares against the catalog's curated ``scope`` line, which is a
  human-written paraphrase — weaker, and reported as a different basis so the
  two are never silently mixed.

Fetched records are cached under ``benchmark/.cache/`` so a re-run costs nothing
and a reviewer can inspect exactly what was compared.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

CACHE = Path(os.getenv("BENCHMARK_CACHE", Path(__file__).with_name(".cache")))
USER_AGENT = "eligibility-benchmark/0.1 (research prototype; contact via repository)"
EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PUBMED = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


def _http(url: str, timeout: int = 25) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, ""


def pmid_from_url(url: str) -> str | None:
    match = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{4,9})", url or "")
    return match.group(1) if match else None


def _cached(name: str, producer):
    """Memoise a JSON record on disk, keyed by a filesystem-safe name."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', name)}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    value = producer()
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1))
    return value


class SourceCatalog:
    """A set of citable sources, keyed by the ids an agent is allowed to use."""

    def __init__(self, records: dict[str, dict], fetch: bool = False):
        self.records = records
        self.fetch = fetch

    @classmethod
    def from_demo(cls, fetch: bool = False) -> "SourceCatalog":
        """The catalog the milestone 1 demo cites, when its package is importable."""
        from milestone1.evidence import SOURCES
        from milestone1.population_library import POPULATION_SOURCES

        merged = {**SOURCES, **POPULATION_SOURCES}
        return cls({k: dict(v) for k, v in merged.items()}, fetch=fetch)

    @classmethod
    def from_json(cls, path: str, fetch: bool = False) -> "SourceCatalog":
        return cls(json.loads(Path(path).read_text()), fetch=fetch)

    def __contains__(self, source_id) -> bool:
        return source_id in self.records

    def known(self, source_id: str) -> bool:
        return source_id in self.records

    def scope_text(self, source_id: str) -> str:
        record = self.records.get(source_id) or {}
        return ". ".join(filter(None, [record.get("title", ""), record.get("scope", "")]))

    # -- existence -------------------------------------------------------
    def resolve(self, source_id: str) -> dict:
        record = self.records.get(source_id)
        if not record:
            return dict(source_id=source_id, status="missing", detail="source id is not in the catalog")
        url, pmid = record.get("url", ""), pmid_from_url(record.get("url", ""))
        if not self.fetch:
            return dict(source_id=source_id, status="unverified", url=url, pmid=pmid,
                        detail="offline mode: existence not re-checked")
        status = _cached(f"resolve_{source_id}", lambda: self._probe(url, pmid))
        return dict(source_id=source_id, url=url, pmid=pmid, **status)

    def _probe(self, url: str, pmid: str | None) -> dict:
        if pmid:
            code, body = _http(EUROPEPMC + "?query=" + urllib.request.quote(f"EXT_ID:{pmid} AND SRC:MED")
                               + "&format=json&resultType=lite")
            if code == 200:
                hits = json.loads(body).get("hitCount", 0)
                return dict(status="ok" if hits else "missing", http_status=code,
                            detail=f"Europe PMC hitCount={hits}")
            return dict(status="inaccessible", http_status=code, detail="Europe PMC request failed")
        if url:
            time.sleep(0.5)  # be polite to the publisher/regulator host
            code, _ = _http(url, timeout=30)
            if code in (200, 403):
                # 403 on a guidance page still means the record exists; the host
                # refuses automated clients. Marked so support checks fall back.
                return dict(status="ok" if code == 200 else "inaccessible", http_status=code,
                            detail="page exists" if code == 200 else "host refused automated fetch")
            return dict(status="missing" if code == 404 else "inaccessible", http_status=code,
                        detail=f"HTTP {code}")
        return dict(status="unverified", detail="no URL in catalog")

    # -- support ---------------------------------------------------------
    def evidence_text(self, source_id: str) -> dict:
        """Text to compare a claim against, and where it came from."""
        record = self.records.get(source_id) or {}
        pmid = pmid_from_url(record.get("url", ""))
        if self.fetch and pmid:
            abstract = _cached(f"abstract_{source_id}", lambda: self._abstract(pmid))
            if abstract.get("text"):
                return dict(text=abstract["text"], basis="abstract", title=abstract.get("title", ""))
        return dict(text=self.scope_text(source_id), basis="catalog_scope",
                    title=record.get("title", ""))

    def _abstract(self, pmid: str) -> dict:
        code, body = _http(EUROPEPMC + "?query=" + urllib.request.quote(f"EXT_ID:{pmid} AND SRC:MED")
                           + "&format=json&resultType=core")
        if code != 200:
            return dict(text="", title="")
        results = json.loads(body).get("resultList", {}).get("result", [])
        if not results:
            return dict(text="", title="")
        row = results[0]
        return dict(title=row.get("title", ""), text=row.get("abstractText", "") or "")


def sentence_support(claim: str, evidence: str) -> dict:
    """Best-matching sentence in the evidence for a claim.

    Deliberately simple: a concept-overlap score against each evidence sentence.
    It is a screening signal, not entailment, and the README says so.
    """
    from .normalize import clause_similarity

    sentences = [s.strip() for s in re.split(r"(?<=[.;])\s+", evidence or "") if len(s.strip()) > 25]
    if not sentences:
        return dict(score=0.0, sentence="", basis="empty", shared_concepts=[])
    scored = [(clause_similarity(claim, s)["score"], s) for s in sentences]
    score, sentence = max(scored, key=lambda row: row[0])
    detail = clause_similarity(claim, sentence)
    return dict(score=round(score, 4), sentence=sentence[:400],
                basis="concept" if detail["shared_concepts"] else "lexical",
                shared_concepts=detail["shared_concepts"],
                concept_coverage=detail["concept_coverage"],
                token_coverage=detail["token_coverage"],
                numeric_conflict=detail["numeric_conflict"],
                comparison_conflict=detail["comparison_conflict"],
                categorical_conflict=detail["categorical_conflict"],
                polarity_conflict=detail["polarity_conflict"])
