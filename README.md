# Ergo Assist AI

Assistente de IA que interpreta cadeiras ergonômicas, calcula as medidas ideais do posto de trabalho para o corpo de cada pessoa e indica qual cadeira comprar, a partir de um catálogo real com fontes e de uma base de ergonomia citada (NR-17, NBR 13962, OSHA, CCOHS, Cornell).

Projeto de estudo para praticar a stack de vagas de IA aplicada: **Django + DRF, React, PostgreSQL/pgvector, LLM com tool calling, RAG híbrido, avaliação (evals) e segurança**.

**No ar:** https://ergo-assist-ai.fly.dev. A calculadora e o catálogo são abertos; o assistente pede conta, e o cadastro exige código de convite.

## O que ele faz

- **Minhas medidas**: a partir da estatura (e, se quiser, de medidas tiradas com fita), calcula a altura ideal do assento, a profundidade máxima, a altura da mesa e do monitor e a do apoio para os pés. Mostra um diagrama em escala e as cadeiras que servem.
- **Catálogo**: 65 cadeiras reais com as medidas da fonte, o link e a data de consulta:
  - **high end:** Herman Miller (Aeron A/B/C, Embody, Mirra 2, Sayl, Cosm, Lino), Steelcase (Leap, Leap Plus, Gesture, Amia, Series 1/2, Karman), Haworth, Humanscale, Vitra, Okamura e Knoll;
  - **importadas:** ErgoHuman Ultra e Elite 2, Sihoo, Autonomous, Branch, Hbada, Secretlab e Razer;
  - **nacionais e varejo:** Flexform, Cavaletti, Plaxmetal, Marelli, DT3, Elements e ThunderX3.

  O preço é o praticado na data da consulta (Black Friday de 2026), com o preço "de" nas observações. A exceção é a Herman Miller, que tem preço cheio. Dado não confirmado fica vazio, nunca estimado. Dá para comparar até 3 lado a lado.
- **Assistente**: chat com um agente que chama ferramentas (calcular, recomendar, detalhar, buscar na base) e cita as fontes. Ele mostra cada passo que deu e avisa quando escreve um número que não veio das ferramentas.

## Requisito da vaga → onde está no código

