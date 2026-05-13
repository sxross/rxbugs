import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders, mockBug, mockProducts, mockAreas, mockPlatforms, mockSeverities } from './utils'
import BugFormPage from '../views/BugFormPage'

const mockNavigate = vi.fn()
let mockParamId: string | undefined = undefined

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: mockParamId }),
  }
})

vi.mock('../api', () => ({
  bugs: { get: vi.fn(), create: vi.fn(), update: vi.fn() },
  products: { list: vi.fn() },
  areas: { list: vi.fn() },
  platforms: { list: vi.fn() },
  severities: { list: vi.fn() },
  getToken: vi.fn(() => 'test-token'),
  setToken: vi.fn(),
  clearToken: vi.fn(),
}))

async function getApi() {
  return import('../api')
}

describe('BugFormPage — create mode', () => {
  beforeEach(async () => {
    mockParamId = undefined
    mockNavigate.mockReset()
    const api = await getApi()
    vi.mocked(api.products.list).mockResolvedValue(mockProducts)
    vi.mocked(api.areas.list).mockResolvedValue(mockAreas)
    vi.mocked(api.platforms.list).mockResolvedValue(mockPlatforms)
    vi.mocked(api.severities.list).mockResolvedValue(mockSeverities)
  })

  it('renders "New bug" heading', () => {
    renderWithProviders(<BugFormPage />, { token: 'tok' })
    expect(screen.getByText('New bug')).toBeInTheDocument()
  })

  it('shows validation error when title is empty', async () => {
    renderWithProviders(<BugFormPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('New bug'))
    fireEvent.click(screen.getByRole('button', { name: /create bug/i }))
    expect(screen.getByText(/title is required/i)).toBeInTheDocument()
  })

  it('shows validation error when product not selected', async () => {
    renderWithProviders(<BugFormPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('New bug'))
    fireEvent.change(screen.getByPlaceholderText(/short, descriptive title/i), {
      target: { value: 'My bug' },
    })
    fireEvent.click(screen.getByRole('button', { name: /create bug/i }))
    expect(screen.getByText(/product is required/i)).toBeInTheDocument()
  })

  it('submits and navigates to the new bug on success', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.create).mockResolvedValue({ ...mockBug, id: 'new-id' })

    renderWithProviders(<BugFormPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('New bug'))

    fireEvent.change(screen.getByPlaceholderText(/short, descriptive title/i), {
      target: { value: 'My new bug' },
    })
    // Select product
    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'TestApp' } })
    fireEvent.click(screen.getByRole('button', { name: /create bug/i }))

    await waitFor(() =>
      expect(api.bugs.create).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'My new bug', product: 'TestApp' }),
      ),
    )
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/bugs/new-id'),
    )
  })

  it('shows error message when create fails', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.create).mockRejectedValue(new Error('server error'))

    renderWithProviders(<BugFormPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('New bug'))

    fireEvent.change(screen.getByPlaceholderText(/short, descriptive title/i), {
      target: { value: 'My bug' },
    })
    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'TestApp' } })
    fireEvent.click(screen.getByRole('button', { name: /create bug/i }))

    await waitFor(() =>
      expect(screen.getByText(/failed to create bug/i)).toBeInTheDocument(),
    )
  })

  it('Cancel navigates back', () => {
    renderWithProviders(<BugFormPage />, { token: 'tok' })
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(mockNavigate).toHaveBeenCalledWith(-1)
  })
})

describe('BugFormPage — edit mode', () => {
  beforeEach(async () => {
    mockParamId = mockBug.id
    mockNavigate.mockReset()
    const api = await getApi()
    vi.mocked(api.bugs.get).mockResolvedValue(mockBug)
    vi.mocked(api.products.list).mockResolvedValue(mockProducts)
    vi.mocked(api.areas.list).mockResolvedValue(mockAreas)
    vi.mocked(api.platforms.list).mockResolvedValue(mockPlatforms)
    vi.mocked(api.severities.list).mockResolvedValue(mockSeverities)
  })

  it('renders "Edit bug" heading', async () => {
    renderWithProviders(<BugFormPage />, { token: 'tok' })
    await waitFor(() => expect(screen.getByText('Edit bug')).toBeInTheDocument())
  })

  it('pre-populates title from existing bug', async () => {
    renderWithProviders(<BugFormPage />, { token: 'tok' })
    await waitFor(() =>
      expect(screen.getByDisplayValue('Test bug title')).toBeInTheDocument(),
    )
  })

  it('submits PATCH and navigates to bug on success', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.update).mockResolvedValue({ ...mockBug, title: 'Updated title' })

    renderWithProviders(<BugFormPage />, { token: 'tok' })
    await waitFor(() => screen.getByDisplayValue('Test bug title'))

    fireEvent.change(screen.getByPlaceholderText(/short, descriptive title/i), {
      target: { value: 'Updated title' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() =>
      expect(api.bugs.update).toHaveBeenCalledWith(
        mockBug.id,
        expect.objectContaining({ title: 'Updated title' }),
      ),
    )
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith(`/bugs/${mockBug.id}`),
    )
  })
})
