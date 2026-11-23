import { useEffect, useState, type FormEvent } from 'react'
import { api, cm, type Medidas, type Recomendacao } from '../api'
import { useSessao } from '../App'
import DiagramaPosto from '../components/DiagramaPosto'
import RecomendacaoCard from '../components/RecomendacaoCard'

type Campos = Record<string, string>

const NUMERICOS = [
  'estatura_cm', 'peso_kg', 'altura_poplitea_cm', 'comprimento_nadega_poplitea_cm',
  'largura_quadril_cm', 'altura_mesa_cm', 'orcamento_brl', 'horas_por_dia',
]

function paraCorpo(c: Campos, extras: Record<string, unknown>) {
  const corpo: Record<string, unknown> = { ...extras }
  for (const k of NUMERICOS) {
    if (c[k]?.trim()) corpo[k] = Number(c[k].replace(',', '.'))
  }
  if (c.material_preferido) corpo.material_preferido = c.material_preferido
  return corpo
}

export default function MedidasPagina() {
  const { username } = useSessao()
  const [c, setC] = useState<Campos>({ estatura_cm: '', peso_kg: '', horas_por_dia: '8' })
  const [gamer, setGamer] = useState(false)
  const [cabeca, setCabeca] = useState(false)
  const [res, setRes] = useState<{ medidas: Medidas; recomendacoes: Recomendacao[] } | null>(null)
  const [erro, setErro] = useState('')
  const [salvo, setSalvo] = useState('')

  useEffect(() => {
    if (!username) return
    api<Record<string, number | string | null> | undefined>('perfil').then((p) => {
      if (!p) return
      const campos: Campos = {}
      for (const [k, v] of Object.entries(p)) if (v != null && k !== 'atualizado_em') campos[k] = String(v)
      setC((atual) => ({ ...atual, ...campos }))
    }).catch(() => {})
  }, [username])

  const set = (k: string) => (e: { target: { value: string } }) => setC({ ...c, [k]: e.target.value })

  async function calcular(e: FormEvent) {
    e.preventDefault()
    setErro('')
    setSalvo('')
    try {
      setRes(await api('medidas/calcular', {
        corpo: paraCorpo(c, { incluir_gamer: gamer, quer_apoio_cabeca: cabeca, limite: 6 }),
      }))
    } catch (err) {
      setErro((err as Error).message)
    }
  }

  async function salvar() {
    try {
      await api('perfil', { metodo: 'PUT', corpo: paraCorpo(c, {}) })
      setSalvo('Perfil salvo. O assistente vai usar essas medidas.')
    } catch (err) {
      setErro((err as Error).message)
    }
  }

  const m = res?.medidas
  return (
    <div className="medidas">
      <section>
        <h1>Minhas medidas</h1>
        <p className="sutil">
          Só a estatura é obrigatória. Medidas tiradas com fita métrica deixam o cálculo mais preciso que a
          estimativa pela altura.
        </p>
        <form className="cartao form" onSubmit={calcular}>
          <div className="linha">
            <label>Estatura (cm)<input inputMode="decimal" value={c.estatura_cm ?? ''} onChange={set('estatura_cm')} required placeholder="175" /></label>
            <label>Peso (kg)<input inputMode="decimal" value={c.peso_kg ?? ''} onChange={set('peso_kg')} placeholder="80" /></label>
          </div>
          <div className="linha">
            <label>Orçamento (R$)<input inputMode="decimal" value={c.orcamento_brl ?? ''} onChange={set('orcamento_brl')} placeholder="sem limite" /></label>
            <label>Horas sentado/dia<input inputMode="decimal" value={c.horas_por_dia ?? ''} onChange={set('horas_por_dia')} /></label>
          </div>
          <label>
            Material preferido
            <select value={c.material_preferido ?? ''} onChange={set('material_preferido')}>
              <option value="">tanto faz</option>
              <option value="tela">tela (ventila mais)</option>
              <option value="espuma">espuma</option>
            </select>
          </label>
          <details>
            <summary>Medidas com fita (opcional)</summary>
            <div className="linha">
              <label>Altura poplítea (cm)<input inputMode="decimal" value={c.altura_poplitea_cm ?? ''} onChange={set('altura_poplitea_cm')} title="Sentado e descalço, do chão até a dobra de trás do joelho" /></label>
              <label>Nádega–joelho (cm)<input inputMode="decimal" value={c.comprimento_nadega_poplitea_cm ?? ''} onChange={set('comprimento_nadega_poplitea_cm')} title="Sentado, do fundo do glúteo até a dobra de trás do joelho" /></label>
            </div>
            <div className="linha">
              <label>Largura do quadril (cm)<input inputMode="decimal" value={c.largura_quadril_cm ?? ''} onChange={set('largura_quadril_cm')} /></label>
              <label>Altura da sua mesa (cm)<input inputMode="decimal" value={c.altura_mesa_cm ?? ''} onChange={set('altura_mesa_cm')} placeholder="se for fixa" /></label>
            </div>
          </details>
          <label className="check"><input type="checkbox" checked={cabeca} onChange={(e) => setCabeca(e.target.checked)} /> Quero apoio de cabeça</label>
          <label className="check"><input type="checkbox" checked={gamer} onChange={(e) => setGamer(e.target.checked)} /> Incluir cadeiras gamer</label>
          {erro && <p className="erro">{erro}</p>}
          <div className="acao-botoes">
            <button className="primario">Calcular</button>
            {username && <button type="button" onClick={salvar}>Salvar no perfil</button>}
          </div>
          {salvo && <p className="ok">{salvo}</p>}
        </form>
      </section>

      {m && res && (
        <section className="resultado">
          <div className="cartao">
            <DiagramaPosto m={m} />
            <dl className="numeros">
              <div><dt>Altura do assento</dt><dd>{cm(m.altura_assento_ideal_cm)}</dd><small>aceitável {cm(m.altura_assento_faixa_cm[0])}–{cm(m.altura_assento_faixa_cm[1])}</small></div>
              <div><dt>Profundidade do assento</dt><dd>até {cm(m.profundidade_assento_max_cm)}</dd><small>ideal {cm(m.profundidade_assento_ideal_cm[0])}–{cm(m.profundidade_assento_ideal_cm[1])}</small></div>
              <div><dt>Largura mínima</dt><dd>{cm(m.largura_assento_min_cm)}</dd></div>
              <div><dt>Mesa (altura do cotovelo)</dt><dd>{cm(m.altura_mesa_ideal_cm)}</dd></div>
              <div><dt>Topo da tela</dt><dd>{cm(m.altura_topo_monitor_cm)}</dd><small>do chão; na altura dos olhos ou um pouco abaixo</small></div>
              {m.apoio_pes_cm != null && <div><dt>Apoio para os pés</dt><dd>{cm(m.apoio_pes_cm)}</dd></div>}
            </dl>
            {m.avisos.map((a) => <p key={a} className="alerta">{a}</p>)}
          </div>

          <h2>Cadeiras que servem para você</h2>
          {res.recomendacoes.length === 0 ? (
            <p className="sutil">Nenhuma cadeira do catálogo atende a esses critérios. Tente aumentar o orçamento.</p>
          ) : (
            <div className="recs">
              {res.recomendacoes.map((r, i) => <RecomendacaoCard key={r.slug} r={r} posicao={i + 1} />)}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
