"""Cliente do OpenRouter (API compatível com OpenAI) com cadeia de modelos.

Ordem de tentativa: os modelos de `OPENROUTER_MODELS` (pagos e baratos, ex.:
DeepSeek V4.1 Flash e Claude Haiku 5.5), depois os `:free` com `tools` do
catálogo do OpenRouter (cache de 1 h), na ordem de `PREFERIDOS`. Se um modelo
falhar (429, 5xx, timeout), tenta o próximo. O custo real de cada chamada vem
do próprio OpenRouter (`usage.cost`, em dólares) e é auditado em ChamadaLLM.
"""

import logging
import time
from dataclasses import dataclass, field

import httpx
from django.conf import settings

log = logging.getLogger("ergo.llm")

URL_BASE = "https://openrouter.ai/api/v1"
# Ordem medida em 23/11/2026 com uma pergunta de recomendação (tool calling
# certo e latência). Os da lista antiga (Qwen3, GPT-OSS, Llama 3.3) deixaram de
# ser grátis; Gemma e Ling estavam dando 429 do provedor nesse dia.
PREFERIDOS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",  # 5,9 s, tool certa
    "nvidia/nemotron-3.5-super-vl:free",  # 3,0 s, tool certa
    "baidu/ernie-5.5-flash-preview:free",  # 1,6 s, tool certa (+1 chamada extra)
    "google/gemma-4-31b-it:free",
    "inclusionai/ling-3.2-flash:free",
]
TENTATIVAS = 4
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
    custo_usd: float = 0.0
    mensagem_bruta: dict = field(default_factory=dict)


def _gratis_com_tools(m: dict) -> bool:
    preco = m.get("pricing") or {}
    gratis = all(str(preco.get(k, "1")) in ("0", "0.0") for k in ("prompt", "completion"))
    return gratis and "tools" in (m.get("supported_parameters") or [])


def modelos_candidatos(cliente: httpx.Client | None = None) -> list[str]:
    if settings.OPENROUTER_MODEL:
        return [settings.OPENROUTER_MODEL]
    pagos = list(settings.OPENROUTER_MODELS)
    return pagos + [m for m in _modelos_gratis(cliente) if m not in pagos]


def _modelos_gratis(cliente: httpx.Client | None = None) -> list[str]:
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


def conversar(
    mensagens: list[dict],
    ferramentas: list[dict],
    registrar=None,
    tool_choice: str = "auto",
    max_tokens: int = 2500,  # respostas com tabela de comparação passam de 1.200
) -> RespostaLLM:
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
                        "max_tokens": max_tokens,
                        "usage": {"include": True},  # OpenRouter devolve o custo em usage.cost
                        **({"tools": ferramentas, "tool_choice": tool_choice} if ferramentas else {}),
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
                    custo_usd=float(uso.get("cost") or 0),
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
