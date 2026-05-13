import { type ReactNode } from 'react'
import { render, type RenderResult } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, type MemoryRouterProps } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'

interface RenderOptions {
  route?: string
  routerProps?: MemoryRouterProps
  token?: string | null
}

export function renderWithProviders(
  ui: ReactNode,
  { route = '/', token = null }: RenderOptions = {},
): RenderResult {
  if (token) localStorage.setItem('bugtracker_token', token)

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// Shared mock data
export const mockBugSummary = {
  id: 'abc12345-0000-0000-0000-000000000001',
  title: 'Test bug title',
  product: 'TestApp',
  area: 'Frontend',
  platform: 'Web',
  priority: 2 as const,
  severity: 'Major',
  status: 'open' as const,
  resolution: 'none' as const,
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
}

export const mockBug = {
  ...mockBugSummary,
  description: 'Steps to reproduce the issue.',
  annotations: [
    {
      id: 1,
      bug_id: mockBugSummary.id,
      author: 'alice',
      author_type: 'human' as const,
      body: 'First annotation',
      created_at: '2024-01-15T11:00:00Z',
    },
  ],
  artifacts: [
    {
      id: 1,
      bug_id: mockBugSummary.id,
      filename: 'screenshot.png',
      mime_type: 'image/png',
      uploaded_at: '2024-01-15T12:00:00Z',
      url: '/bugs/abc12345/artifacts/1',
    },
  ],
  related_bugs: ['other-id-0000-0000-0000-000000000002'],
}

export const mockProducts = [
  { name: 'TestApp', description: null, archived: false, bug_count: 5 },
  { name: 'OtherApp', description: 'desc', archived: false, bug_count: 2 },
  { name: 'OldApp', description: null, archived: true, bug_count: 0 },
]

export const mockAreas = [
  { name: 'Frontend', description: null, archived: false, bug_count: 3 },
]

export const mockSeverities = [
  { name: 'Major', description: null, archived: false, bug_count: 4 },
  { name: 'Minor', description: null, archived: false, bug_count: 1 },
]

export const mockPlatforms = [
  { name: 'Web', description: null, archived: false, bug_count: 2 },
]

export const mockAgents = [
  {
    key: 'agent-key-abc',
    name: 'CI Bot',
    description: 'Automated agent',
    created_at: '2024-01-01T00:00:00Z',
    active: true,
  },
]
