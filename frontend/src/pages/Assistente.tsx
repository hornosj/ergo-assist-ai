import { useEffect, useRef, useState, type FormEvent } from 'react'
import Markdown from 'react-markdown'
import { api, type Acao, type Mensagem } from '../api'

interface ConversaResumo {
  id: number
  titulo: string
}

const SUGESTOES = [
  'Tenho 1,68 m, 72 kg e trabalho 8 h por dia. Qual cadeira comprar até R$ 2.500?',
  'Como regular a altura do assento e dos braços?',
  'Compare a Aeron com a Steelcase Leap.',
  'O que a NR-17 exige de uma cadeira de escritório?',
  'Cadeira gamer é ergonômica?',
]

const NOMES_FERRAMENTA: Record<string, string> = {
  calcular_medidas: 'Calculou as medidas',
  recomendar_cadeiras: 'Buscou cadeiras que servem',
  buscar_cadeiras: 'Procurou no catálogo',
  detalhar_cadeiras: 'Abriu fichas técnicas',
  buscar_conhecimento: 'Consultou a base de ergonomia',
  propor_salvar_perfil: 'Propôs salvar o perfil',
}

export default function Assistente() {
  const [conversas, setConversas] = useState<ConversaResumo[]>([])
  const [atual, setAtual] = useState<number | null>(null)
  const [mensagens, setMensagens] = useState<Mensagem[]>([])
  const [acoes, setAcoes] = useState<Record<number, Acao>>({})
  const [texto, setTexto] = useState('')
  const [pensando, setPensando] = useState(false)
  const [erro, setErro] = useState('')
  const fim = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api<ConversaResumo[]>('conversas').then(setConversas).catch(() => {})
  }, [])

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [mensagens, pensando])

  async function abrir(id: number) {
    setErro('')
    const c = await api<{ mensagens: Mensagem[]; acoes: Acao[] }>(`conversas/${id}`)
    setAtual(id)
    setMensagens(c.mensagens)
    setAcoes(Object.fromEntries(c.acoes.map((a) => [a.id, a])))
  }

  function nova() {
    setAtual(null)
    setMensagens([])
    setAcoes({})
    setErro('')
  }

  async function perguntar(pergunta: string) {
    if (!pergunta.trim() || pensando) return
    setErro('')
    setPensando(true)
    setTexto('')
    const provisoria: Mensagem = {
      id: -Date.now(), papel: 'user', texto: pergunta, modo: '', modelo: '', fontes: [], alertas: [],
      latencia_ms: null, tokens_entrada: 0, tokens_saida: 0, passos: [],
    }
    setMensagens((m) => [...m, provisoria])
    try {
      let id = atual
      if (id == null) {
        const c = await api<ConversaResumo>('conversas', { metodo: 'POST' })
        id = c.id
        setAtual(id)
        setConversas((cs) => [{ id: c.id, titulo: pergunta.slice(0, 80) }, ...cs])
      }
      const resposta = await api<Mensagem>(`conversas/${id}/mensagens`, { corpo: { texto: pergunta } })
      setMensagens((m) => [...m, resposta])
      if (resposta.acoes?.length) {
        setAcoes((a) => ({ ...a, ...Object.fromEntries(resposta.acoes!.map((x) => [x.id, x])) }))
      }
    } catch (e) {
      setErro((e as Error).message)
      setMensagens((m) => m.filter((x) => x.id !== provisoria.id))
      setTexto(pergunta)
    } finally {
      setPensando(false)
    }
  }

  async function decidir(acao: Acao, decisao: 'confirmar' | 'recusar') {
    const r = await api<Acao>(`acoes/${acao.id}/${decisao}`, { metodo: 'POST' })
    setAcoes((a) => ({ ...a, [r.id]: r }))
  }

  function enviar(e: FormEvent) {
    e.preventDefault()
    perguntar(texto)
  }

  const pendentes = Object.values(acoes)

  return (
    <div className="assistente">
      <aside className="conversas">
        <button className="primario largo" onClick={nova}>Nova conversa</button>
        <ul>
          {conversas.map((c) => (
            <li key={c.id}>
              <button className={c.id === atual ? 'ativa' : ''} onClick={() => abrir(c.id)}>
                {c.titulo || 'Sem título'}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="chat">
        <div className="mensagens">
          {mensagens.length === 0 && (
            <div className="vazio">
              <h1>Qual cadeira serve para o seu corpo?</h1>
              <p className="sutil">
                Conte sua altura, peso, orçamento e quanto tempo passa sentado. As medidas saem de uma
                calculadora, as cadeiras de um catálogo com fonte e as regras de ergonomia de documentos citados.
              </p>
              <div className="sugestoes">
                {SUGESTOES.map((s) => (
                  <button key={s} onClick={() => perguntar(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {mensagens.map((m) => (
            <article key={m.id} className={`msg ${m.papel}`}>
              {m.papel === 'assistant' && m.passos.length > 0 && (
                <details className="passos">
                  <summary>
                    {m.passos.filter((p) => p.ferramenta).length} passo(s)
                    {m.modo === 'sem_ia' ? ' · modo sem IA' : m.modelo ? ` · ${m.modelo}` : ''}
                    {m.latencia_ms ? ` · ${(m.latencia_ms / 1000).toFixed(1)} s` : ''}
                  </summary>
                  <ol>
                    {m.passos.map((p, i) =>
                      p.ferramenta ? (
                        <li key={i} className={p.ok ? '' : 'falhou'}>
                          <strong>{NOMES_FERRAMENTA[p.ferramenta] ?? p.ferramenta}</strong>
                          <code>{JSON.stringify(p.argumentos)}</code>
                        </li>
                      ) : (
                        <li key={i} className="aviso-passo">{p.aviso}</li>
                      ),
                    )}
                  </ol>
                </details>
              )}
              <div className="balao">
                {m.papel === 'assistant' ? <Markdown>{m.texto}</Markdown> : <p>{m.texto}</p>}
              </div>
              {m.alertas.map((a) => (
                <p key={a} className="alerta">⚠ {a}</p>
              ))}
              {m.fontes.length > 0 && (
                <div className="fontes">
                  <span>Fontes:</span>
                  {m.fontes.map((f, i) => (
                    <a key={f.url} href={f.url} target="_blank" rel="noreferrer noopener">
                      {f.ref ? `[${f.ref}] ` : ''}{f.titulo || new URL(f.url).hostname}
                      {i < m.fontes.length - 1 ? '' : ''}
                    </a>
                  ))}
                </div>
              )}
            </article>
          ))}

          {pendentes.map((a) => (
            <div key={a.id} className={`acao ${a.estado}`}>
              <div>
                <strong>Salvar no seu perfil?</strong>
                <p>{a.resumo}</p>
              </div>
              {a.estado === 'pendente' ? (
                <div className="acao-botoes">
                  <button className="primario" onClick={() => decidir(a, 'confirmar')}>Confirmar</button>
                  <button onClick={() => decidir(a, 'recusar')}>Recusar</button>
                </div>
              ) : (
                <span className="selo">{a.estado}</span>
              )}
            </div>
          ))}

          {pensando && <div className="msg assistant"><div className="balao pensando">Consultando…</div></div>}
          <div ref={fim} />
        </div>

        {erro && <p className="erro">{erro}</p>}
        <form className="caixa" onSubmit={enviar}>
          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                perguntar(texto)
              }
            }}
            placeholder="Pergunte sobre cadeiras, medidas ou ajuste do posto…"
            rows={2}
            maxLength={2000}
          />
          <button className="primario" disabled={pensando || !texto.trim()}>Enviar</button>
        </form>
      </section>
    </div>
  )
}