| Requisito | Implementação |
|---|---|
| Assistentes de IA e agentes | `backend/assistente/agente.py`: laço ReAct com tool calling (até 6 passos) e modo sem IA quando o LLM cai |
| LLMs | `backend/assistente/llm.py`: OpenRouter com cadeia **DeepSeek V4.1 Flash → Claude Haiku 5.5 → modelos `:free`** (troca automática quando um falha); custo real de cada chamada (`usage.cost`) e tetos de gasto diário por usuário e global |
| RAG | `backend/conhecimento/`: documentos → trechos → full-text em português (`unaccent`) + embeddings locais (fastembed) no pgvector (HNSW), fundidos por RRF |
| Uso de ferramentas | `backend/assistente/ferramentas.py`: 6 ferramentas com JSON Schema, validação do payload do LLM e permissão conferida em cada chamada |
| Interpretar documentos | fichas técnicas e normas viram dados estruturados (`data/catalogo/*.json`) e trechos citáveis (`data/conhecimento/*.md`) |
| Python, Django, DRF | `backend/`: apps `catalogo`, `medidas`, `conhecimento` e `assistente`; autenticação por token; throttling por escopo |
| React | `frontend/`: Vite + TypeScript + React Router; telas de chat, medidas (com diagrama SVG) e catálogo |
| PostgreSQL + busca semântica | Docker `pgvector/pgvector:pg17`; extensões `vector`, `pg_trgm` e `unaccent` criadas por migration |
| Qualidade, fiabilidade, tempo e custo | `backend/evals/`: acerto@k e MRR por modo de busca, conjunto de perguntas às cegas, invariantes da recomendação, latência p50/p95, tokens e LLM-as-judge; `ChamadaLLM` registra modelo, tokens e latência de cada chamada |
| Segurança, permissões, isolamento, rastreabilidade | permissão `usar_assistente`; conversa e perfil filtrados pelo dono (o de outro usuário dá 404); o agente **não grava nada**, só propõe (`AcaoPendente`) e a pessoa confirma; `ChamadaFerramenta` audita cada ferramenta; trechos marcados como dados (defesa contra prompt injection); limite de perguntas por hora; cadastro com código de convite; chave do LLM só no servidor (ver [Deploy](#deploy-no-flyio)) |

## Como rodar

Pré-requisitos: Docker Desktop, Python 3.13 e Node 22 ou mais novo.

```bash
docker compose up -d                       # Postgres + pgvector na porta 5433

cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
cp .env.example .env                       # cole a OPENROUTER_APIKEY (opcional)
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py importar_catalogo
.venv/Scripts/python manage.py indexar_conhecimento   # 1ª vez baixa ~220 MB de modelo
.venv/Scripts/python manage.py runserver

cd ../frontend
npm install && npm run dev                 # http://localhost:5173
```

Sem `OPENROUTER_APIKEY`, o assistente responde no **modo sem IA**: monta a resposta com o recomendador e a busca determinísticos, sem inventar nada.

### Testes e avaliação

```bash
cd backend
.venv/Scripts/python -m pytest                        # 42 testes, sem rede
.venv/Scripts/python manage.py avaliar                # busca + recomendação
.venv/Scripts/python manage.py avaliar --agente --juiz   # + agente com LLM (precisa da chave)
```

O relatório sai em `backend/evals/RESULTADOS.md`.

## Arquitetura

```
React (Vite)  ──/api──▶  Django + DRF
                           ├─ medidas/       cálculo antropométrico + recomendador (determinístico)
                           ├─ catalogo/      cadeiras reais (JSON com fontes → Postgres)
                           ├─ conhecimento/  RAG: trechos + tsvector + pgvector (RRF)
                           └─ assistente/    agente ReAct ─▶ OpenRouter (tool calling)
                                               ├─ ferramentas (validação + permissão + auditoria)
                                               ├─ verificador de números sem lastro
                                               └─ ações pendentes (humano confirma)
```

**Princípio:** o LLM nunca é a fonte de um número. Medidas vêm do cálculo, especificações vêm do catálogo e regras vêm da base citada. O LLM escolhe as ferramentas e explica o resultado, e o verificador confere se cada número da resposta aparece nos dados.

## Resultados da avaliação (23/11/2026)

| Busca | acerto@1 | acerto@3 | MRR |
|---|---|---|---|
| dev (15 perguntas, escritas por quem fez o sistema) — híbrido | 87% | 100% | 0,93 |
| **às cegas (36 perguntas, escritas sem ver os textos) — texto** | 61% | 83% | 0,73 |
| **às cegas — vetor** | 67% | 83% | 0,76 |
| **às cegas — híbrido** | 67% | 92% | 0,79 |

- A busca híbrida supera texto e vetor sozinhos no top 3. A diferença entre o conjunto de desenvolvimento e o cego é o viés de quem escreve as próprias perguntas; a estimativa honesta é a das cegas.
- **Corte de escopo:** a distância vetorial de 0,6 recusa 3 das 4 perguntas cegas fora do escopo e perde 1 boa. O casamento textual não serve para isso, porque "dor nas costas" casa com tudo.
- **Recomendação:** 0 violações de invariantes em 7 perfis (de 1,50 m a 2,00 m). Na cobertura por estatura, das 65 cadeiras, só 7 alcançam a altura ideal de quem tem 1,50 m, contra 40 para 1,70 m e 62 para 1,90 m.

### Agente: comparação de modelos (13 casos, juiz fixo DeepSeek V4 Pro)

| Modelo | ferramenta certa | latência p50 / p95 | juiz: fundamentada | juiz: útil | custo (13 casos) |
|---|---|---|---|---|---|
| **DeepSeek V4.1 Flash** (principal) | 100% | 6,8 s / 11,0 s | 4,92 | 4,46 | US$ 0,012 |
| Claude Haiku 5.5 (reserva, rodada anterior) | 100% | 6,9 s / 10,2 s | 4,78 | 4,56 | US$ 0,015 |
| modelos `:free` (Nemotron etc.) | 100% | **30 s / 58 s** | 4,83* | 4,67* | 0 |

\* Na rodada dos grátis, o juiz era o próprio modelo avaliado.

**Uma pergunta custa cerca de US$ 0,001.** O que os evals revelaram e foi corrigido:
- o verificador de números acusava norma ("NBR 13962"), centavos ("1.887,90") e cm → m;
- a busca por texto proibido dava falso positivo quando o modelo citava a frase da injeção para recusá-la (virou critério julgado);
- o juiz lia só 9 mil caracteres dos resultados e acusava de "inventado" o que estava na parte cortada;
- a ficha não levava as observações, então o agente não sabia do pistão de 100 mm da ErgoHuman Ultra, que resolve o caso de 1,75 m;
- ao esgotar os passos ou receber uma resposta vazia, o agente desistia (agora fecha a resposta sem ferramentas ou pede de novo);
- a saída tinha limite de 1.200 tokens e cortava respostas com tabela.

As duas últimas correções entraram depois da última rodada medida.

## Limitações conhecidas

- Os coeficientes antropométricos são de militares dos EUA (ANSUR); não foi possível obter tabelas brasileiras (INT/IBGE). O acréscimo de 2,5 cm de calçado é uma hipótese do projeto.
- A NBR 13962 é paga: as faixas citadas vêm de fontes secundárias.
- Várias cadeiras premium e importadas não têm preço no Brasil (importação ou venda sob consulta) e saem da lista quando há orçamento.
- Os preços são de referência da data da consulta (Black Friday de 2026).

## Deploy no Fly.io

Dois apps na região `gru`:

| App | O que é | Exposição |
|---|---|---|
| `ergo-assist-ai` | imagem única (`Dockerfile`): build do React + Django/gunicorn, modelo de embeddings já dentro da imagem; escala a zero sem uso | público (HTTPS) |
| `ergo-assist-db` | `pgvector/pgvector:pg17` com volume de 1 GB (`db/fly.toml`) | **sem IP público**; só pela rede privada (`ergo-assist-db.internal`) |

No `release_command`, cada deploy roda `migrate`, `importar_catalogo` e `indexar_conhecimento`.

**Como a chave do LLM fica protegida:**
1. Ela nunca vai para o git nem para a imagem: `.env` e `.env.fly` estão no `.gitignore` e no `.dockerignore`.
2. Ela entra como `fly secrets`, que o Fly guarda criptografado e só injeta como variável de ambiente na máquina em execução. O `fly secrets list` mostra só o digest.
3. Os segredos são gerados por `scripts/gerar_segredos_fly.py` e vão para o `fly secrets import` por pipe, sem aparecer na tela nem no histórico.
4. A chave nunca chega ao navegador: toda chamada ao LLM sai do servidor.
5. Para ninguém gastar o saldo:
   - o cadastro exige código de convite (`CODIGO_CONVITE`, comparação em tempo constante);
   - há limite de perguntas por hora;
   - há teto diário de US$ 0,10 por usuário e de US$ 0,50 somando todos (acima disso, o assistente responde sem IA);
   - vale também pôr um limite de crédito na própria chave, no painel do OpenRouter.

```bash
fly apps create ergo-assist-db && fly volumes create ergo_pgdata -a ergo-assist-db -r gru -s 1
python scripts/gerar_segredos_fly.py db  | fly secrets import -a ergo-assist-db --stage
fly deploy -c db/fly.toml --ha=false
fly apps create ergo-assist-ai
python scripts/gerar_segredos_fly.py web | fly secrets import -a ergo-assist-ai --stage
fly deploy --remote-only --ha=false
```
- O documento "Como ler a ficha técnica" atrai perguntas de outros temas na busca (ver os erros em `evals/RESULTADOS.md`).

## Próximas fases (roteiro de estudo)

1. **Streaming** da resposta (SSE no Django, leitura incremental no React).
2. **Multiagente**: um agente revisor que confere a resposta contra os resultados das ferramentas antes de enviar, e um roteador que escolhe entre o especialista em ajuste e o em compra.
3. **Reranker** (cross-encoder) depois do RRF, medido no conjunto cego.
4. **Ingestão de PDF**: subir o manual de uma cadeira e extrair a ficha técnica com saída estruturada validada.
5. **Multi-tenant**: organizações (empresa → funcionários) com isolamento por organização e um painel de custo e latência.
6. **CI** rodando `pytest` e `avaliar`, falhando se o acerto@3 cego cair, com deploy automático no Fly.
7. **Backup do banco** (hoje é um volume único, sem réplica) ou migração para um Postgres gerenciado com pgvector.
