import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { type ReactNode } from 'react'
import { AuthProvider, useAuth } from '../context/AuthContext'

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient()
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('useAuth', () => {
  it('starts unauthenticated when localStorage is empty', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.token).toBeNull()
  })

  it('starts authenticated when token already in localStorage', () => {
    localStorage.setItem('bugtracker_token', 'pre-existing')
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.token).toBe('pre-existing')
  })

  it('login() sets the token and updates isAuthenticated', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    act(() => result.current.login('new-token'))
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.token).toBe('new-token')
    expect(localStorage.getItem('bugtracker_token')).toBe('new-token')
  })

  it('logout() clears the token', () => {
    localStorage.setItem('bugtracker_token', 'tok')
    const { result } = renderHook(() => useAuth(), { wrapper })
    act(() => result.current.logout())
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.token).toBeNull()
    expect(localStorage.getItem('bugtracker_token')).toBeNull()
  })

  it('throws when used outside AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within AuthProvider')
  })
})
