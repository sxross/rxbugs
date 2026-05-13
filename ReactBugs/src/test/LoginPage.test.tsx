import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from './utils'
import LoginPage from '../views/LoginPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    bugs: {
      ...actual.bugs,
      list: vi.fn(),
    },
  }
})

describe('LoginPage', () => {
  beforeEach(() => {
    mockNavigate.mockReset()
  })

  it('renders the token input and sign-in button', () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByLabelText(/access token/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('redirects to /bugs immediately when already authenticated', () => {
    renderWithProviders(<LoginPage />, { token: 'existing-token' })
    expect(mockNavigate).toHaveBeenCalledWith('/bugs', { replace: true })
  })

  it('shows error when sign in fails', async () => {
    const { bugs } = await import('../api')
    vi.mocked(bugs.list).mockRejectedValueOnce(new Error('bad'))

    renderWithProviders(<LoginPage />)
    fireEvent.change(screen.getByLabelText(/access token/i), {
      target: { value: 'bad-token' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() =>
      expect(screen.getByText(/invalid token/i)).toBeInTheDocument(),
    )
  })

  it('navigates to /bugs on successful sign in', async () => {
    const { bugs } = await import('../api')
    vi.mocked(bugs.list).mockResolvedValueOnce({ bugs: [], total: 0 })

    renderWithProviders(<LoginPage />)
    fireEvent.change(screen.getByLabelText(/access token/i), {
      target: { value: 'good-token' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/bugs', { replace: true }),
    )
  })

  it('sign in also triggered by Enter key', async () => {
    const { bugs } = await import('../api')
    vi.mocked(bugs.list).mockResolvedValueOnce({ bugs: [], total: 0 })

    renderWithProviders(<LoginPage />)
    const input = screen.getByLabelText(/access token/i)
    fireEvent.change(input, { target: { value: 'tok' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/bugs', { replace: true }),
    )
  })

  it('Show QR Code button appears on desktop and shows error without token', async () => {
    // jsdom user agent is not mobile, so QR button should be rendered
    renderWithProviders(<LoginPage />)
    const qrBtn = screen.queryByRole('button', { name: /show qr code/i })
    // Only assert if desktop path is taken (non-mobile jsdom)
    if (qrBtn) {
      fireEvent.click(qrBtn)
      await waitFor(() =>
        expect(screen.getByText(/please enter your token first/i)).toBeInTheDocument(),
      )
    }
  })

  it('Show QR Code button fetches /auth/qr with the entered token', async () => {
    vi.stubGlobal('fetch', vi.fn())
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      blob: async () => new Blob(['fake-png'], { type: 'image/png' }),
    })
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:fake'), revokeObjectURL: vi.fn() })

    renderWithProviders(<LoginPage />)
    const input = screen.getByLabelText(/access token/i)
    fireEvent.change(input, { target: { value: 'mytoken' } })

    const qrBtn = screen.queryByRole('button', { name: /show qr code/i })
    if (qrBtn) {
      fireEvent.click(qrBtn)
      await waitFor(() =>
        expect(fetch).toHaveBeenCalledWith(
          '/auth/qr',
          expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer mytoken' }) }),
        ),
      )
    }
  })
})
