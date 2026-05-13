import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { bugs as bugsApi } from '../api'
import type { BugFilters, Priority, Resolution, Status } from '../types'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PRIORITY_LABEL: Record<Priority, string> = { 1: 'P1', 2: 'P2', 3: 'P3' }
const PRIORITY_COLOR: Record<Priority, string> = {
  1: 'bg-red-100 text-red-700',
  2: 'bg-yellow-100 text-yellow-700',
  3: 'bg-green-100 text-green-700',
}
const STATUS_COLOR: Record<Status, string> = {
  open: 'bg-blue-100 text-blue-700',
  closed: 'bg-gray-100 text-gray-600',
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${color}`}>
      {label}
    </span>
  )
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

// ---------------------------------------------------------------------------
// URL ↔ filter state helpers
// ---------------------------------------------------------------------------

const PER_PAGE = 25

function paramsToFilters(p: URLSearchParams): BugFilters {
  const status = (p.get('status') ?? 'open') as Status | 'all'
  return {
    status,
    q: p.get('q') ?? undefined,
    product: p.getAll('product').length ? p.getAll('product') : undefined,
    area: p.getAll('area').length ? p.getAll('area') : undefined,
    platform: p.getAll('platform').length ? p.getAll('platform') : undefined,
    priority: p.getAll('priority').length
      ? (p.getAll('priority').map(Number) as Priority[])
      : undefined,
    severity: p.getAll('severity').length ? p.getAll('severity') : undefined,
    resolution: p.getAll('resolution').length
      ? (p.getAll('resolution') as Resolution[])
      : undefined,
    page: p.get('page') ? Number(p.get('page')) : 1,
    per_page: PER_PAGE,
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusToggle({
  value,
  onChange,
}: {
  value: Status | 'all'
  onChange: (v: Status | 'all') => void
}) {
  const opts: Array<{ label: string; value: Status | 'all' }> = [
    { label: 'Open', value: 'open' },
    { label: 'Closed', value: 'closed' },
    { label: 'All', value: 'all' },
  ]
  return (
    <div className="inline-flex rounded-lg border border-gray-200 overflow-hidden text-sm">
      {opts.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`px-3 py-1.5 font-medium transition-colors ${
            value === o.value
              ? 'bg-blue-600 text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

function MultiSelect({
  label,
  options,
  selected,
  onChange,
}: {
  label: string
  options: string[]
  selected: string[]
  onChange: (v: string[]) => void
}) {
  function toggle(val: string) {
    onChange(
      selected.includes(val) ? selected.filter((x) => x !== val) : [...selected, val],
    )
  }
  return (
    <details className="relative group">
      <summary className="cursor-pointer list-none flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 select-none">
        {label}
        {selected.length > 0 && (
          <span className="ml-1 rounded-full bg-blue-600 text-white text-xs w-4 h-4 flex items-center justify-center">
            {selected.length}
          </span>
        )}
        <svg className="ml-auto w-3 h-3 text-gray-400" viewBox="0 0 12 12" fill="currentColor">
          <path d="M6 8L1 3h10z" />
        </svg>
      </summary>
      <div className="absolute z-10 mt-1 w-48 rounded-lg border border-gray-200 bg-white shadow-lg py-1 max-h-56 overflow-y-auto">
        {options.length === 0 && (
          <p className="px-3 py-2 text-xs text-gray-400">No options</p>
        )}
        {options.map((opt) => (
          <label key={opt} className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 cursor-pointer text-sm">
            <input
              type="checkbox"
              checked={selected.includes(opt)}
              onChange={() => toggle(opt)}
              className="accent-blue-600"
            />
            {opt}
          </label>
        ))}
        {selected.length > 0 && (
          <button
            onClick={() => onChange([])}
            className="w-full text-left px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 border-t border-gray-100 mt-1"
          >
            Clear
          </button>
        )}
      </div>
    </details>
  )
}

function SearchInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Search bugs…"
      className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm w-56 focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
  )
}

