import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { api, gravarToken, lerToken } from './api'
import Assistente from './pages/Assistente'
import Catalogo from './pages/Catalogo'
import Entrar from './pages/Entrar'
import MedidasPagina from './pages/Medidas'

interface Sessao {
  username: string | null
  entrar: (token: string, username: string) => void
  sair: () => void
}

const SessaoCtx = createContext<Sessao>({ username: null, entrar: () => {}, sair: () => {} })
export const useSessao = () => useContext(SessaoCtx)

export default function App() {
  const [username, setUsername] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(Boolean(lerToken()))

  useEffect(() => {
    if (!lerToken()) return
    api<{ username: string }>('auth/eu')
      .then((eu) => setUsername(eu.username))
      .catch(() => gravarToken(null))
      .finally(() => setCarregando(false))
  }, [])

  const entrar = useCallback((token: string, nome: string) => {
    gravarToken(token)
    setUsername(nome)
  }, [])
  const sair = useCallback(() => {
    gravarToken(null)
    setUsername(null)
  }, [])

  if (carregando) return null

  return (
    <SessaoCtx.Provider value={{ username, entrar, sair }}>
      <BrowserRouter>
        <header className="topo">
          <div className="topo-dentro">
            <NavLink to="/" className="marca">
              <svg viewBox="0 0 32 32" aria-hidden="true">
                <rect width="32" height="32" rx="8" />
                <path d="M11 6v12h11M11 18l-1 8M22 18l1 8M16 18v8" />
              </svg>
              Ergo Assist
            </NavLink>
            <nav>
              <NavLink to="/" end>Assistente</NavLink>
              <NavLink to="/medidas">Minhas medidas</NavLink>
              <NavLink to="/catalogo">Catálogo</NavLink>
            </nav>
            <div className="topo-usuario">
              {username ? (
                <>
                  <span>{username}</span>
                  <button className="link" onClick={sair}>Sair</button>
                </>
              ) : (
                <NavLink to="/entrar">Entrar</NavLink>
              )}
            </div>
          </div>
        </header>
        <main>
          <Routes>
            <Route path="/" element={username ? <Assistente /> : <Navigate to="/entrar" />} />
            <Route path="/medidas" element={<MedidasPagina />} />
            <Route path="/catalogo" element={<Catalogo />} />
            <Route path="/entrar" element={username ? <Navigate to="/" /> : <Entrar />} />
          </Routes>
        </main>
      </BrowserRouter>
    </SessaoCtx.Provider>
  )
}
