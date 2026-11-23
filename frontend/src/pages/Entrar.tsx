import { useState, type FormEvent } from 'react'
import { api } from '../api'
import { useSessao } from '../App'

export default function Entrar() {
  const { entrar } = useSessao()
  const [modo, setModo] = useState<'entrar' | 'cadastro'>('entrar')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setErro('')
    setEnviando(true)
    try {
      const r = await api<{ token: string }>(modo === 'entrar' ? 'auth/token' : 'auth/cadastro', {
        corpo: { username, password },
      })
      entrar(r.token, username)
    } catch (err) {
      setErro(modo === 'entrar' ? 'Usuário ou senha incorretos.' : (err as Error).message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="entrar">
      <h1>{modo === 'entrar' ? 'Entrar' : 'Criar conta'}</h1>
      <p className="sutil">
        O assistente guarda as suas conversas e o seu perfil de medidas. A calculadora e o catálogo
        funcionam sem conta.
      </p>
      <form onSubmit={enviar} className="cartao form">
        <label>
          Usuário
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </label>
        <label>
          Senha
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={modo === 'entrar' ? 'current-password' : 'new-password'}
            required
          />
        </label>
        {erro && <p className="erro">{erro}</p>}
        <button className="primario" disabled={enviando}>
          {enviando ? 'Aguarde…' : modo === 'entrar' ? 'Entrar' : 'Criar conta'}
        </button>
        <button type="button" className="link" onClick={() => setModo(modo === 'entrar' ? 'cadastro' : 'entrar')}>
          {modo === 'entrar' ? 'Não tem conta? Criar uma' : 'Já tenho conta'}
        </button>
      </form>
    </section>
  )
}
