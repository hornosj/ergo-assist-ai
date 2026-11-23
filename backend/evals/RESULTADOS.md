# Resultados da avaliação — 2026-11-23 14:35

## Busca — dev (15 perguntas no escopo, 2 fora)

| modo | acerto@1 | acerto@3 | MRR | ms (mediana) |
|---|---|---|---|---|
| texto | 73% | 73% | 0.78 | 2.4 |
| vetor | 80% | 100% | 0.89 | 52.0 |
| hibrido | 87% | 100% | 0.93 | 52.2 |

Corte de escopo por distância (fora recusadas / boas perdidas): 0.45: 2/1, 0.5: 2/1, 0.55: 2/0, 0.6: 2/0, 0.65: 2/0, 0.7: 1/0

Erros do híbrido (o esperado não veio em 1º):
- "como regular a altura da cadeira" → esperado ['ajuste-altura-do-assento'], veio ['como-ler-a-ficha-tecnica', 'ajuste-altura-do-assento', 'nbr13962-cadeiras-de-escritorio']
- "o que a NR-17 exige da cadeira" → esperado ['nr17-mobiliario-e-assentos'], veio ['como-ler-a-ficha-tecnica', 'nr17-mobiliario-e-assentos', 'nr17-mobiliario-e-assentos']

## Busca — cegas (36 perguntas no escopo, 4 fora)

| modo | acerto@1 | acerto@3 | MRR | ms (mediana) |
|---|---|---|---|---|
| texto | 61% | 83% | 0.73 | 2.8 |
| vetor | 67% | 83% | 0.76 | 52.1 |
| hibrido | 67% | 92% | 0.79 | 56.0 |

Corte de escopo por distância (fora recusadas / boas perdidas): 0.45: 4/10, 0.5: 4/6, 0.55: 4/3, 0.6: 3/1, 0.65: 1/1, 0.7: 1/1

Erros do híbrido (o esperado não veio em 1º):
- "altura do banco cadeira" → esperado ['ajuste-altura-do-assento'], veio ['como-ler-a-ficha-tecnica', 'ajuste-altura-do-assento', 'nbr13962-cadeiras-de-escritorio']
- "a mesa do escritorio é muito alta e se eu subo a cadeira meus pes ficam balançando, faço oq" → esperado ['ajuste-altura-do-assento', 'nr17-mobiliario-e-assentos'], veio ['monitor-mesa-e-pausas', 'ajuste-altura-do-assento', 'monitor-mesa-e-pausas']
- "Estou comparando três modelos num site e cada um mostra as dimensões de um jeito diferente, alguns nem informam tudo. Quais números da descrição eu deveria olhar primeiro antes de fechar a compra?" → esperado ['como-ler-a-ficha-tecnica'], veio ['capacidade-de-peso', 'como-ler-a-ficha-tecnica', 'nbr13962-cadeiras-de-escritorio']
- "fica um vão entre minhas costas e o encosto bem na altura da cintura" → esperado ['encosto-lombar-e-reclinacao'], veio ['ajuste-altura-do-assento', 'encosto-lombar-e-reclinacao', 'sinais-e-mitos']
- "qtos graus eu deveria deixar o encosto inclinado pra trabalhar" → esperado ['encosto-lombar-e-reclinacao'], veio ['nr17-mobiliario-e-assentos', 'nr17-mobiliario-e-assentos', 'nr17-mobiliario-e-assentos']
- "cadeira sem selo da ABNT é proibida de vender?" → esperado ['nbr13962-cadeiras-de-escritorio'], veio ['sinais-e-mitos', 'sinais-e-mitos', 'nbr13962-cadeiras-de-escritorio']
- "Essa norma técnica de cadeira de escritório serve pra quem é muito alto ou muito baixo, ou ela foi pensada só para uma pessoa de tamanho médio? Tenho quase 2 metros e nada parece servir." → esperado ['nbr13962-cadeiras-de-escritorio'], veio ['ajuste-altura-do-assento', 'antropometria-e-calculo', 'nbr13962-cadeiras-de-escritorio']
- "qual a diferença entre o que a NR-17 exige e o que a norma da ABNT pede pra cadeira?" → esperado ['nbr13962-cadeiras-de-escritorio', 'nr17-mobiliario-e-assentos'], veio ['como-ler-a-ficha-tecnica', 'nr17-mobiliario-e-assentos', 'nr17-mobiliario-e-assentos']
- "a empresa é obrigada por lei a me dar uma cadeira que regula a altura?" → esperado ['nr17-mobiliario-e-assentos'], veio ['como-ler-a-ficha-tecnica', 'ajuste-altura-do-assento', 'nbr13962-cadeiras-de-escritorio']
- "pausa obrigatoria telemarketing" → esperado ['nr17-mobiliario-e-assentos'], veio ['monitor-mesa-e-pausas', 'nr17-mobiliario-e-assentos', 'nr17-mobiliario-e-assentos']
- "a beirada do assento aperta atrás do joelho" → esperado ['profundidade-e-largura-do-assento'], veio ['ajuste-altura-do-assento', 'profundidade-e-largura-do-assento', 'sinais-e-mitos']
- "Sou baixinha e nas cadeiras do escritório eu não consigo encostar as costas sem que o assento empurre minhas pernas pra frente. É a cadeira que é funda demais pra mim ou estou sentando errado?" → esperado ['profundidade-e-largura-do-assento'], veio ['ajuste-altura-do-assento', 'sinais-e-mitos', 'sinais-e-mitos']

## Recomendação

Violações de invariantes: **0**

| perfil | assento ideal | top 3 |
|---|---|---|
| {'estatura_cm': 150, 'peso_kg': 50} | 38.9 cm | steelcase-leap-v2, herman-miller-mirra-2 |
| {'estatura_cm': 158, 'peso_kg': 62, 'orcamento_brl': 1500} | 40.9 cm | plaxmetal-brizza-presidente |
| {'estatura_cm': 168, 'peso_kg': 72, 'orcamento_brl': 2500, 'horas_por_dia': 8} | 43.3 cm | plaxmetal-brizza-presidente, elements-rasala, elements-astra-pro |
| {'estatura_cm': 175, 'peso_kg': 80} | 45.0 cm | haworth-zody, plaxmetal-brizza-presidente, steelcase-series-1 |
| {'estatura_cm': 183, 'peso_kg': 95, 'horas_por_dia': 10} | 47.0 cm | haworth-zody, steelcase-series-1, plaxmetal-brizza-presidente |
| {'estatura_cm': 192, 'peso_kg': 115} | 49.2 cm | haworth-zody, plaxmetal-brizza-presidente, steelcase-series-1 |
| {'estatura_cm': 200, 'peso_kg': 130} | 51.1 cm | haworth-zody, plaxmetal-brizza-presidente, steelcase-series-1 |

Cobertura (cadeiras de 33 que alcançam a altura ideal, por estatura): 145 cm: 1, 150 cm: 2, 155 cm: 9, 160 cm: 14, 165 cm: 18, 170 cm: 23, 175 cm: 28, 180 cm: 30, 185 cm: 32, 190 cm: 32, 195 cm: 33, 200 cm: 33, 205 cm: 33

