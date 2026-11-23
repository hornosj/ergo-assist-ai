import { Link } from 'react-router-dom'
import { brl, cm, FAIXAS, type Recomendacao } from '../api'

export default function RecomendacaoCard({ r, posicao }: { r: Recomendacao; posicao: number }) {
  const [min, max] = r.altura_assento_cm
  return (
    <article className="cartao rec">
      <header>
        <span className="posicao">{posicao}</span>
        <div>
          <h3>{r.nome}</h3>
          {r.variante && <p className="sutil pequeno">{r.variante}</p>}
        </div>
        <div className="preco">
          <strong>{r.preco_referencia_brl ? brl(r.preco_referencia_brl) : 'sem preço BR'}</strong>
          {r.faixa_preco && <span className={`faixa ${r.faixa_preco}`}>{FAIXAS[r.faixa_preco]}</span>}
        </div>
      </header>
      <p className="pequeno">Assento: {cm(min)} a {cm(max)}</p>
      {r.motivos.length > 0 && (
        <ul className="motivos">
          {r.motivos.map((m) => <li key={m}>{m}</li>)}
        </ul>
      )}
      {r.alertas.length > 0 && (
        <ul className="alertas">
          {r.alertas.map((a) => <li key={a}>{a}</li>)}
        </ul>
      )}
      <footer>
        <Link to={`/catalogo?ver=${r.slug}`}>Ficha técnica</Link>
        {r.fontes[0] && <a href={r.fontes[0]} target="_blank" rel="noreferrer noopener">Fonte</a>}
      </footer>
    </article>
  )
}