function Pagination({
  page,
  total,
  perPage,
  onChange,
}: {
  page: number
  total: number
  perPage: number
  onChange: (p: number) => void
}) {
  const totalPages = Math.ceil(total / perPage)
  if (totalPages <= 1) return null
  return (
    <div className="flex items-center gap-2 text-sm text-gray-600">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="px-2 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
      >
        ‹
      </button>
      <span>
        Page {page} of {totalPages}
      </span>
      <button
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        className="px-2 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
      >
        ›
      </button>
      <span className="text-gray-400 text-xs">({total} total)</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function BugListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = paramsToFilters(searchParams)

  // Fetch lookup options for filter dropdowns
  const { data: productOpts = [] } = useQuery({
    queryKey: ['products'],
    queryFn: () =>
      import('../api').then((m) => m.products.list()).then((ps) => ps.map((p) => p.name)),
  })
  const { data: areaOpts = [] } = useQuery({
    queryKey: ['areas'],
    queryFn: () =>
      import('../api').then((m) => m.areas.list()).then((as) => as.map((a) => a.name)),
  })
  const { data: platformOpts = [] } = useQuery({
    queryKey: ['platforms'],
    queryFn: () =>
      import('../api').then((m) => m.platforms.list()).then((ps) => ps.map((p) => p.name)),
  })
  const { data: severityOpts = [] } = useQuery({
    queryKey: ['severities'],
    queryFn: () =>
      import('../api').then((m) => m.severities.list()).then((ss) => ss.map((s) => s.name)),
  })

  const { data, isLoading, isError } = useQuery({
    queryKey: ['bugs', filters],
    queryFn: () => bugsApi.list(filters),
  })

  function setFilter(patch: Partial<BugFilters>) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      // Reset page on filter change
      if (!('page' in patch)) next.set('page', '1')

      for (const [k, v] of Object.entries(patch)) {
        if (v === undefined || v === null) {
          next.delete(k)
        } else if (Array.isArray(v)) {
          next.delete(k)
          v.forEach((item) => next.append(k, String(item)))
        } else {
          next.set(k, String(v))
        }
      }
      return next
    })
  }

  const status = filters.status ?? 'open'
  const page = filters.page ?? 1

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-6 space-y-4">

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <StatusToggle
            value={status}
            onChange={(v) => setFilter({ status: v })}
          />
          <SearchInput
            value={filters.q ?? ''}
            onChange={(q) => setFilter({ q: q || undefined })}
          />
          <MultiSelect
            label="Product"
            options={productOpts}
            selected={filters.product ?? []}
            onChange={(v) => setFilter({ product: v.length ? v : undefined })}
          />
          <MultiSelect
            label="Area"
            options={areaOpts}
            selected={filters.area ?? []}
            onChange={(v) => setFilter({ area: v.length ? v : undefined })}
          />
          <MultiSelect
            label="Platform"
            options={platformOpts}
            selected={filters.platform ?? []}
            onChange={(v) => setFilter({ platform: v.length ? v : undefined })}
          />
          <MultiSelect
            label="Severity"
            options={severityOpts}
            selected={filters.severity ?? []}
            onChange={(v) => setFilter({ severity: v.length ? v : undefined })}
          />
          <MultiSelect
            label="Priority"
            options={['1', '2', '3']}
            selected={(filters.priority ?? []).map(String)}
            onChange={(v) =>
              setFilter({ priority: v.length ? (v.map(Number) as Priority[]) : undefined })
            }
          />
          <Link
            to="/bugs/new"
            className="ml-auto px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            + New bug
          </Link>
        </div>

        {/* Table */}
        {isError && (
          <p className="text-red-600 text-sm">Failed to load bugs.</p>
        )}
        {isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-10 rounded-lg bg-gray-200 animate-pulse" />
            ))}
          </div>
        )}
        {data && (
          <>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {data.bugs.length === 0 ? (
                <p className="text-center text-gray-400 text-sm py-12">No bugs found.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200 text-xs text-gray-500 uppercase tracking-wide">
                    <tr>
                      <th className="px-4 py-2 text-left">ID</th>
                      <th className="px-4 py-2 text-left">Title</th>
                      <th className="px-4 py-2 text-left">Product</th>
                      <th className="px-4 py-2 text-left">Priority</th>
                      <th className="px-4 py-2 text-left">Status</th>
                      <th className="px-4 py-2 text-left">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.bugs.map((bug) => (
                      <tr key={bug.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs text-gray-400">{bug.id.slice(0, 8)}</td>
                        <td className="px-4 py-3">
                          <Link
                            to={`/bugs/${bug.id}`}
                            className="text-gray-900 hover:text-blue-600 font-medium"
                          >
                            {bug.title}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-gray-600">{bug.product}</td>
                        <td className="px-4 py-3">
                          {bug.priority && (
                            <Badge
                              label={PRIORITY_LABEL[bug.priority]}
                              color={PRIORITY_COLOR[bug.priority]}
                            />
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <Badge label={bug.status} color={STATUS_COLOR[bug.status]} />
                        </td>
                        <td className="px-4 py-3 text-gray-400">{formatDate(bug.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <Pagination
              page={page}
              total={data.total}
              perPage={PER_PAGE}
              onChange={(p) => setFilter({ page: p })}
            />
          </>
        )}
      </div>
    </div>
  )
}
