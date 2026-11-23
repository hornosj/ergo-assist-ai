import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, brl, cm, FAIXAS, rotulo, type Cadeira } from '../api'

const LINHAS: { rotulo: string; valor: (c: Cadeira) => string; campo?: string }[] = [
  { rotulo: 'Preço de referência', valor: (c) => (c.preco_referencia_brl ? brl(c.preco_referencia_brl) : 'sem preço BR'), campo: 'preco_referencia_brl' },
  { rotulo: 'Altura do assento', valor: (c) => `${cm(c.altura_assento_min_cm)} a ${cm(c.altura_assento_max_cm)}`, campo: 'altura_assento_min_cm' },
  {
    rotulo: 'Profundidade do assento',
    valor: (c) =>
      c.profundidade_assento_min_cm === c.profundidade_assento_max_cm
        ? cm(c.profundidade_assento_min_cm)
        : `${cm(c.profundidade_assento_min_cm)} a ${cm(c.profundidade_assento_max_cm)}`,
    campo: 'profundidade_assento_min_cm',
  },
  { rotulo: 'Regula profundidade', valor: (c) => (c.regula_profundidade_assento == null ? '—' : c.regula_profundidade_assento ? 'sim' : 'não'), campo: 'regula_profundidade_assento' },
  { rotulo: 'Largura do assento', valor: (c) => cm(c.largura_assento_cm), campo: 'largura_assento_cm' },
  { rotulo: 'Apoio lombar', valor: (c) => rotulo(c.apoio_lombar), campo: 'apoio_lombar' },
  { rotulo: 'Braços', valor: (c) => rotulo(c.bracos), campo: 'bracos' },
  { rotulo: 'Apoio de cabeça', valor: (c) => rotulo(c.apoio_cabeca), campo: 'apoio_cabeca' },
  { rotulo: 'Mecanismo', valor: (c) => rotulo(c.mecanismo), campo: 'mecanismo' },
  { rotulo: 'Material', valor: (c) => `${rotulo(c.material_assento)} / ${rotulo(c.material_encosto)}` },
  { rotulo: 'Carga máxima', valor: (c) => (c.carga_maxima_kg ? `${c.carga_maxima_kg} kg` : '—'), campo: 'carga_maxima_kg' },
  { rotulo: 'Garantia', valor: (c) => (c.garantia_anos ? `${c.garantia_anos} anos` : '—'), campo: 'garantia_anos' },
  { rotulo: 'NBR 13962 declarada', valor: (c) => (c.certificacao_nbr13962 ? 'sim' : 'não informado'), campo: 'certificacao_nbr13962' },
]

export default function Catalogo() {
  const [cadeiras, setCadeiras] = useState<Cadeira[]>([])
  const [busca, setBusca] = useState('')
  const [faixa, setFaixa] = useState('')
  const [categoria, setCategoria] = useState('')
  const [params, setParams] = useSearchParams()
  const selecionadas = (params.get('ver') ?? '').split(',').filter(Boolean)

  useEffect(() => {
    api<Cadeira[]>('cadeiras/').then(setCadeiras).catch(() => {})
  }, [])

  const filtradas = useMemo(() => {
    const t = busca.toLowerCase()
    return cadeiras.filter(
      (c) =>
        (!t || c.nome.toLowerCase().includes(t)) &&
        (!faixa || (faixa === 'sem' ? !c.faixa_preco : c.faixa_preco === faixa)) &&
        (!categoria || c.categoria === categoria),
    )
  }, [cadeiras, busca, faixa, categoria])

  function alternar(slug: string) {
    const novo = selecionadas.includes(slug)
      ? selecionadas.filter((s) => s !== slug)
      : [...selecionadas, slug].slice(-3)
    setParams(novo.length ? { ver: novo.join(',') } : {})
  }

  const comparadas = selecionadas.map((s) => cadeiras.find((c) => c.slug === s)).filter(Boolean) as Cadeira[]

  return (
    <div className="catalogo">
      <h1>Catálogo</h1>
      <p className="sutil">
        {cadeiras.length} cadeiras com medidas do fabricante (ou de varejista, quando o fabricante não publica),
        consultadas em 23/11/2026. Traço = dado não confirmado. Selecione até 3 para comparar.
      </p>

      <div className="filtros">
        <input placeholder="Buscar marca ou modelo" value={busca} onChange={(e) => setBusca(e.target.value)} />
        <select value={faixa} onChange={(e) => setFaixa(e.target.value)}>
          <option value="">Todas as faixas</option>
          {Object.entries(FAIXAS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          <option value="sem">Sem preço no Brasil</option>
        </select>
        <select value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          <option value="">Todas as categorias</option>
          <option value="escritorio">Escritório</option>
          <option value="gamer">Gamer</option>
        </select>
      </div>

      {comparadas.length > 0 && (
        <div className="cartao comparacao">
          <table>
            <thead>
              <tr>
                <th />
                {comparadas.map((c) => (
                  <th key={c.slug}>
                    {c.nome}
                    <button className="link pequeno" onClick={() => alternar(c.slug)}>remover</button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {LINHAS.map((l) => (
                <tr key={l.rotulo}>
                  <th>{l.rotulo}</th>
                  {comparadas.map((c) => (
                    <td key={c.slug} className={l.campo && c.campos_incertos.includes(l.campo) ? 'incerto' : ''}>
                      {l.valor(c)}
                    </td>
                  ))}
                </tr>
              ))}
              <tr>
                <th>Fontes</th>
                {comparadas.map((c) => (
                  <td key={c.slug}>
                    <div className="fontes-celula">
                      {c.fontes.map((f, i) => (
                        <a key={f} href={f} target="_blank" rel="noreferrer noopener">fonte {i + 1}</a>
                      ))}
                    </div>
                  </td>
                ))}
              </tr>
              <tr>
                <th>Observações</th>
                {comparadas.map((c) => <td key={c.slug} className="pequeno">{c.observacoes || '—'}</td>)}
              </tr>
            </tbody>
          </table>
          <p className="pequeno sutil">Células em itálico: dado que a fonte não confirma com clareza.</p>
        </div>
      )}

      <div className="grade">
        {filtradas.map((c) => (
          <button
            key={c.slug}
            className={`cartao item ${selecionadas.includes(c.slug) ? 'selecionada' : ''}`}
            onClick={() => alternar(c.slug)}
          >
            <span className="item-marca">{c.marca}</span>
            <strong>{c.modelo}</strong>
            <span className="item-preco">
              {c.preco_referencia_brl ? brl(c.preco_referencia_brl) : 'sem preço BR'}
              {c.faixa_preco && <span className={`faixa ${c.faixa_preco}`}>{FAIXAS[c.faixa_preco]}</span>}
              {c.categoria === 'gamer' && <span className="faixa gamer">Gamer</span>}
            </span>
            <span className="pequeno">
              Assento {cm(c.altura_assento_min_cm)}–{cm(c.altura_assento_max_cm)} · braços {rotulo(c.bracos)}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
