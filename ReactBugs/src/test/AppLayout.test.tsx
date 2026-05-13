import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from './utils'
import AppLayout from '../components/AppLayout'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

describe('AppLayout', () => {
  it('renders brand name and nav links', () => {
    renderWithProviders(<AppLayout><p>content</p></AppLayout>, { token: 'tok' })
    expect(screen.getByText('RxBugs')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Bugs' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Admin' })).toBeInTheDocument()
  })

  it('renders children', () => {
    renderWithProviders(<AppLayout><p>child content</p></AppLayout>, { token: 'tok' })
    expect(screen.getByText('child content')).toBeInTheDocument()
  })

  it('sign out clears token and navigates to /login', () => {
    localStorage.setItem('bugtracker_token', 'tok')
    renderWithProviders(<AppLayout><p>x</p></AppLayout>, { token: 'tok' })
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    expect(localStorage.getItem('bugtracker_token')).toBeNull()
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
  })
})
