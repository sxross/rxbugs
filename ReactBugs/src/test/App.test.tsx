import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from './utils'
import App from '../App'

// Mock all views so the route table is tested without real API calls
vi.mock('../views/LoginPage', () => ({
  default: () => <div>mock-login</div>,
}))
vi.mock('../views/BugListPage', () => ({
  default: () => <div>mock-bug-list</div>,
}))
vi.mock('../views/BugDetailPage', () => ({
  default: () => <div>mock-bug-detail</div>,
}))
vi.mock('../views/BugFormPage', () => ({
  default: () => <div>mock-bug-form</div>,
}))
vi.mock('../views/AdminPage', () => ({
  default: () => <div>mock-admin</div>,
}))
describe('App routing', () => {
  it('/login renders LoginPage', () => {
    renderWithProviders(<App />, { route: '/login' })
    expect(screen.getByText('mock-login')).toBeInTheDocument()
  })

  it('/ redirects to /bugs, which redirects to /login when unauthenticated', () => {
    renderWithProviders(<App />, { route: '/' })
    expect(screen.getByText('mock-login')).toBeInTheDocument()
  })

  it('/bugs renders BugListPage when authenticated', () => {
    renderWithProviders(<App />, { route: '/bugs', token: 'tok' })
    expect(screen.getByText('mock-bug-list')).toBeInTheDocument()
  })

  it('/bugs/new renders BugFormPage when authenticated', () => {
    renderWithProviders(<App />, { route: '/bugs/new', token: 'tok' })
    expect(screen.getByText('mock-bug-form')).toBeInTheDocument()
  })

  it('/bugs/:id renders BugDetailPage when authenticated', () => {
    renderWithProviders(<App />, { route: '/bugs/some-id', token: 'tok' })
    expect(screen.getByText('mock-bug-detail')).toBeInTheDocument()
  })

  it('/bugs/:id/edit renders BugFormPage when authenticated', () => {
    renderWithProviders(<App />, { route: '/bugs/some-id/edit', token: 'tok' })
    expect(screen.getByText('mock-bug-form')).toBeInTheDocument()
  })

  it('/admin renders AdminPage when authenticated', () => {
    renderWithProviders(<App />, { route: '/admin', token: 'tok' })
    expect(screen.getByText('mock-admin')).toBeInTheDocument()
  })

  it('unknown route redirects to /bugs → /login when unauthenticated', () => {
    renderWithProviders(<App />, { route: '/does-not-exist' })
    expect(screen.getByText('mock-login')).toBeInTheDocument()
  })
})
