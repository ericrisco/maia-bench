"""Clients mínims per parlar amb un model, sense dependències externes.

Un model s'escriu com `proveidor:model`:

    ollama:gemma4:e4b                  Ollama (OLLAMA_HOST, per defecte http://localhost:11434; OLLAMA_TOKEN si és privat)
    ollamacloud:gpt-oss:120b           Ollama Cloud (OLLAMA_API_KEY)
    openai:gpt-5                       OpenAI (OPENAI_API_KEY)
    anthropic:claude-sonnet-5-5        Anthropic (ANTHROPIC_API_KEY)
    openrouter:meta-llama/llama-4      OpenRouter (OPENROUTER_API_KEY)
    vertex:google/gemini-3.8-flash     Vertex AI, endpoint compatible amb OpenAI (gcloud + GCP_PROJECT)
    vertexclaude:claude-haiku-5-5      Claude a Vertex AI (rawPredict, gcloud + GCP_PROJECT)

`crida(model, missatges)` retorna {"text", "tokens_entrada", "tokens_sortida"} i reintenta els errors temporals.
"""
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request

PROVEIDORS = ("ollama", "ollamacloud", "openai", "anthropic", "openrouter", "vertex", "vertexclaude")
REINTENTS = 8

_tok = {"v": None, "t": 0}
_lock = threading.Lock()


class ErrorModel(RuntimeError):
    pass


def separa(model):
    prov, _, nom = model.partition(":")
    if prov not in PROVEIDORS or not nom:
        raise ValueError(f"model ha de ser proveidor:nom amb proveidor a {PROVEIDORS}: {model!r}")
    return prov, nom


def _token_gcloud():
    with _lock:
        if not _tok["v"] or time.time() - _tok["t"] > 2400:
            r = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True)
            if r.returncode != 0:
                raise ErrorModel("gcloud auth print-access-token ha fallat")
            _tok["v"], _tok["t"] = r.stdout.strip(), time.time()
        return _tok["v"]


def _clau(var):
    v = os.environ.get(var)
    if not v:
        raise ErrorModel(f"cal la variable d'entorn {var}")
    return v


def _post(url, cos, capcaleres, timeout):
    req = urllib.request.Request(url, data=json.dumps(cos).encode(), headers={"Content-Type": "application/json",
                                                                              **capcaleres})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _openai_compatible(prov, nom, missatges, temperatura, max_tokens, raonament=None):
    if prov == "ollama":
        base = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        url, cap = f"{base}/v1/chat/completions", {}
        # Un Ollama privat a Cloud Run demana un token d'identitat de Google (gcloud auth print-identity-token).
        if os.environ.get("OLLAMA_TOKEN"):
            cap["Authorization"] = f"Bearer {os.environ['OLLAMA_TOKEN']}"
    elif prov == "ollamacloud":
        url = "https://ollama.com/v1/chat/completions"
        cap = {"Authorization": f"Bearer {_clau('OLLAMA_API_KEY')}"}
    elif prov == "openai":
        url, cap = "https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {_clau('OPENAI_API_KEY')}"}
    elif prov == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        cap = {"Authorization": f"Bearer {_clau('OPENROUTER_API_KEY')}",
               "HTTP-Referer": "https://github.com/ericrisco/maia-bench", "X-Title": "maia-bench"}
    else:  # vertex
        projecte = os.environ.get("GCP_PROJECT", "maia-andorra")
        url = (f"https://aiplatform.googleapis.com/v1/projects/{projecte}"
               "/locations/global/endpoints/openapi/chat/completions")
        cap = {"Authorization": f"Bearer {_token_gcloud()}", "x-goog-user-project": projecte}
    cos = {"model": nom, "messages": missatges, "temperature": temperatura}
    # Els models de raonament d'OpenAI no accepten max_tokens; la resta sí.
    cos["max_completion_tokens" if prov == "openai" else "max_tokens"] = max_tokens
    if raonament:  # reasoning_effort: low|medium|high (models de raonament)
        cos["reasoning_effort"] = raonament
    try:
        d = _post(url, cos, cap, 600)
    except urllib.error.HTTPError as e:
        cos_err = e.read()[:400].decode(errors="replace")
        # Alguns models només accepten la temperatura per defecte: es reintenta sense.
        if e.code == 400 and "temperature" in cos_err:
            cos.pop("temperature")
            d = _post(url, cos, cap, 600)
        else:
            raise urllib.error.HTTPError(e.url, e.code, cos_err, e.headers, None)
    m = d["choices"][0]["message"]
    u = d.get("usage") or {}
    return {"text": m.get("content") or "", "tokens_entrada": u.get("prompt_tokens", 0),
            "tokens_sortida": u.get("completion_tokens", 0)}


def _anthropic(nom, missatges, temperatura, max_tokens):
    sistema = "\n".join(m["content"] for m in missatges if m["role"] == "system")
    resta = [m for m in missatges if m["role"] != "system"]
    cos = {"model": nom, "max_tokens": max_tokens, "temperature": temperatura, "messages": resta}
    if sistema:
        cos["system"] = sistema
    d = _post("https://api.anthropic.com/v1/messages", cos,
              {"x-api-key": _clau("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"}, 600)
    text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    u = d.get("usage") or {}
    return {"text": text, "tokens_entrada": u.get("input_tokens", 0), "tokens_sortida": u.get("output_tokens", 0)}


def _vertex_claude(nom, missatges, max_tokens):
    # Sense temperatura: des del 21/10/2026 l'API de Claude rebutja els paràmetres de mostreig.
    projecte = os.environ.get("GCP_PROJECT", "maia-andorra")
    url = (f"https://aiplatform.googleapis.com/v1/projects/{projecte}/locations/global"
           f"/publishers/anthropic/models/{nom}:rawPredict")
    sistema = "\n".join(m["content"] for m in missatges if m["role"] == "system")
    cos = {"anthropic_version": "vertex-2023-10-16", "max_tokens": max_tokens,
           "messages": [m for m in missatges if m["role"] != "system"]}
    if sistema:
        cos["system"] = sistema
    d = _post(url, cos, {"Authorization": f"Bearer {_token_gcloud()}", "x-goog-user-project": projecte}, 600)
    text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    u = d.get("usage") or {}
    return {"text": text, "tokens_entrada": u.get("input_tokens", 0), "tokens_sortida": u.get("output_tokens", 0)}


def crida(model, missatges, temperatura=0, max_tokens=4000, raonament=None):
    prov, nom = separa(model)
    for intent in range(REINTENTS):
        try:
            if prov == "anthropic":
                return _anthropic(nom, missatges, temperatura, max_tokens)
            if prov == "vertexclaude":
                return _vertex_claude(nom, missatges, max_tokens)
            return _openai_compatible(prov, nom, missatges, temperatura, max_tokens, raonament)
        except urllib.error.HTTPError as e:
            if e.code == 401 and prov in ("vertex", "vertexclaude"):
                _tok["v"] = None  # token caducat: se'n demana un de nou
            if e.code in (401, 408, 429, 500, 502, 503, 504, 529) and intent < REINTENTS - 1:
                time.sleep(min(120, 5 * 2 ** intent))
                continue
            raise ErrorModel(f"HTTP {e.code}: {e.msg}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if intent < REINTENTS - 1:
                time.sleep(min(120, 5 * 2 ** intent))
                continue
            raise ErrorModel(f"xarxa: {e}") from None
    raise ErrorModel("sense resposta")
