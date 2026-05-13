import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders, mockBug } from './utils'
import BugDetailPage from '../views/BugDetailPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: mockBug.id }),
  }
})

vi.mock('../api', () => ({
  bugs: {
    get: vi.fn(),
    close: vi.fn(),
    reopen: vi.fn(),
  },
  annotations: { create: vi.fn() },
  artifacts: { upload: vi.fn() },
  relations: {
    add: vi.fn(),
    remove: vi.fn(),
  },
  getToken: vi.fn(() => 'test-token'),
}))

async function getApi() {
  return import('../api')
}

describe('BugDetailPage', () => {
  beforeEach(async () => {
    mockNavigate.mockReset()
    const api = await getApi()
    vi.mocked(api.bugs.get).mockResolvedValue(mockBug)
  })

  it('renders bug title and metadata', async () => {
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => expect(screen.getByText('Test bug title')).toBeInTheDocument())
    expect(screen.getByText('TestApp')).toBeInTheDocument()
    expect(screen.getByText('Frontend')).toBeInTheDocument()
    expect(screen.getByText('Steps to reproduce the issue.')).toBeInTheDocument()
  })

  it('renders existing annotation', async () => {
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => expect(screen.getByText('First annotation')).toBeInTheDocument())
    expect(screen.getByText('alice')).toBeInTheDocument()
  })

  it('renders artifact filename', async () => {
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => expect(screen.getByText('screenshot.png')).toBeInTheDocument())
  })

  it('renders related bug ID', async () => {
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() =>
      expect(screen.getByText('other-id')).toBeInTheDocument(),
    )
  })

  it('shows loading skeletons initially', () => {
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    // Skeleton divs are present before data arrives
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('shows error state when bug fetch fails', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.get).mockRejectedValue(new Error('not found'))
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() =>
      expect(screen.getByText(/bug not found or failed to load/i)).toBeInTheDocument(),
    )
  })

  it('go back button on error calls navigate(-1)', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.get).mockRejectedValue(new Error('not found'))
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => screen.getByText(/go back/i))
    fireEvent.click(screen.getByText(/go back/i))
    expect(mockNavigate).toHaveBeenCalledWith(-1)
  })

  it('Post annotation button calls annotations.create', async () => {
    const api = await getApi()
    vi.mocked(api.annotations.create).mockResolvedValue({
      id: 2, bug_id: mockBug.id, author: 'me', author_type: 'human',
      body: 'new note', created_at: new Date().toISOString(),
    })
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('Test bug title'))

    const textarea = screen.getByPlaceholderText(/add an annotation/i)
    fireEvent.change(textarea, { target: { value: 'new note' } })
    fireEvent.click(screen.getByRole('button', { name: /post/i }))
    await waitFor(() =>
      expect(api.annotations.create).toHaveBeenCalledWith(mockBug.id, 'new note'),
    )
  })

  it('Post button is disabled when textarea is empty', async () => {
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('Test bug title'))
    expect(screen.getByRole('button', { name: /^post$/i })).toBeDisabled()
  })

  it('Close button opens the close dialog for open bugs', async () => {
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('Test bug title'))
    fireEvent.click(screen.getByRole('button', { name: /^close$/i }))
    // dialog heading
    expect(screen.getByRole('heading', { name: /close bug/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/resolution/i)).toBeInTheDocument()
  })

  it('close dialog Cancel hides the dialog', async () => {
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('Test bug title'))
    fireEvent.click(screen.getByRole('button', { name: /^close$/i }))
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(screen.queryByText('Close bug')).not.toBeInTheDocument()
  })

  it('close dialog submits with chosen resolution', async () => {
    const api = await getApi()
    vi.mocked(api.bugs.close).mockResolvedValue({ bug: { ...mockBug, status: 'closed' } })
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('Test bug title'))

    fireEvent.click(screen.getByRole('button', { name: /^close$/i }))
    fireEvent.change(screen.getByLabelText(/resolution/i), { target: { value: 'fixed' } })
    fireEvent.click(screen.getByRole('button', { name: /close bug/i }))
    await waitFor(() =>
      expect(api.bugs.close).toHaveBeenCalledWith(mockBug.id, 'fixed', undefined),
    )
  })

  it('Reopen button shown and works for closed bugs', async () => {
    const api = await getApi()
    const closedBug = { ...mockBug, status: 'closed' as const }
    vi.mocked(api.bugs.get).mockResolvedValue(closedBug)
    vi.mocked(api.bugs.reopen).mockResolvedValue({ ...mockBug, status: 'open' })
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => screen.getByRole('button', { name: /reopen/i }))
    fireEvent.click(screen.getByRole('button', { name: /reopen/i }))
    await waitFor(() => expect(api.bugs.reopen).toHaveBeenCalledWith(mockBug.id))
  })

  it('Edit link points to the edit route', async () => {
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('Test bug title'))
    const editLink = screen.getByRole('link', { name: /edit/i })
    expect(editLink).toHaveAttribute('href', expect.stringContaining('/edit'))
  })

  it('Add relation and remove relation', async () => {
    const api = await getApi()
    vi.mocked(api.relations.add).mockResolvedValue({ bug_id: mockBug.id, related_id: 'new-rel' })
    vi.mocked(api.relations.remove).mockResolvedValue(undefined)
    renderWithProviders(<BugDetailPage />, { token: 'tok' })
    await waitFor(() => screen.getByText('Test bug title'))

    // Add relation
    const relInput = screen.getByPlaceholderText(/bug id…/i)
    fireEvent.change(relInput, { target: { value: 'new-rel' } })
    fireEvent.click(screen.getByRole('button', { name: /^add$/i }))
    await waitFor(() => expect(api.relations.add).toHaveBeenCalledWith(mockBug.id, 'new-rel'))

    // Remove existing relation
    const removeBtn = screen.getByRole('button', { name: '×' })
    fireEvent.click(removeBtn)
    await waitFor(() =>
      expect(api.relations.remove).toHaveBeenCalledWith(
        mockBug.id,
        mockBug.related_bugs[0],
      ),
    )
  })
})
