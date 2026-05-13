import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders, mockProducts, mockAreas, mockSeverities, mockPlatforms, mockAgents } from './utils'
import AdminPage from '../views/AdminPage'

vi.mock('../api', () => ({
  products: { list: vi.fn(), create: vi.fn(), update: vi.fn() },
  areas: { list: vi.fn(), create: vi.fn(), update: vi.fn() },
  severities: { list: vi.fn(), create: vi.fn(), update: vi.fn() },
  platforms: { list: vi.fn(), create: vi.fn(), update: vi.fn() },
  agentsApi: { list: vi.fn(), register: vi.fn(), revoke: vi.fn() },
  getToken: vi.fn(() => 'test-token'),
  setToken: vi.fn(),
  clearToken: vi.fn(),
}))

async function getApi() {
  return import('../api')
}

describe('AdminPage', () => {
  beforeEach(async () => {
    const api = await getApi()
    vi.mocked(api.products.list).mockResolvedValue(mockProducts)
    vi.mocked(api.areas.list).mockResolvedValue(mockAreas)
    vi.mocked(api.severities.list).mockResolvedValue(mockSeverities)
    vi.mocked(api.platforms.list).mockResolvedValue(mockPlatforms)
    vi.mocked(api.agentsApi.list).mockResolvedValue(mockAgents)
  })

  it('renders tab navigation', () => {
    renderWithProviders(<AdminPage />, { token: 'tok' })
    expect(screen.getByRole('button', { name: 'Products' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Areas' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Severities' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Platforms' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agents' })).toBeInTheDocument()
  })

  it('defaults to Products tab and loads products', async () => {
    renderWithProviders(<AdminPage />, { token: 'tok' })
    await waitFor(() => expect(screen.getByText('TestApp')).toBeInTheDocument())
    expect(screen.getByText('OtherApp')).toBeInTheDocument()
  })

  it('hides archived items by default', async () => {
    renderWithProviders(<AdminPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('TestApp'))
    expect(screen.queryByText('OldApp')).not.toBeInTheDocument()
  })

  it('shows archived items when toggle checked', async () => {
    renderWithProviders(<AdminPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('TestApp'))
    fireEvent.click(screen.getByLabelText(/show archived/i))
    expect(screen.getByText('OldApp')).toBeInTheDocument()
  })

  it('switching to Areas tab loads areas', async () => {
    const api = await getApi()
    renderWithProviders(<AdminPage />, { token: 'tok' })
    fireEvent.click(screen.getByRole('button', { name: 'Areas' }))
    await waitFor(() => expect(api.areas.list).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText('Frontend')).toBeInTheDocument())
  })

  it('create product form calls products.create', async () => {
    const api = await getApi()
    vi.mocked(api.products.create).mockResolvedValue({
      name: 'NewProduct', description: null, archived: false, bug_count: 0,
    })
    renderWithProviders(<AdminPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('TestApp'))

    const nameInput = screen.getByPlaceholderText(/new product name/i)
    fireEvent.change(nameInput, { target: { value: 'NewProduct' } })
    fireEvent.click(screen.getByRole('button', { name: /^add$/i }))
    await waitFor(() =>
      // LookupTable converts empty description '' to undefined before calling create
      expect(api.products.create).toHaveBeenCalledWith('NewProduct', undefined),
    )
  })

  it('archive button calls products.update with archived: true', async () => {
    const api = await getApi()
    vi.mocked(api.products.update).mockResolvedValue({ ...mockProducts[0], archived: true })
    renderWithProviders(<AdminPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('TestApp'))

    const archiveBtns = screen.getAllByRole('button', { name: /archive/i })
    fireEvent.click(archiveBtns[0])
    await waitFor(() =>
      expect(api.products.update).toHaveBeenCalledWith('TestApp', { archived: true }),
    )
  })

  it('Agents tab loads agents', async () => {
    const api = await getApi()
    renderWithProviders(<AdminPage />, { token: 'tok' })
    fireEvent.click(screen.getByRole('button', { name: 'Agents' }))
    await waitFor(() => expect(api.agentsApi.list).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText('CI Bot')).toBeInTheDocument())
  })

  it('register agent calls agentsApi.register', async () => {
    const api = await getApi()
    vi.mocked(api.agentsApi.register).mockResolvedValue({
      key: 'new-key', name: 'My Agent', description: null,
      created_at: new Date().toISOString(), active: true,
    })
    renderWithProviders(<AdminPage />, { token: 'tok' })
    fireEvent.click(screen.getByRole('button', { name: 'Agents' }))
    await waitFor(() => screen.getByText('CI Bot'))

    fireEvent.change(screen.getByPlaceholderText(/agent name/i), {
      target: { value: 'My Agent' },
    })
    fireEvent.click(screen.getByRole('button', { name: /register/i }))
    await waitFor(() =>
      expect(api.agentsApi.register).toHaveBeenCalledWith('My Agent', undefined, undefined),
    )
  })

  it('revoke agent calls agentsApi.revoke', async () => {
    const api = await getApi()
    vi.mocked(api.agentsApi.revoke).mockResolvedValue(undefined)
    renderWithProviders(<AdminPage />, { token: 'tok' })
    fireEvent.click(screen.getByRole('button', { name: 'Agents' }))
    await waitFor(() => screen.getByText('CI Bot'))

    fireEvent.click(screen.getByRole('button', { name: /revoke/i }))
    await waitFor(() =>
      expect(api.agentsApi.revoke).toHaveBeenCalledWith(mockAgents[0].key),
    )
  })

  it('Severities tab loads severities', async () => {
    const api = await getApi()
    renderWithProviders(<AdminPage />, { token: 'tok' })
    fireEvent.click(screen.getByRole('button', { name: 'Severities' }))
    await waitFor(() => expect(api.severities.list).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText('Major')).toBeInTheDocument())
  })

  it('Platforms tab loads platforms', async () => {
    const api = await getApi()
    renderWithProviders(<AdminPage />, { token: 'tok' })
    fireEvent.click(screen.getByRole('button', { name: 'Platforms' }))
    await waitFor(() => expect(api.platforms.list).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText('Web')).toBeInTheDocument())
  })

  it('shows empty message when no items', async () => {
    const api = await getApi()
    vi.mocked(api.areas.list).mockResolvedValue([])
    renderWithProviders(<AdminPage />, { token: 'tok' })
    fireEvent.click(screen.getByRole('button', { name: 'Areas' }))
    await waitFor(() => expect(screen.getByText(/no areas yet/i)).toBeInTheDocument())
  })
})
