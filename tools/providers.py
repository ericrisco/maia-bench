"""Minimal clients to talk to a model, with no external dependencies.

A model is written as `provider:model`:

    ollama:gemma4:e4b                  Ollama (OLLAMA_HOST, default http://localhost:11434; OLLAMA_TOKEN if private)
    ollamacloud:gpt-oss:120b           Ollama Cloud (OLLAMA_API_KEY)
    openai:gpt-5                       OpenAI (OPENAI_API_KEY)
    anthropic:claude-sonnet-5-5        Anthropic (ANTHROPIC_API_KEY)
    openrouter:meta-llama/llama-4      OpenRouter (OPENROUTER_API_KEY)
    vertex:google/gemini-3.8-flash     Vertex AI, OpenAI-compatible endpoint (gcloud + GCP_PROJECT)
    vertexclaude:claude-haiku-5-5      Claude on Vertex AI (rawPredict, gcloud + GCP_PROJECT)

`call(model, messages)` returns {"text", "input_tokens", "output_tokens"} and retries transient errors.
"""
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request

PROVIDERS = ("ollama", "ollamacloud", "openai", "anthropic", "openrouter", "vertex", "vertexclaude")
RETRIES = 8

_token = {"value": None, "at": 0}
_lock = threading.Lock()


class ModelError(RuntimeError):
    pass


def split_model(model):
    provider, _, name = model.partition(":")
    if provider not in PROVIDERS or not name:
        raise ValueError(f"model must be provider:name with provider in {PROVIDERS}: {model!r}")
    return provider, name


def _gcloud_token():
    with _lock:
        if not _token["value"] or time.time() - _token["at"] > 2400:
            r = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True)
            if r.returncode != 0:
                raise ModelError("gcloud auth print-access-token failed")
            _token["value"], _token["at"] = r.stdout.strip(), time.time()
        return _token["value"]


def _key(var):
    v = os.environ.get(var)
    if not v:
        raise ModelError(f"needs the environment variable {var}")
    return v


def _post(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json",
                                                                               **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _openai_compatible(provider, name, messages, temperature, max_tokens, reasoning=None):
    if provider == "ollama":
        base = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        url, headers = f"{base}/v1/chat/completions", {}
        # A private Ollama on Cloud Run needs a Google identity token (gcloud auth print-identity-token).
        if os.environ.get("OLLAMA_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['OLLAMA_TOKEN']}"
    elif provider == "ollamacloud":
        url = "https://ollama.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {_key('OLLAMA_API_KEY')}"}
    elif provider == "openai":
        url, headers = "https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {_key('OPENAI_API_KEY')}"}
    elif provider == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {_key('OPENROUTER_API_KEY')}",
                   "HTTP-Referer": "https://github.com/ericrisco/maia-bench", "X-Title": "maia-bench"}
    else:  # vertex
        project = os.environ.get("GCP_PROJECT", "maia-andorra")
        url = (f"https://aiplatform.googleapis.com/v1/projects/{project}"
               "/locations/global/endpoints/openapi/chat/completions")
        headers = {"Authorization": f"Bearer {_gcloud_token()}", "x-goog-user-project": project}
    body = {"model": name, "messages": messages, "temperature": temperature}
    # OpenAI reasoning models do not accept max_tokens; everyone else does.
    body["max_completion_tokens" if provider == "openai" else "max_tokens"] = max_tokens
    if reasoning:  # reasoning_effort: low|medium|high (reasoning models); OpenRouter wants it as an object
        if provider == "openrouter":
            # a number caps the reasoning tokens, so there is always room left for the answer
            body["reasoning"] = {"max_tokens": int(reasoning)} if str(reasoning).isdigit() else {"effort": reasoning}
        else:
            body["reasoning_effort"] = reasoning
    try:
        d = _post(url, body, headers, 600)
    except urllib.error.HTTPError as e:
        err_body = e.read()[:400].decode(errors="replace")
        # Some models only accept the default temperature: retry without it.
        if e.code == 400 and "temperature" in err_body:
            body.pop("temperature")
            d = _post(url, body, headers, 600)
        else:
            raise urllib.error.HTTPError(e.url, e.code, err_body, e.headers, None)
    m = d["choices"][0]["message"]
    u = d.get("usage") or {}
    return {"text": m.get("content") or "", "input_tokens": u.get("prompt_tokens", 0),
            "output_tokens": u.get("completion_tokens", 0)}


def _anthropic(name, messages, temperature, max_tokens):
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [m for m in messages if m["role"] != "system"]
    body = {"model": name, "max_tokens": max_tokens, "temperature": temperature, "messages": rest}
    if system:
        body["system"] = system
    d = _post("https://api.anthropic.com/v1/messages", body,
              {"x-api-key": _key("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"}, 600)
    text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    u = d.get("usage") or {}
    return {"text": text, "input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0)}


def _vertex_claude(name, messages, max_tokens):
    # No temperature: since 2026-10-21 the Claude API rejects sampling parameters.
    project = os.environ.get("GCP_PROJECT", "maia-andorra")
    url = (f"https://aiplatform.googleapis.com/v1/projects/{project}/locations/global"
           f"/publishers/anthropic/models/{name}:rawPredict")
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    body = {"anthropic_version": "vertex-2023-10-16", "max_tokens": max_tokens,
            "messages": [m for m in messages if m["role"] != "system"]}
    if system:
        body["system"] = system
    d = _post(url, body, {"Authorization": f"Bearer {_gcloud_token()}", "x-goog-user-project": project}, 600)
    text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    u = d.get("usage") or {}
    return {"text": text, "input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0)}


def call(model, messages, temperature=0, max_tokens=4000, reasoning=None):
    provider, name = split_model(model)
    for attempt in range(RETRIES):
        try:
            if provider == "anthropic":
                return _anthropic(name, messages, temperature, max_tokens)
            if provider == "vertexclaude":
                return _vertex_claude(name, messages, max_tokens)
            return _openai_compatible(provider, name, messages, temperature, max_tokens, reasoning)
        except urllib.error.HTTPError as e:
            if e.code == 401 and provider in ("vertex", "vertexclaude"):
                _token["value"] = None  # expired token: ask for a new one
            if e.code in (401, 408, 429, 500, 502, 503, 504, 529) and attempt < RETRIES - 1:
                time.sleep(min(120, 5 * 2 ** attempt))
                continue
            raise ModelError(f"HTTP {e.code}: {e.msg}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < RETRIES - 1:
                time.sleep(min(120, 5 * 2 ** attempt))
                continue
            raise ModelError(f"network: {e}") from None
    raise ModelError("no answer")
