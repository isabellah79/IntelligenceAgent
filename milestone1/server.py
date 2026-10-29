"""Run with: python3 -m milestone1.server (Python standard library only)."""
import argparse
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import sqlite3
import uuid
from urllib.parse import urlparse

from .agent import compare, model_configured, synthesize
from .evidence import DEFAULT_CASE, OPTIONS, SOURCES, VERSION, AS_OF
from .forecasting import examples, evaluate_forecast
from .scoring import WEIGHT_PRESETS
from .endpoint_comparison import DEFAULT_DESIGN
from .llm import ModelServiceError, model_status
from .populations import (DEFAULT_CONTEXT as POPULATION_CONTEXT, DEFAULT_DESIGN as POPULATION_DESIGN,
                          propose, review_populations, attach_population_judgment, all_populations)
from .population_library import POPULATION_SOURCES

ROOT = Path(__file__).parent
LOG = logging.getLogger(__name__)


def init_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created TEXT, result TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, run_id TEXT, created TEXT, action TEXT, option_id TEXT, comment TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS forecast_runs (id TEXT PRIMARY KEY, created TEXT, result TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS population_feedback (id TEXT PRIMARY KEY, run_id TEXT, created TEXT, treatment_id TEXT, population_id TEXT, action TEXT, comment TEXT)")


def apply_judgment_provenance(result, parent_result, parent_id):
    """Record exact reviewed factor changes without attributing other edits to a model."""
    if parent_result.get("mode") != "model_synthesis":
        raise ValueError("Parent run must contain a model review")
    if parent_result["case"] != result["case"]:
        raise ValueError("Case changed; request a new model review before applying its suggestions")
    for key,value in parent_result["endpoint_design"].items():
        if key != "factor_overrides" and result["endpoint_design"].get(key) != value:
            raise ValueError("Forecast assumptions changed; request a new model review before applying its suggestions")
    applied=[]
    for proposal in parent_result.get("model_judgments",[]):
        value=result["endpoint_design"]["factor_overrides"].get(proposal["option_id"],{}).get(proposal["factor_id"])
        if value == proposal["proposed_factor"]:
            applied.append(proposal)
    if not applied:
        raise ValueError("No reviewed model factor changes were found in this calculation")
    result.update(parent_model_judgment_run_id=parent_id,applied_model_judgments=applied,
                  parent_model_metadata=parent_result.get("model_metadata"),
                  parent_model_synthesis=parent_result["synthesis"])


def load_run(path, run_id):
    try:
        uuid.UUID(run_id)
    except (ValueError,AttributeError,TypeError):
        return None
    with sqlite3.connect(path) as db:
        stored=db.execute("SELECT result FROM runs WHERE id = ?",(run_id,)).fetchone()
        if not stored:
            return None
        result=json.loads(stored[0])
        result["saved_reviews"]=[dict(id=row[0],option_id=row[1],action=row[2],comment=row[3]) for row in
                                 db.execute("SELECT id,option_id,action,comment FROM feedback WHERE run_id = ? ORDER BY created",(run_id,))]
        if result.get("task")=="population_design":
            result["saved_reviews"]=[dict(id=row[0],treatment_id=row[1],population_id=row[2],action=row[3],comment=row[4]) for row in
                db.execute("SELECT id,treatment_id,population_id,action,comment FROM population_feedback WHERE run_id = ? ORDER BY created",(run_id,))]
    return result


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "static"), **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        super().end_headers()

    def reply(self, value, status=200):
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if not self.valid_host():
            return self.reply({"error": "Use the localhost demo URL"}, 403)
        path = urlparse(self.path).path
        if path == "/api/bootstrap":
            return self.reply(dict(default_case=DEFAULT_CASE, sources=SOURCES, evidence_version=VERSION,
                evidence_as_of=AS_OF, model_configured=model_configured(),
                forecast_examples=examples(), weight_presets=WEIGHT_PRESETS,
                option_names=[dict(id=o["id"], title=o["title"]) for o in OPTIONS], endpoint_design=DEFAULT_DESIGN,
                model_status=model_status(),population_context=POPULATION_CONTEXT,population_design=POPULATION_DESIGN,
                population_sources=POPULATION_SOURCES))
        if path.startswith("/api/runs/"):
            result=load_run(self.server.db_path,path.removeprefix("/api/runs/"))
            return self.reply(result if result else {"error":"Saved review was not found"},200 if result else 404)
        if path.startswith("/api/"):
            return self.reply({"error": "Not found"}, 404)
        if path not in {"/", "/index.html", "/legacy.html", "/app.js", "/styles.css", "/population-app.js", "/population.css", "/favicon.ico"}:
            return self.reply({"error": "Not found"}, 404)
        return super().do_GET()

    def do_POST(self):
        if not self.valid_host():
            return self.reply({"error": "Use the localhost demo URL"}, 403)
        # Browser writes must originate from this local app. No CORS wildcard.
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + self.headers.get("Host", ""):
            return self.reply({"error": "Cross-origin requests are not allowed"}, 403)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 32000:
                return self.reply({"error": "Request must be 1–32000 bytes"}, 413)
            if self.headers.get_content_type() != "application/json":
                return self.reply({"error": "Use application/json"}, 415)
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("Request must be a JSON object")
            path = urlparse(self.path).path
            if path == "/api/populations":
                result=propose(payload.get("context"),payload.get("design"),payload.get("focus_treatment_id","elacestrant"))
                mode=payload.get("mode","curated")
                if mode not in {"curated","model"}:raise ValueError("Invalid population-review mode")
                parent=payload.get("judgment_parent_run")
                if parent and mode!="curated":raise ValueError("Apply reviewed weights in curated calculation mode")
                if mode=="model":
                    try:result=review_populations(result)
                    except ModelServiceError as exc:return self.reply({"error":str(exc)},502)
                if parent:
                    stored=load_run(self.server.db_path,parent)
                    if not stored:raise ValueError("Parent population review was not found")
                    attach_population_judgment(result,stored,parent)
                result["run_id"]=str(uuid.uuid4());result["created_at"]=datetime.now(timezone.utc).isoformat()
                with sqlite3.connect(self.server.db_path) as db:
                    db.execute("INSERT INTO runs VALUES (?,?,?)",(result["run_id"],result["created_at"],json.dumps(result)))
                return self.reply(result)
            if path == "/api/population-feedback":
                action=payload.get("action");comment=payload.get("comment","")
                if action not in {"select","edit","reject"}:raise ValueError("Invalid population feedback action")
                if not isinstance(comment,str) or len(comment)>12000 or (action=="edit" and not comment.strip()):
                    raise ValueError("Provide a proposed edit; comments may contain at most 12000 characters")
                run_id=payload.get("run_id");stored=load_run(self.server.db_path,run_id)
                if not stored or stored.get("task")!="population_design":raise ValueError("Population-design run not found")
                pid=payload.get("population_id");populations=all_populations(stored["treatments"])
                if not isinstance(pid,str) or pid not in populations:raise ValueError("Population is not part of this saved run")
                tid=populations[pid]["treatment_id"];feedback_id=str(uuid.uuid4())
                with sqlite3.connect(self.server.db_path) as db:
                    db.execute("INSERT INTO population_feedback VALUES (?,?,?,?,?,?,?)",(feedback_id,run_id,datetime.now(timezone.utc).isoformat(),tid,pid,action,comment.strip()))
                return self.reply(dict(id=feedback_id,run_id=run_id,treatment_id=tid,population_id=pid,action=action,comment=comment.strip()),201)
            if path == "/api/compare":
                result = compare(payload.get("case"), payload.get("weights"), payload.get("endpoint_design"))
                mode = payload.get("mode", "curated")
                if mode not in {"curated", "model"}:
                    raise ValueError("Invalid comparison mode")
                if mode == "model":
                    try:
                        result = synthesize(result)
                    except ValueError:
                        raise
                    except ModelServiceError as exc:
                        return self.reply({"error":str(exc)},502)
                    except Exception:
                        # Never echo upstream bodies/headers, which may contain secrets.
                        LOG.warning("Model synthesis failed; no model output was used")
                        return self.reply({"error": "Model service unavailable. Retry or choose curated evidence mode."}, 502)
                parent=payload.get("judgment_parent_run")
                if parent:
                    if not isinstance(parent,str) or mode != "curated":
                        raise ValueError("Invalid parent judgment run")
                    with sqlite3.connect(self.server.db_path) as db:
                        stored=db.execute("SELECT result FROM runs WHERE id = ?",(parent,)).fetchone()
                    if not stored:
                        raise ValueError("Parent judgment run was not found")
                    parent_result=json.loads(stored[0])
                    apply_judgment_provenance(result,parent_result,parent)
                result["run_id"] = str(uuid.uuid4())
                result["created_at"] = datetime.now(timezone.utc).isoformat()
                with sqlite3.connect(self.server.db_path) as db:
                    db.execute("INSERT INTO runs VALUES (?, ?, ?)", (result["run_id"], result["created_at"], json.dumps(result)))
                return self.reply(result)
            if path == "/api/forecast":
                option_id = payload.get("option_id")
                if option_id is not None and (not isinstance(option_id, str) or option_id not in {o["id"] for o in OPTIONS}):
                    raise ValueError("Unknown treatment context")
                result = evaluate_forecast(payload.get("forecast_case"), option_id)
                result["forecast_run_id"] = str(uuid.uuid4())
                result["created_at"] = datetime.now(timezone.utc).isoformat()
                with sqlite3.connect(self.server.db_path) as db:
                    db.execute("INSERT INTO forecast_runs VALUES (?, ?, ?)",
                               (result["forecast_run_id"], result["created_at"], json.dumps(result)))
                return self.reply(result)
            if path == "/api/feedback":
                action = payload.get("action")
                option_id = payload.get("option_id")
                comment = payload.get("comment", "")
                run_id = payload.get("run_id")
                if action not in {"select", "edit", "reject"} or option_id not in {o["id"] for o in OPTIONS}:
                    raise ValueError("Invalid action or option")
                if not isinstance(comment, str) or len(comment) > 4000:
                    raise ValueError("Comment must be at most 4000 characters")
                if action == "edit" and not comment.strip():
                    raise ValueError("Describe the proposed edit")
                if not isinstance(run_id, str):
                    raise ValueError("run_id must be a string")
                with sqlite3.connect(self.server.db_path) as db:
                    row = db.execute("SELECT result FROM runs WHERE id = ?", (run_id,)).fetchone()
                    if not row or option_id not in {o["id"] for o in json.loads(row[0])["options"]}:
                        raise ValueError("Run or option not found")
                    feedback_id = str(uuid.uuid4())
                    db.execute("INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?)",
                        (feedback_id, run_id, datetime.now(timezone.utc).isoformat(), action, option_id, comment.strip()))
                return self.reply({"id": feedback_id, "saved": True}, 201)
            return self.reply({"error": "Not found"}, 404)
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            return self.reply({"error": str(exc)}, 400)
        except Exception:
            LOG.exception("Local request failed")
            return self.reply({"error": "Local server error; see server log"}, 500)

    def valid_host(self):
        return self.headers.get("Host") in {
            f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}


def make_server(port=8765, db_path=None):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.db_path = Path(db_path or os.getenv("DEMO_DB_PATH", str(ROOT / ".local" / "demo.sqlite3")))
    init_db(server.db_path)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    server = make_server(args.port)
    print(f"Population design demo: http://127.0.0.1:{server.server_port}", flush=True)
    print("Population drafts and researcher reviews are saved locally.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
