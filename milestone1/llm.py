"""Server-side Vertex Gemini / Anthropic adapters. Never log credentials.

The local Vertex adapter uses gcloud Application Default Credentials, avoiding
a downloaded service-account key or an extra SDK dependency in this prototype.
"""
import json
import http.client
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import urllib.error
import urllib.request

SETTINGS_FILE = Path(__file__).with_name("vertex_settings.json")


class ModelServiceError(RuntimeError):
    """A safe, actionable error without upstream headers or credential values."""


def settings():
    config = json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}
    provider = os.getenv("LLM_PROVIDER", config.get("provider", "anthropic"))
    return dict(provider=provider,
                project=os.getenv("GOOGLE_CLOUD_PROJECT", config.get("project", "")),
                location=os.getenv("GOOGLE_CLOUD_LOCATION", config.get("location", "")),
                model=os.getenv("GEMINI_MODEL", config.get("model", "")) if provider == "vertex" else os.getenv("ANTHROPIC_MODEL", ""))


def adc_path():
    return Path(os.getenv("CLOUDSDK_CONFIG", str(Path.home()/".config"/"gcloud"))) / "application_default_credentials.json"


def vertex_url(config):
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", config["project"]):
        raise ValueError("Set a valid Google Cloud project ID")
    if not re.fullmatch(r"global|[a-z]+-[a-z]+[0-9]+", config["location"]):
        raise ValueError("Set a supported Vertex location, for example global")
    if not re.fullmatch(r"gemini-[a-zA-Z0-9.-]+", config["model"]):
        raise ValueError("Set a valid Gemini model ID")
    host = "aiplatform.googleapis.com" if config["location"] == "global" else config["location"]+"-aiplatform.googleapis.com"
    return f"https://{host}/v1/projects/{config['project']}/locations/{config['location']}/publishers/google/models/{config['model']}:generateContent"


def model_status():
    config = settings()
    ready = False
    detail = ""
    if config["provider"] == "vertex":
        try:
            vertex_url(config)
            if not shutil.which("gcloud"):
                detail = "Google Cloud CLI is not available to the server"
            elif not adc_path().is_file():
                detail = "Run gcloud auth application-default login and set the quota project"
            else:
                ready = True
                detail = "Vertex configured; sign-in, permissions and model access are checked when a request is made"
        except ValueError as exc:
            detail = str(exc)
    elif config["provider"] == "anthropic":
        ready = bool(os.getenv("ANTHROPIC_API_KEY") and config["model"])
        detail = "Anthropic configured" if ready else "Anthropic API key/model not configured"
    else:
        detail = "Unknown LLM_PROVIDER; choose vertex or anthropic"
    return dict(**config, configured=ready, detail=detail)


def adc_access_token():
    gcloud = shutil.which("gcloud")
    if not gcloud:
        raise ModelServiceError("Install the Google Cloud CLI for local Vertex ADC authentication")
    env = dict(os.environ, CLOUDSDK_CORE_DISABLE_FILE_LOGGING="true", CLOUDSDK_CORE_DISABLE_PROMPTS="1")
    # Pass the host's existing proxy selection to gcloud's bundled runtime too.
    # This does not change network settings or save any proxy credentials.
    for kind,proxy in urllib.request.getproxies().items():
        if kind in {"http","https"}:
            env.setdefault(kind.upper()+"_PROXY",proxy)
    try:
        process = subprocess.run([gcloud,"auth","application-default","print-access-token"],
            capture_output=True, text=True, timeout=40, env=env)
    except (OSError,subprocess.TimeoutExpired):
        raise ModelServiceError("Could not obtain a Vertex access token; check local gcloud ADC sign-in") from None
    token = process.stdout.strip()
    if process.returncode or not token or any(c.isspace() for c in token):
        raise ModelServiceError("Vertex ADC sign-in is missing or expired. Run gcloud auth application-default login")
    return token


def ssl_context():
    context=ssl.create_default_context()
    try:
        import certifi
        context.load_verify_locations(cafile=certifi.where())
    except ImportError:
        gcloud=shutil.which("gcloud")
        bundle=Path(gcloud).resolve().parent.parent/"lib/third_party/certifi/cacert.pem" if gcloud else None
        if bundle and bundle.is_file():
            context.load_verify_locations(cafile=str(bundle))
    return context


def _post(request):
    try:
        with urllib.request.urlopen(request, timeout=120, context=ssl_context()) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        hints={400:"Check model support and request settings",401:"Refresh Application Default Credentials",
               403:"Check Vertex API enablement, billing and Vertex AI User access for the signed-in identity",
               404:"Check the exact model ID and its availability in the selected location",
               429:"Check the project's model quota or retry later"}
        raise ModelServiceError(f"Model service returned HTTP {exc.code}. {hints.get(exc.code,'Retry or check the model service status')}.") from None
    except (urllib.error.URLError,TimeoutError,http.client.HTTPException,OSError):
        raise ModelServiceError("Model service could not be reached; check network access and retry") from None


def generate(system, user_text, max_tokens=8192):
    config = settings()
    if config["provider"] == "vertex":
        url=vertex_url(config)
        body=dict(systemInstruction=dict(parts=[dict(text=system)]),
                  contents=[dict(role="user",parts=[dict(text=user_text)])],
                  generationConfig=dict(responseMimeType="application/json",maxOutputTokens=max_tokens))
        if config["model"].startswith("gemini-3"):
            body["generationConfig"]["thinkingConfig"]={"thinkingLevel":"LOW"}
        token=adc_access_token()
        request=urllib.request.Request(url,data=json.dumps(body).encode(),headers={
            "Authorization":"Bearer "+token,"Content-Type":"application/json",
            "x-goog-user-project":config["project"]})
        payload=_post(request)
        candidates=payload.get("candidates",[])
        if not candidates:
            raise ModelServiceError("Gemini returned no candidate; the request may have been blocked")
        candidate=candidates[0]
        if candidate.get("finishReason") != "STOP":
            raise ModelServiceError("Gemini did not complete a usable response; no judgments were applied")
        text="".join(p.get("text","") for p in candidate.get("content",{}).get("parts",[]) if not p.get("thought"))
        usage=payload.get("usageMetadata",{})
        reported_model=payload.get("modelVersion")
    elif config["provider"] == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY") or not config["model"]:
            raise ModelServiceError("Anthropic API key/model not configured")
        body=dict(model=config["model"],max_tokens=max_tokens,system=system,messages=[dict(role="user",content=user_text)])
        request=urllib.request.Request("https://api.anthropic.com/v1/messages",data=json.dumps(body).encode(),headers={
            "Content-Type":"application/json","x-api-key":os.environ["ANTHROPIC_API_KEY"],"anthropic-version":"2023-06-01"})
        payload=_post(request)
        text="".join(p.get("text","") for p in payload.get("content",[]) if p.get("type")=="text")
        usage=payload.get("usage",{})
        reported_model=payload.get("model")
    else:
        raise ValueError("Unknown LLM provider")
    return text,dict(provider=config["provider"],model=config["model"],project=config["project"] if config["provider"]=="vertex" else None,
                     location=config["location"] if config["provider"]=="vertex" else None,
                     reported_model=reported_model,usage=usage)
