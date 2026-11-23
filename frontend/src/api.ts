// Cliente da API Django/DRF. O token fica no localStorage (projeto de estudo;
// em produção, prefira cookie httpOnly).

const CHAVE_TOKEN = 'ergo.token'

export function lerToken(): string | null {
  try {
    return localStorage.getItem(CHAVE_TOKEN)
  } catch {
    return null
  }
}

export function gravarToken(token: string | null) {
  try {
    if (token) localStorage.setItem(CHAVE_TOKEN, token)
    else localStorage.removeItem(CHAVE_TOKEN)
  } catch {
    /* navegação privada: segue sem persistir */
  }
}

export class ErroApi extends Error {
  status: number
  constructor(status: number, mensagem: string) {
    super(mensagem)
    this.status = status
  }
}

function mensagemDeErro(corpo: unknown): string {
  if (!corpo || typeof corpo !== 'object') return 'Erro inesperado'
  const c = corpo as Record<string, unknown>
  if (typeof c.erro === 'string') return c.erro
  if (typeof c.detail === 'string') return c.detail
  return Object.entries(c)
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : String(v)}`)
    .join('; ')
}

export async function api<T>(caminho: string, opcoes: { metodo?: string; corpo?: unknown } = {}): Promise<T> {
  const cabecalhos: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = lerToken()
  if (token) cabecalhos.Authorization = `Token ${token}`
  const r = await fetch(`/api/${caminho}`, {
    method: opcoes.metodo ?? (opcoes.corpo ? 'POST' : 'GET'),
    headers: cabecalhos,
    body: opcoes.corpo ? JSON.stringify(opcoes.corpo) : undefined,
  })
  if (r.status === 204) return undefined as T
  const corpo = await r.json().catch(() => null)
  if (!r.ok) throw new ErroApi(r.status, mensagemDeErro(corpo))
  return corpo as T
}

// --- tipos ---------------------------------------------------------------

export interface Cadeira {
  slug: string
  nome: string
  marca: string
  modelo: string
  variante: string
  categoria: string
  faixa_preco: string
  preco_referencia_brl: string | null
  preco_fonte: string
  altura_assento_min_cm: number | null
  altura_assento_max_cm: number | null
  profundidade_assento_min_cm: number | null
  profundidade_assento_max_cm: number | null
  regula_profundidade_assento: boolean | null
  largura_assento_cm: number | null
  altura_encosto_cm: number | null
  apoio_lombar: string
  bracos: string
  apoio_cabeca: string
  mecanismo: string
  material_assento: string
  material_encosto: string
  carga_maxima_kg: number | null
  garantia_anos: number | null
  certificacao_nbr13962: boolean | null
  fontes: string[]
  consultado_em: string | null
  campos_incertos: string[]
  observacoes: string
}

export interface Medidas {
  estatura_cm: number
  peso_kg: number | null
  altura_poplitea_cm: number
  comprimento_nadega_poplitea_cm: number
  largura_quadril_cm: number
  cotovelo_sentado_cm: number
  olhos_sentado_cm: number
  estimadas: string[]
  altura_assento_ideal_cm: number
  altura_assento_faixa_cm: [number, number]
  profundidade_assento_max_cm: number
  profundidade_assento_ideal_cm: [number, number]
  largura_assento_min_cm: number
  altura_mesa_ideal_cm: number
  altura_topo_monitor_cm: number
  mesa_informada_cm: number | null
  altura_assento_para_mesa_cm: number | null
  apoio_pes_cm: number | null
  avisos: string[]
}

export interface Recomendacao {
  slug: string
  nome: string
  variante: string
  preco_referencia_brl: number | null
  faixa_preco: string
  altura_assento_cm: [number | null, number | null]
  pontos: number
  motivos: string[]
  alertas: string[]
  fontes: string[]
}

export interface Passo {
  ferramenta?: string
  argumentos?: Record<string, unknown>
  ok?: boolean
  duracao_ms?: number
  aviso?: string
}

export interface Acao {
  id: number
  tipo: string
  resumo: string
  estado: 'pendente' | 'confirmada' | 'recusada'
}

export interface Mensagem {
  id: number
  papel: 'user' | 'assistant'
  texto: string
  modo: string
  modelo: string
  fontes: { ref?: number; titulo: string; url: string }[]
  alertas: string[]
  latencia_ms: number | null
  tokens_entrada: number
  tokens_saida: number
  custo_usd?: string | number
  passos: Passo[]
  acoes?: Acao[]
}

export const brl = (v: number | string | null) =>
  v == null ? '—' : Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })

export const cm = (v: number | null | undefined) => (v == null ? '—' : `${Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} cm`)

export const FAIXAS: Record<string, string> = {
  economica: 'Econômica',
  intermediaria: 'Intermediária',
  alta: 'Alta',
  premium: 'Premium',
}

export const ROTULOS: Record<string, string> = {
  adaptativo: 'adaptativo',
  regulavel_altura_profundidade: 'regula altura e profundidade',
  regulavel_altura: 'regula altura',
  fixo: 'fixo',
  nenhum: 'não tem',
  opcional: 'opcional',
  regulavel: 'regulável',
  syncro: 'syncro',
  autoajustavel: 'autoajustável',
  back_system: 'back system',
  relax: 'relax',
  outro: 'outro',
  tela: 'tela',
  espuma: 'espuma',
  espuma_injetada: 'espuma injetada',
  couro: 'couro',
  couro_sintetico: 'couro sintético',
}
export const rotulo = (v: string | null | undefined) => (v ? (ROTULOS[v] ?? v) : '—')
