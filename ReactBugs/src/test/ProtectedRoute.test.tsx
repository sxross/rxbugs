import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from './utils'
import ProtectedRoute from '../components/ProtectedRoute'

describe('ProtectedRoute', () => {
  it('redirects to /login when no token', () => {
    renderWithProviders(
      <ProtectedRoute><p>secret</p></ProtectedRoute>,
    )
    expect(screen.queryByText('secret')).not.toBeInTheDocument()
  })

  it('renders children inside AppLayout when authenticated', () => {
    renderWithProviders(
      <ProtectedRoute><p>secret content</p></ProtectedRoute>,
      { token: 'valid-token' },
    )
    expect(screen.getByText('secret content')).toBeInTheDocument()
    // AppLayout header should be present
    expect(screen.getByText('RxBugs')).toBeInTheDocument()
  })
})
