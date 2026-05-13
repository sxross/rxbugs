import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { products, areas, severities, platforms, agentsApi } from '../api'
import type { Area, Platform, Product, Severity, Agent } from '../types'

// ---------------------------------------------------------------------------
// Generic lookup table (Products / Areas / Severities / Platforms)
// ---------------------------------------------------------------------------

type LookupItem = Product | Area | Severity | Platform

interface LookupTableProps {
  queryKey: string
  label: string
  items: LookupItem[] | undefined
  isLoading: boolean
  onCreate: (name: string, description: string) => Promise<unknown>
  onToggleArchive: (item: LookupItem) => Promise<unknown>
}

function LookupTable({ queryKey, label, items, isLoading, onCreate, onToggleArchive }: LookupTableProps) {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [createError, setCreateError] = useState('')
  const [showArchived, setShowArchived] = useState(false)

  const create = useMutation({
    mutationFn: () => onCreate(name.trim(), desc.trim()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [queryKey] })
      setName('')
      setDesc('')
      setCreateError('')
    },
    onError: () => setCreateError('Failed to create.'),
  })

  const toggle = useMutation({
    mutationFn: (item: LookupItem) => onToggleArchive(item),
    onSuccess: () => qc.invalidateQueries({ queryKey: [queryKey] }),
  })

  const visible = items?.filter((i) => showArchived || !i.archived) ?? []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">{label}</h2>
        <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="accent-blue-600"
          />
          Show archived
        </label>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-8 rounded bg-gray-100 animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && visible.length === 0 && (
        <p className="text-sm text-gray-400">No {label.toLowerCase()} yet.</p>
      )}

      <ul className="divide-y divide-gray-100">
        {visible.map((item) => (
          <li key={item.name} className="flex items-center justify-between py-2 text-sm">
            <div>
              <span className={item.archived ? 'text-gray-400 line-through' : 'text-gray-800'}>
                {item.name}
              </span>
              {item.description && (
                <span className="ml-2 text-xs text-gray-400">{item.description}</span>
              )}
              <span className="ml-2 text-xs text-gray-300">({item.bug_count})</span>
            </div>
            <button
              onClick={() => toggle.mutate(item)}
              disabled={toggle.isPending}
              className="text-xs text-gray-400 hover:text-blue-600 disabled:opacity-40"
            >
              {item.archived ? 'Unarchive' : 'Archive'}
            </button>
          </li>
        ))}
      </ul>

      {/* Create form */}
      <div className="pt-3 border-t border-gray-100 space-y-2">
        <div className="flex gap-2">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && name.trim()) create.mutate() }}
            placeholder={`New ${label.toLowerCase().slice(0, -1)} name…`}
            className="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            placeholder="Description (optional)"
            className="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => { if (name.trim()) create.mutate() }}
            disabled={!name.trim() || create.isPending}
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            Add
          </button>
        </div>
        {createError && <p className="text-xs text-red-500">{createError}</p>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Agents table
// ---------------------------------------------------------------------------

function AgentsTable() {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [rateLimit, setRateLimit] = useState('')
  const [createError, setCreateError] = useState('')

  const { data: agentList, isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentsApi.list(),
  })

  const register = useMutation({
    mutationFn: () =>
      agentsApi.register(name.trim(), desc.trim() || undefined, rateLimit ? Number(rateLimit) : undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agents'] })
      setName('')
      setDesc('')
      setRateLimit('')
      setCreateError('')
    },
    onError: () => setCreateError('Failed to register agent.'),
  })

  const revoke = useMutation({
    mutationFn: (key: string) => agentsApi.revoke(key),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  })

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-gray-900">Agents</h2>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-8 rounded bg-gray-100 animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && agentList?.length === 0 && (
        <p className="text-sm text-gray-400">No agents registered.</p>
      )}

      <ul className="divide-y divide-gray-100">
        {agentList?.map((agent: Agent) => (
          <li key={agent.key} className="flex items-start justify-between py-2 text-sm gap-4">
            <div className="space-y-0.5 min-w-0">
              <div className="flex items-center gap-2">
                <span className={agent.active ? 'text-gray-800 font-medium' : 'text-gray-400'}>
                  {agent.name}
                </span>
                {!agent.active && (
                  <span className="text-xs bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded">inactive</span>
                )}
              </div>
              {agent.description && (
                <p className="text-xs text-gray-400">{agent.description}</p>
              )}
              <p className="text-xs font-mono text-gray-300 truncate">{agent.key}</p>
              <p className="text-xs text-gray-300">Registered {formatDate(agent.created_at)}</p>
            </div>
            <button
              onClick={() => revoke.mutate(agent.key)}
              disabled={revoke.isPending}
              className="text-xs text-red-400 hover:text-red-600 disabled:opacity-40 shrink-0"
            >
              Revoke
            </button>
          </li>
        ))}
      </ul>

      <div className="pt-3 border-t border-gray-100 space-y-2">
        <div className="flex gap-2 flex-wrap">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Agent name…"
            className="flex-1 min-w-32 rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            placeholder="Description (optional)"
            className="flex-1 min-w-32 rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="number"
            value={rateLimit}
            onChange={(e) => setRateLimit(e.target.value)}
            placeholder="Rate limit/min"
            className="w-32 rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => { if (name.trim()) register.mutate() }}
            disabled={!name.trim() || register.isPending}
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            Register
          </button>
        </div>
        {createError && <p className="text-xs text-red-500">{createError}</p>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Admin page shell with tab nav
// ---------------------------------------------------------------------------

type Tab = 'products' | 'areas' | 'severities' | 'platforms' | 'agents'
const TABS: { id: Tab; label: string }[] = [
  { id: 'products', label: 'Products' },
  { id: 'areas', label: 'Areas' },
  { id: 'severities', label: 'Severities' },
  { id: 'platforms', label: 'Platforms' },
  { id: 'agents', label: 'Agents' },
]

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>('products')

  const { data: productList, isLoading: plLoading } = useQuery({
    queryKey: ['products', 'all'],
    queryFn: () => products.list(true),
    enabled: tab === 'products',
  })
  const { data: areaList, isLoading: alLoading } = useQuery({
    queryKey: ['areas', 'all'],
    queryFn: () => areas.list(true),
    enabled: tab === 'areas',
  })
  const { data: severityList, isLoading: slLoading } = useQuery({
    queryKey: ['severities', 'all'],
    queryFn: () => severities.list(true),
    enabled: tab === 'severities',
  })
  const { data: platformList, isLoading: pllLoading } = useQuery({
    queryKey: ['platforms', 'all'],
    queryFn: () => platforms.list(true),
    enabled: tab === 'platforms',
  })

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        <h1 className="text-xl font-bold text-gray-900">Admin</h1>

        {/* Tab bar */}
        <div className="flex gap-1 border-b border-gray-200">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === t.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          {tab === 'products' && (
            <LookupTable
              queryKey="products"
              label="Products"
              items={productList}
              isLoading={plLoading}
              onCreate={(n, d) => products.create(n, d || undefined)}
              onToggleArchive={(item) =>
                products.update(item.name, { archived: !item.archived })
              }
            />
          )}
          {tab === 'areas' && (
            <LookupTable
              queryKey="areas"
              label="Areas"
              items={areaList}
              isLoading={alLoading}
              onCreate={(n, d) => areas.create(n, d || undefined)}
              onToggleArchive={(item) =>
                areas.update(item.name, { archived: !item.archived })
              }
            />
          )}
          {tab === 'severities' && (
            <LookupTable
              queryKey="severities"
              label="Severities"
              items={severityList}
              isLoading={slLoading}
              onCreate={(n, d) => severities.create(n, d || undefined)}
              onToggleArchive={(item) =>
                severities.update(item.name, { archived: !item.archived })
              }
            />
          )}
          {tab === 'platforms' && (
            <LookupTable
              queryKey="platforms"
              label="Platforms"
              items={platformList}
              isLoading={pllLoading}
              onCreate={(n, d) => platforms.create(n, d || undefined)}
              onToggleArchive={(item) =>
                platforms.update(item.name, { archived: !item.archived })
              }
            />
          )}
          {tab === 'agents' && <AgentsTable />}
        </div>
      </div>
    </div>
  )
}
