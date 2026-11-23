"""Cálculo determinístico das medidas ideais do posto sentado.

Nada aqui usa LLM: os números saem de proporções antropométricas publicadas
(ver `COEFICIENTES` e `docs/medidas.md`). Medida informada pelo usuário
sempre vence a estimativa. O LLM só explica o resultado.
"""

from dataclasses import asdict, dataclass, field

# Fração da estatura (pessoa descalça). Fontes em data/conhecimento/antropometria.md:
# Fromuth & Parkinson 2008 (ANSUR, P50 média dos sexos) e ANSUR II (NC State).
COEFICIENTES = {
    "altura_poplitea": 0.243,  # chão até a dobra do joelho, sentado (Fromuth P50)
    "nadega_poplitea": 0.290,  # fundo do glúteo até a dobra do joelho (Fromuth P50)
    "cotovelo_sentado": 0.14,  # assento até o cotovelo (ANSUR II, razão calculada)
    "olhos_sentado": 0.452,  # assento até os olhos (Fromuth P50)
    "quadril_sentado": 0.21,  # largura do quadril (ANSUR II: 0,196 H / 0,217 M)
}
# HIPÓTESE DO PROJETO (sem fonte verificada): calçado comum soma ~2,5 cm.
COMPENSACAO_CALCADO_CM = 2.5
# Folga entre a borda do assento e a dobra do joelho: 2–4 dedos (≈ 3–6 cm),
# síntese de CCOHS (punho ≈ 5 cm), NHS (1–2") e Southern Health (2–4 dedos).
FOLGA_JOELHO_CM = (3.0, 6.0)
FOLGA_LARGURA_CM = 2.0  # sobra mínima no assento além da largura do quadril

LIMITES = {
    "estatura_cm": (120, 230),
    "peso_kg": (30, 250),
    "altura_poplitea_cm": (30, 65),
    "comprimento_nadega_poplitea_cm": (35, 65),
    "largura_quadril_cm": (25, 70),
    "altura_mesa_cm": (55, 100),
}


class MedidaInvalida(ValueError):
    pass


def _validar(nome: str, valor: float | None) -> float | None:
    if valor is None:
        return None
    try:
        valor = float(valor)
    except (TypeError, ValueError) as exc:
        raise MedidaInvalida(f"{nome} precisa ser um número") from exc
    lo, hi = LIMITES[nome]
    if not lo <= valor <= hi:
        raise MedidaInvalida(f"{nome}={valor:g} fora da faixa plausível ({lo}–{hi})")
    return valor


@dataclass
class Medidas:
    estatura_cm: float
    peso_kg: float | None
    altura_poplitea_cm: float
    comprimento_nadega_poplitea_cm: float
    largura_quadril_cm: float
    cotovelo_sentado_cm: float
    olhos_sentado_cm: float
    estimadas: list[str] = field(default_factory=list)

    # --- resultados ---------------------------------------------------------
    altura_assento_ideal_cm: float = 0.0
    altura_assento_faixa_cm: tuple[float, float] = (0.0, 0.0)
    profundidade_assento_max_cm: float = 0.0
    profundidade_assento_ideal_cm: tuple[float, float] = (0.0, 0.0)
    largura_assento_min_cm: float = 0.0
    altura_mesa_ideal_cm: float = 0.0
    altura_topo_monitor_cm: float = 0.0
    mesa_informada_cm: float | None = None
    altura_assento_para_mesa_cm: float | None = None
    apoio_pes_cm: float | None = None
    avisos: list[str] = field(default_factory=list)

    def como_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, float):
                d[k] = round(v, 1)
            elif isinstance(v, tuple):
                d[k] = [round(x, 1) for x in v]
        return d


def calcular(
    estatura_cm: float,
    peso_kg: float | None = None,
    altura_poplitea_cm: float | None = None,
    comprimento_nadega_poplitea_cm: float | None = None,
    largura_quadril_cm: float | None = None,
    altura_mesa_cm: float | None = None,
) -> Medidas:
    estatura = _validar("estatura_cm", estatura_cm)
    if estatura is None:
        raise MedidaInvalida("estatura_cm é obrigatória")
    peso = _validar("peso_kg", peso_kg)
    pop = _validar("altura_poplitea_cm", altura_poplitea_cm)
    nad = _validar("comprimento_nadega_poplitea_cm", comprimento_nadega_poplitea_cm)
    quad = _validar("largura_quadril_cm", largura_quadril_cm)
    mesa = _validar("altura_mesa_cm", altura_mesa_cm)

    estimadas = []
    if pop is None:
        pop = estatura * COEFICIENTES["altura_poplitea"]
        estimadas.append("altura_poplitea_cm")
    if nad is None:
        nad = estatura * COEFICIENTES["nadega_poplitea"]
        estimadas.append("comprimento_nadega_poplitea_cm")
    if quad is None:
        quad = estatura * COEFICIENTES["quadril_sentado"]
        estimadas.append("largura_quadril_cm")

    m = Medidas(
        estatura_cm=estatura,
        peso_kg=peso,
        altura_poplitea_cm=pop,
        comprimento_nadega_poplitea_cm=nad,
        largura_quadril_cm=quad,
        cotovelo_sentado_cm=estatura * COEFICIENTES["cotovelo_sentado"],
        olhos_sentado_cm=estatura * COEFICIENTES["olhos_sentado"],
        estimadas=estimadas,
        mesa_informada_cm=mesa,
    )

    # Assento: pés apoiados e coxas ~horizontais => altura poplítea + calçado.
    # Um pouco mais baixo é tolerável (pés seguem apoiados); mais alto pressiona
    # a parte de trás da coxa.
    ideal = pop + COMPENSACAO_CALCADO_CM
    m.altura_assento_ideal_cm = ideal
    m.altura_assento_faixa_cm = (ideal - 3.0, ideal + 1.0)

    # Profundidade: a borda não pode encostar na dobra do joelho.
    m.profundidade_assento_max_cm = nad - FOLGA_JOELHO_CM[0]
    m.profundidade_assento_ideal_cm = (nad - FOLGA_JOELHO_CM[1], nad - FOLGA_JOELHO_CM[0])
    m.largura_assento_min_cm = quad + FOLGA_LARGURA_CM

    # Mesa na altura do cotovelo (antebraço ~horizontal).
    m.altura_mesa_ideal_cm = ideal + m.cotovelo_sentado_cm
    # Topo da tela na altura dos olhos ou um pouco abaixo.
    m.altura_topo_monitor_cm = ideal + m.olhos_sentado_cm

    if mesa is not None:
        # Mesa fixa: sobe o assento até o cotovelo alcançar a mesa e compensa
        # os pés com um apoio.
        assento_mesa = mesa - m.cotovelo_sentado_cm
        m.altura_assento_para_mesa_cm = assento_mesa
        if assento_mesa > ideal + 1.0:
            m.apoio_pes_cm = assento_mesa - ideal
            m.avisos.append(
                f"A mesa ({mesa:g} cm) é alta para você: suba o assento para "
                f"~{assento_mesa:.0f} cm e use apoio para os pés de ~{m.apoio_pes_cm:.0f} cm."
            )
        elif assento_mesa < ideal - 3.0:
            m.avisos.append(
                f"A mesa ({mesa:g} cm) é baixa para você: o ideal seria ~{m.altura_mesa_ideal_cm:.0f} cm "
                "(mesa regulável, calços ou teclado em suporte)."
            )

    if estimadas:
        m.avisos.append(
            "Medidas estimadas pela estatura (média populacional). Para precisão, meça "
            "a altura poplítea sentado, descalço, do chão à dobra do joelho."
        )
    return m
