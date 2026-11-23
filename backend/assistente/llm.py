"""Cliente do OpenRouter (API compatível com OpenAI) com escolha de modelo grátis.

Sem `OPENROUTER_MODEL`, lê o catálogo do OpenRouter (cache de 1 h) e usa
modelos `:free` que aceitam `tools`, na ordem de `PREFERIDOS`. Se um modelo
falhar (429, 5xx, timeout), tenta o próximo. Modelos grátis mudam de nome e
somem com frequência: por isso o catálogo é a fonte e a lista é só semente.
"""

import logging
import time
from dataclasses import dataclass, field

import httpx
from django.conf import settings

log = logging.getLogger("ergo.llm")

URL_BASE = "https://openrouter.ai/api/v1"
PREFERIDOS = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]
TENTATIVAS = 3
TIMEOUT_S = 60.0
_cache: dict = {"quando": 0.0, "modelos": []}


class LLMIndisponivel(RuntimeError):
    """Sem chave, ou todos os modelos falharam: o chamador usa o modo sem IA."""


@dataclass
class RespostaLLM:
    modelo: str
    conteudo: str
    chamadas: list[dict] = field(default_factory=list)  # tool_calls no formato OpenAI
    tokens_entrada: int = 0
    tokens_saida: int = 0
    latencia_ms: int = 0
    mensagem_bruta: dict = field(default_factory=dict)


def _gratis_com_tools(m: dict) -> bool:
    preco = m.get("pricing") or {}
    gratis = all(str(preco.get(k, "1")) in ("0", "0.0") for k in ("prompt", "completion"))
    return gratis and "tools" in (m.get("supported_parameters") or [])


def modelos_candidatos(cliente: httpx.Client | None = None) -> list[str]:
    if settings.OPENROUTER_MODEL:
        return [settings.OPENROUTER_MODEL]
    if time.time() - _cache["quando"] < 3600 and _cache["modelos"]:
        return _cache["modelos"]
    try:
        c = cliente or httpx.Client(timeout=8)
        r = c.get(f"{URL_BASE}/models")
        r.raise_for_status()
        livres = [m["id"] for m in r.json().get("data", []) if _gratis_com_tools(m)]
        ordem = [m for m in PREFERIDOS if m in livres] + [m for m in livres if m not in PREFERIDOS]
        _cache.update(quando=time.time(), modelos=ordem or PREFERIDOS)
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("catálogo do OpenRouter indisponível (%s); usando a lista semente", exc)
        _cache.update(quando=time.time(), modelos=PREFERIDOS)
    return _cache["modelos"]


def conversar(mensagens: list[dict], ferramentas: list[dict], registrar=None) -> RespostaLLM:
    """Uma ida ao modelo. `registrar(modelo, ok, erro, resposta)` audita cada tentativa."""
    if not settings.OPENROUTER_APIKEY:
        raise LLMIndisponivel("OPENROUTER_APIKEY não configurada")
    cabecalhos = {
        "Authorization": f"Bearer {settings.OPENROUTER_APIKEY}",
        "X-Title": "Ergo Assist AI",
    }
    ultimo_erro = ""
    with httpx.Client(timeout=TIMEOUT_S, headers=cabecalhos) as cliente:
        for modelo in modelos_candidatos()[:TENTATIVAS]:
            inicio = time.monotonic()
            try:
                r = cliente.post(
                    f"{URL_BASE}/chat/completions",
                    json={
                        "model": modelo,
                        "messages": mensagens,
                        "temperature": 0.2,
                        "max_tokens": 1200,
                        **({"tools": ferramentas, "tool_choice": "auto"} if ferramentas else {}),
                    },
                )
                latencia = int((time.monotonic() - inicio) * 1000)
                if r.status_code != 200:
                    raise httpx.HTTPStatusError(r.text[:200], request=r.request, response=r)
                corpo = r.json()
                if "error" in corpo:
                    raise ValueError(str(corpo["error"])[:200])
                msg = corpo["choices"][0]["message"]
                uso = corpo.get("usage") or {}
                resposta = RespostaLLM(
                    modelo=corpo.get("model", modelo),
                    conteudo=msg.get("content") or "",
                    chamadas=msg.get("tool_calls") or [],
                    tokens_entrada=uso.get("prompt_tokens", 0),
                    tokens_saida=uso.get("completion_tokens", 0),
                    latencia_ms=latencia,
                    mensagem_bruta=msg,
                )
                if registrar:
                    registrar(modelo, True, "", resposta)
                return resposta
            except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
                ultimo_erro = f"{modelo}: {exc}"[:300]
                log.warning("LLM falhou: %s", ultimo_erro)
                if registrar:
                    registrar(modelo, False, ultimo_erro, None)
    raise LLMIndisponivel(ultimo_erro or "nenhum modelo respondeu")
