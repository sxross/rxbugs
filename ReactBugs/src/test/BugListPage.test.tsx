import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders, mockBugSummary, mockProducts, mockAreas, mockPlatforms, mockSeverities } from './utils'
import BugListPage from '../views/BugListPage'

vi.mock('../api', () => ({
  bugs: { list: vi.fn() },
  products: { list: vi.fn() },
  areas: { list: vi.fn() },
  platforms: { list: vi.fn() },
  severities: { list: vi.fn() },
  getToken: vi.fn(() => 'test-token'),
}))

async function getApi() {
  return import('../api')
}

describe('BugListPage', () => {
  beforeEach(async () => {
    const api = await getApi()
    vi.mocked(api.products.list).mockResolvedValue(mockProducts)
    vi.mocked(api.areas.list).mockResolvedValue(mockAreas)
    vi.mocked(api.platforms.list).mockResolvedValue(mockPlatforms)
    vi.mocked(api.severities.list).mockResolvedValue(mockSeverities)
    vi.mocked(api.bugs.list).mockResolvedValue({ bugs: [mockBugSummary], total: 1 })
  })

  it('renders the bug table with data', async () => {
    renderWithProviders(<BugListPage />, { token: 'tok' })
    await waitFor(() => expect(screen.getByText('Test bug title')).toBeInTheDocument())
    // 'TestApp' appears in both the filter dropdown and the bug row
    expect(screen.getAllByText('TestApp').length).toBeGreaterThan(0)
    expect(screen.getByText('open')).toBeInTheDocument()
  })

  it('renders + New bug link', async () => {
    renderWithProviders(<BugListPage />, { token: 'tok' })
    expect(screen.getByRole('link', { name: /new bug/i })).toBeInTheDocument()
  })

  it('shows empty state message when no bugs', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.list).mockResolvedValue({ bugs: [], total: 0 })
    renderWithProviders(<BugListPage />, { token: 'tok' })
    await waitFor(() => expect(screen.getByText(/no bugs found/i)).toBeInTheDocument())
  })

  it('shows error message when fetch fails', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.list).mockRejectedValue(new Error('network error'))
    renderWithProviders(<BugListPage />, { token: 'tok' })
    await waitFor(() => expect(screen.getByText(/failed to load bugs/i)).toBeInTheDocument())
  })

  it('status toggle updates the filter', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.list).mockResolvedValue({ bugs: [], total: 0 })
    renderWithProviders(<BugListPage />, { token: 'tok' })
    await waitFor(() => screen.getByText(/no bugs found/i))

    fireEvent.click(screen.getByRole('button', { name: 'Closed' }))
    await waitFor(() => {
      const call = vi.mocked(api.bugs.list).mock.calls.at(-1)?.[0]
      expect(call?.status).toBe('closed')
    })
  })

  it('search input debounces and updates the filter', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.list).mockResolvedValue({ bugs: [], total: 0 })
    renderWithProviders(<BugListPage />, { token: 'tok' })
    await waitFor(() => screen.getByText(/no bugs found/i))

    const search = screen.getByPlaceholderText(/search bugs/i)
    fireEvent.change(search, { target: { value: 'crash' } })
    await waitFor(() => {
      const calls = vi.mocked(api.bugs.list).mock.calls
      const last = calls.at(-1)?.[0]
      expect(last?.q).toBe('crash')
    })
  })

  it('renders pagination when multiple pages', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.list).mockResolvedValue({
      bugs: Array.from({ length: 25 }, (_, i) => ({
        ...mockBugSummary,
        id: `id-${i}`,
        title: `Bug ${i}`,
      })),
      total: 50,
    })
    renderWithProviders(<BugListPage />, { token: 'tok' })
    await waitFor(() => expect(screen.getByText(/page 1 of 2/i)).toBeInTheDocument())
  })

  it('pagination next button calls list with page 2', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.list).mockResolvedValue({
      bugs: Array.from({ length: 25 }, (_, i) => ({
        ...mockBugSummary,
        id: `id-${i}`,
        title: `Bug ${i}`,
      })),
      total: 50,
    })
    renderWithProviders(<BugListPage />, { token: 'tok' })
    await waitFor(() => screen.getByText(/page 1 of 2/i))
    fireEvent.click(screen.getByRole('button', { name: '›' }))
    await waitFor(() => {
      const last = vi.mocked(api.bugs.list).mock.calls.at(-1)?.[0]
      expect(last?.page).toBe(2)
    })
  })

  it('bug title is a link to the detail page', async () => {
    renderWithProviders(<BugListPage />, { token: 'tok' })
    await waitFor(() => expect(screen.getByText('Test bug title')).toBeInTheDocument())
    const link = screen.getByRole('link', { name: 'Test bug title' })
    expect(link).toHaveAttribute('href', expect.stringContaining(mockBugSummary.id))
  })
})
