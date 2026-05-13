import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { bugs as bugsApi, products, areas, platforms, severities } from '../api'
import type { Priority } from '../types'

interface FormState {
  title: string
  description: string
  product: string
  area: string
  platform: string
  priority: string
  severity: string
}

const EMPTY: FormState = {
  title: '', description: '', product: '', area: '',
  platform: '', priority: '', severity: '',
}

function FormField({ label, required, children }: {
  label: string; required?: boolean; children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  )
}

function Select({
  value, onChange, options, placeholder,
}: {
  value: string; onChange: (v: string) => void
  options: string[]; placeholder: string
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
    >
      <option value="">{placeholder}</option>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  )
}

export default function BugFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isEdit = !!id

  const [form, setForm] = useState<FormState>(EMPTY)
  const [error, setError] = useState('')

  // Lookup options
  const { data: productOpts = [] } = useQuery({
    queryKey: ['products'],
    queryFn: () => products.list().then((ps) => ps.filter((p) => !p.archived).map((p) => p.name)),
  })
  const { data: areaOpts = [] } = useQuery({
    queryKey: ['areas'],
    queryFn: () => areas.list().then((as) => as.filter((a) => !a.archived).map((a) => a.name)),
  })
  const { data: platformOpts = [] } = useQuery({
    queryKey: ['platforms'],
    queryFn: () => platforms.list().then((ps) => ps.filter((p) => !p.archived).map((p) => p.name)),
  })
  const { data: severityOpts = [] } = useQuery({
    queryKey: ['severities'],
    queryFn: () => severities.list().then((ss) => ss.filter((s) => !s.archived).map((s) => s.name)),
  })

  // Pre-populate in edit mode
  const { data: existingBug } = useQuery({
    queryKey: ['bug', id],
    queryFn: () => bugsApi.get(id!),
    enabled: isEdit,
  })

  useEffect(() => {
    if (existingBug) {
      setForm({
        title: existingBug.title,
        description: existingBug.description ?? '',
        product: existingBug.product,
        area: existingBug.area ?? '',
        platform: existingBug.platform ?? '',
        priority: existingBug.priority ? String(existingBug.priority) : '',
        severity: existingBug.severity ?? '',
      })
    }
  }, [existingBug])

  function set(key: keyof FormState) {
    return (v: string) => setForm((f) => ({ ...f, [key]: v }))
  }

  const create = useMutation({
    mutationFn: () =>
      bugsApi.create({
        title: form.title.trim(),
        product: form.product,
        description: form.description.trim() || undefined,
        area: form.area || undefined,
        platform: form.platform || undefined,
        priority: form.priority ? (Number(form.priority) as Priority) : undefined,
        severity: form.severity || undefined,
      }),
    onSuccess: (bug) => {
      qc.invalidateQueries({ queryKey: ['bugs'] })
      navigate(`/bugs/${bug.id}`)
    },
    onError: () => setError('Failed to create bug.'),
  })

  const update = useMutation({
    mutationFn: () =>
      bugsApi.update(id!, {
        title: form.title.trim(),
        product: form.product,
        description: form.description.trim() || undefined,
        area: form.area || undefined,
        platform: form.platform || undefined,
        priority: form.priority ? (Number(form.priority) as Priority) : undefined,
        severity: form.severity || undefined,
      }),
    onSuccess: (bug) => {
      qc.invalidateQueries({ queryKey: ['bug', id] })
      qc.invalidateQueries({ queryKey: ['bugs'] })
      navigate(`/bugs/${bug.id}`)
    },
    onError: () => setError('Failed to update bug.'),
  })

  function handleSubmit() {
    setError('')
    if (!form.title.trim()) { setError('Title is required.'); return }
    if (!form.product) { setError('Product is required.'); return }
    if (isEdit) update.mutate(); else create.mutate()
  }

  const isPending = create.isPending || update.isPending

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
          <h1 className="text-xl font-bold text-gray-900">
            {isEdit ? 'Edit bug' : 'New bug'}
          </h1>

          <FormField label="Title" required>
            <input
              type="text"
              value={form.title}
              onChange={(e) => set('title')(e.target.value)}
              placeholder="Short, descriptive title"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </FormField>

          <FormField label="Product" required>
            <Select value={form.product} onChange={set('product')} options={productOpts} placeholder="Select product…" />
          </FormField>

          <div className="grid sm:grid-cols-2 gap-4">
            <FormField label="Area">
              <Select value={form.area} onChange={set('area')} options={areaOpts} placeholder="Select area…" />
            </FormField>
            <FormField label="Platform">
              <Select value={form.platform} onChange={set('platform')} options={platformOpts} placeholder="Select platform…" />
            </FormField>
            <FormField label="Priority">
              <Select value={form.priority} onChange={set('priority')} options={['1', '2', '3']} placeholder="Select priority…" />
            </FormField>
            <FormField label="Severity">
              <Select value={form.severity} onChange={set('severity')} options={severityOpts} placeholder="Select severity…" />
            </FormField>
          </div>

          <FormField label="Description">
            <textarea
              value={form.description}
              onChange={(e) => set('description')(e.target.value)}
              rows={6}
              placeholder="Steps to reproduce, expected vs actual behaviour…"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
            />
          </FormField>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
            <button
              onClick={() => navigate(-1)}
              className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isPending}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Create bug'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
