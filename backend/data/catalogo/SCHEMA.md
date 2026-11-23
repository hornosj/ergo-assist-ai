# Esquema do catálogo de cadeiras

Cada arquivo `cadeiras_<lote>.json` é uma lista JSON de objetos neste formato.
Regra de ouro: **nunca chutar**. Campo não encontrado em fonte confiável = `null`
e o nome do campo vai para `campos_incertos`. Medidas em centímetros, peso em kg.

```json
{
  "id": "herman-miller-aeron",            // slug único: marca-modelo[-variante]
  "marca": "Herman Miller",
  "modelo": "Aeron",
  "variante": "Tamanho B, braços ajustáveis, PostureFit SL",  // config. que as medidas descrevem
  "categoria": "escritorio",              // escritorio | gamer | executiva | operacional
  "faixa_preco": "premium",               // economica (<1000) | intermediaria (1000-2500) | alta (2500-6000) | premium (>6000)
  "preco_referencia_brl": 12990,          // número ou null
  "preco_fonte": "https://...",
  "altura_assento_min_cm": 41.0,          // do chão ao topo do assento, posição mais baixa
  "altura_assento_max_cm": 52.0,
  "profundidade_assento_min_cm": 43.0,    // se não regula, min = max
  "profundidade_assento_max_cm": 43.0,
  "regula_profundidade_assento": false,
  "largura_assento_cm": 48.0,
  "altura_encosto_cm": 60.0,              // altura do encosto (sem apoio de cabeça)
  "regula_altura_encosto": false,
  "apoio_lombar": "regulavel_altura",     // nenhum | fixo | regulavel_altura | regulavel_altura_profundidade | adaptativo
  "bracos": "4D",                         // nenhum | fixo | 1D | 2D | 3D | 4D | opcional
  "apoio_cabeca": "nenhum",               // nenhum | fixo | regulavel | opcional
  "mecanismo": "syncro",                  // relax | syncro | back_system | autoajustavel | outro | null
  "regula_tensao_reclinacao": true,
  "travas_reclinacao": 3,                 // número de posições de trava, null se desconhecido
  "material_assento": "tela",             // tela | espuma | espuma_injetada | couro | couro_sintetico | outro
  "material_encosto": "tela",
  "carga_maxima_kg": 159,
  "garantia_anos": 12,
  "certificacao_nbr13962": null,          // true só se o fabricante declarar; null se não achar
  "altura_usuario_indicada_cm": [157, 196],  // só se o fabricante indicar; senão null
  "fontes": ["https://...ficha tecnica...", "https://...loja..."],
  "consultado_em": "2026-11-23",
  "campos_incertos": ["largura_assento_cm"],
  "observacoes": "Medidas da ficha técnica Herman Miller BR; tamanho C muda as medidas."
}
```

Preferência de fonte: ficha técnica / manual do fabricante > página do produto do
fabricante > grande varejista (Kabum, Amazon BR, Magalu, Leroy, Dell) > review técnico.
Converta polegadas/mm para cm. Se houver tamanhos (A/B/C), use o tamanho médio e diga
qual em `variante`.
