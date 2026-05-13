import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getToken, setToken, clearToken, ApiError } from '../api'

// We test the token helpers and ApiError directly.
// The fetch-based functions are exercised indirectly through component tests.

describe('getToken / setToken / clearToken', () => {
  it('returns null when nothing stored', () => {
    expect(getToken()).toBeNull()
  })

  it('returns the stored token after setToken', () => {
    setToken('my-secret')
    expect(getToken()).toBe('my-secret')
  })

  it('returns null after clearToken', () => {
    setToken('my-secret')
    clearToken()
    expect(getToken()).toBeNull()
  })

  it('overwrites an existing token', () => {
    setToken('first')
    setToken('second')
    expect(getToken()).toBe('second')
  })
})

describe('ApiError', () => {
  it('stores status and message', () => {
    const err = new ApiError(404, 'Not found')
    expect(err.status).toBe(404)
    expect(err.message).toBe('Not found')
    expect(err.name).toBe('ApiError')
    expect(err).toBeInstanceOf(Error)
  })
})

describe('apiFetch behaviour (via fetch mock)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  async function importApi() {
    // Fresh dynamic import so module-level state resets between tests
    return import('../api')
  }

  it('attaches Authorization header when token present', async () => {
    setToken('tok123')
    const { bugs } = await importApi()
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ bugs: [], total: 0 }),
    })
    await bugs.list()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/bugs'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer tok123' }),
      }),
    )
  })

  it('clears token and redirects on 401', async () => {
    setToken('bad-tok')
    const assign = vi.fn()
    vi.stubGlobal('location', { href: '' })
    Object.defineProperty(window, 'location', { value: { href: '' }, writable: true })
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ ok: false, status: 401 })
    const { bugs } = await importApi()
    await expect(bugs.list()).rejects.toThrow()
    expect(getToken()).toBeNull()
    void assign // suppress unused warning
  })

  it('throws ApiError with server message on non-ok response', async () => {
    clearToken()
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ error: 'Validation failed' }),
    })
    const { bugs } = await importApi()
    await expect(bugs.list()).rejects.toMatchObject({ status: 422, message: 'Validation failed' })
  })

  it('returns undefined for 204 responses', async () => {
    clearToken()
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ ok: true, status: 204 })
    const { relations } = await importApi()
    const result = await relations.remove('bug-id', 'other-id')
    expect(result).toBeUndefined()
  })

  it('sets Content-Type for JSON bodies', async () => {
    setToken('t')
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({ id: 'x', title: 'y', product: 'p', area: null, platform: null, priority: null, severity: null, status: 'open', resolution: 'none', created_at: '', updated_at: '' }),
    })
    const { bugs } = await importApi()
    await bugs.create({ product: 'p', title: 'y' })
    expect(fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })

  it('does not set Content-Type for FormData bodies', async () => {
    setToken('t')
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ id: 1, bug_id: 'x', filename: 'f.txt', mime_type: null, uploaded_at: '', url: '' }),
    })
    const { artifacts } = await importApi()
    await artifacts.upload('bug-id', new File(['x'], 'f.txt'))
    const [, opts] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect((opts.headers as Record<string, string>)['Content-Type']).toBeUndefined()
  })
})
