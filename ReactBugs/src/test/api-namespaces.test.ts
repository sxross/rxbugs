/**
 * Direct tests for each API namespace function.
 * fetch is stubbed; these tests verify the correct URL and method are used.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setToken, clearToken } from '../api'

function okJson(data: unknown) {
  return Promise.resolve({ ok: true, status: 200, json: async () => data })
}
function ok204() {
  return Promise.resolve({ ok: true, status: 204 })
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
  setToken('test')
})

function lastCall() {
  const f = fetch as ReturnType<typeof vi.fn>
  return { url: f.mock.calls.at(-1)?.[0] as string, opts: f.mock.calls.at(-1)?.[1] as RequestInit }
}

describe('bugs namespace', () => {
  it('list builds correct query string', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ bugs: [], total: 0 }))
    const { bugs } = await import('../api')
    await bugs.list({ status: 'open', product: ['App'], priority: [1, 2], page: 2, per_page: 10 })
    expect(lastCall().url).toContain('status=open')
    expect(lastCall().url).toContain('product=App')
    expect(lastCall().url).toContain('priority=1')
    expect(lastCall().url).toContain('page=2')
  })

  it('get fetches /bugs/:id', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ id: 'x' }))
    const { bugs } = await import('../api')
    await bugs.get('x')
    expect(lastCall().url).toBe('/bugs/x')
  })

  it('update sends PATCH', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ id: 'x' }))
    const { bugs } = await import('../api')
    await bugs.update('x', { title: 'new' })
    expect(lastCall().opts.method).toBe('PATCH')
    expect(lastCall().url).toBe('/bugs/x')
  })

  it('close sends POST to /bugs/:id/close', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ bug: { id: 'x' } }))
    const { bugs } = await import('../api')
    await bugs.close('x', 'fixed', 'done')
    expect(lastCall().url).toBe('/bugs/x/close')
    expect(lastCall().opts.method).toBe('POST')
  })

  it('reopen sends POST to /bugs/:id/reopen', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ id: 'x' }))
    const { bugs } = await import('../api')
    await bugs.reopen('x')
    expect(lastCall().url).toBe('/bugs/x/reopen')
    expect(lastCall().opts.method).toBe('POST')
  })

  it('list with all optional filter fields builds full qs', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ bugs: [], total: 0 }))
    const { bugs } = await import('../api')
    await bugs.list({
      q: 'crash', status: 'all', related_to: 'abc', created_after: '2024-01-01',
      created_before: '2024-12-31', has_artifacts: true,
      area: ['FE'], platform: ['Web'], severity: ['Major'], resolution: ['fixed'],
    })
    const url = lastCall().url
    expect(url).toContain('q=crash')
    expect(url).toContain('has_artifacts=true')
    expect(url).toContain('related_to=abc')
    expect(url).toContain('created_after=2024-01-01')
    expect(url).toContain('area=FE')
    expect(url).toContain('severity=Major')
    expect(url).toContain('resolution=fixed')
  })
})

describe('annotations namespace', () => {
  it('create posts to /bugs/:id/annotations', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ id: 1 }))
    const { annotations } = await import('../api')
    await annotations.create('bug-id', 'hello')
    expect(lastCall().url).toBe('/bugs/bug-id/annotations')
    expect(lastCall().opts.method).toBe('POST')
  })
})

describe('artifacts namespace', () => {
  it('upload posts FormData to /bugs/:id/artifacts', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ id: 1 }))
    const { artifacts } = await import('../api')
    await artifacts.upload('bug-id', new File(['x'], 'x.txt'))
    expect(lastCall().url).toBe('/bugs/bug-id/artifacts')
    expect(lastCall().opts.method).toBe('POST')
    expect(lastCall().opts.body).toBeInstanceOf(FormData)
  })
})

describe('relations namespace', () => {
  it('add posts to /bugs/:id/relations', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ bug_id: 'a', related_id: 'b' }))
    const { relations } = await import('../api')
    await relations.add('a', 'b')
    expect(lastCall().url).toBe('/bugs/a/relations')
    expect(lastCall().opts.method).toBe('POST')
  })

  it('remove sends DELETE', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockImplementationOnce(() => ok204())
    const { relations } = await import('../api')
    await relations.remove('a', 'b')
    expect(lastCall().url).toBe('/bugs/a/relations/b')
    expect(lastCall().opts.method).toBe('DELETE')
  })
})

describe('products namespace', () => {
  it('list with includeArchived=true appends query param', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson([]))
    const { products } = await import('../api')
    await products.list(true)
    expect(lastCall().url).toContain('include_archived=true')
  })

  it('list without arg hits /api/products', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson([]))
    const { products } = await import('../api')
    await products.list()
    expect(lastCall().url).toBe('/api/products')
  })

  it('create posts to /api/products', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ name: 'P' }))
    const { products } = await import('../api')
    await products.create('P', 'desc')
    expect(lastCall().url).toBe('/api/products')
    expect(lastCall().opts.method).toBe('POST')
  })

  it('update patches /api/products/:name (URL encodes spaces)', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ name: 'My App' }))
    const { products } = await import('../api')
    await products.update('My App', { archived: true })
    expect(lastCall().url).toBe('/api/products/My%20App')
    expect(lastCall().opts.method).toBe('PATCH')
  })
})

describe('areas / severities / platforms namespaces', () => {
  it('areas.list, create, update work correctly', async () => {
    const f = fetch as ReturnType<typeof vi.fn>
    f.mockResolvedValue(okJson([]))
    const { areas } = await import('../api')
    await areas.list(true)
    expect(lastCall().url).toContain('include_archived')
    f.mockResolvedValue(okJson({ name: 'A' }))
    await areas.create('A')
    expect(lastCall().url).toBe('/api/areas')
    await areas.update('A', { name: 'B' })
    expect(lastCall().url).toBe('/api/areas/A')
  })

  it('severities.list, create, update', async () => {
    const f = fetch as ReturnType<typeof vi.fn>
    f.mockResolvedValue(okJson([]))
    const { severities } = await import('../api')
    await severities.list()
    await severities.list(true)
    f.mockResolvedValue(okJson({ name: 'S' }))
    await severities.create('S', 'desc')
    await severities.update('S', { archived: false })
    expect(lastCall().url).toBe('/api/severities/S')
  })

  it('platforms.list, create, update', async () => {
    const f = fetch as ReturnType<typeof vi.fn>
    f.mockResolvedValue(okJson([]))
    const { platforms } = await import('../api')
    await platforms.list()
    await platforms.list(true)
    f.mockResolvedValue(okJson({ name: 'P' }))
    await platforms.create('P')
    await platforms.update('P', { name: 'Q' })
    expect(lastCall().url).toBe('/api/platforms/P')
  })
})

describe('agentsApi namespace', () => {
  it('list fetches /agents', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson([]))
    const { agentsApi } = await import('../api')
    await agentsApi.list()
    expect(lastCall().url).toBe('/agents')
  })

  it('register posts to /agents with optional fields', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ key: 'k' }))
    const { agentsApi } = await import('../api')
    await agentsApi.register('bot', 'desc', 30)
    expect(lastCall().url).toBe('/agents')
    expect(lastCall().opts.method).toBe('POST')
  })

  it('revoke deletes /agents/:key', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockImplementationOnce(() => ok204())
    const { agentsApi } = await import('../api')
    await agentsApi.revoke('k')
    expect(lastCall().url).toBe('/agents/k')
    expect(lastCall().opts.method).toBe('DELETE')
  })
})

describe('authApi namespace', () => {
  it('getQr fetches /auth/qr', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      okJson({ qr_url: 'http://x', session_id: 's' }),
    )
    const { authApi } = await import('../api')
    await authApi.getQr()
    expect(lastCall().url).toBe('/auth/qr')
  })

  it('pollSession posts to /auth/session', async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okJson({ token: 't' }))
    const { authApi } = await import('../api')
    await authApi.pollSession('session-123')
    expect(lastCall().url).toBe('/auth/session')
    expect(lastCall().opts.method).toBe('POST')
  })
})

describe('apiFetch error path — fallback message', () => {
  it('uses HTTP status message when server JSON parse fails', async () => {
    clearToken()
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false, status: 500, json: async () => { throw new Error('not json') },
    })
    const { bugs } = await import('../api')
    await expect(bugs.list()).rejects.toMatchObject({ status: 500, message: 'HTTP 500' })
  })
})
