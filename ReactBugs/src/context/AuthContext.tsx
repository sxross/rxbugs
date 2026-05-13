import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { getToken, setToken as apiSetToken, clearToken as apiClearToken } from '../api'

interface AuthContextValue {
  token: string | null
  isAuthenticated: boolean
  login: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getToken)

  const login = useCallback((newToken: string) => {
    apiSetToken(newToken)
    setTokenState(newToken)
  }, [])

  const logout = useCallback(() => {
    apiClearToken()
    setTokenState(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: token !== null, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
