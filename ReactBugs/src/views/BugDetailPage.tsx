import { useState, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { bugs as bugsApi, annotations as annotationsApi, artifacts as artifactsApi, relations, getToken } from '../api'
import type { Resolution } from '../types'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-900">{children ?? <span className="text-gray-300">—</span>}</dd>
    </div>
  )
}

const PRIORITY_LABEL = { 1: 'P1 — Critical', 2: 'P2 — Major', 3: 'P3 — Minor' } as const
const RESOLUTION_LABEL: Record<Resolution, string> = {
  none: 'None', fixed: 'Fixed', no_repro: 'Cannot Reproduce',
  duplicate: 'Duplicate', wont_fix: "Won't Fix",
}

// ---------------------------------------------------------------------------
// Annotations section
// ---------------------------------------------------------------------------

function AnnotationsSection({ bugId }: { bugId: string }) {
  const qc = useQueryClient()
  const [body, setBody] = useState('')
  const { data: bug } = useQuery({ queryKey: ['bug', bugId], queryFn: () => bugsApi.get(bugId) })

  const add = useMutation({
    mutationFn: (text: string) => annotationsApi.create(bugId, text),
    onMutate: async (text) => {
      await qc.cancelQueries({ queryKey: ['bug', bugId] })
      const prev = qc.getQueryData(['bug', bugId])
      qc.setQueryData(['bug', bugId], (old: typeof bug) => old ? {
        ...old,
        annotations: [...old.annotations, {
          id: Date.now(), bug_id: bugId, author: 'you',
          author_type: 'human' as const, body: text, created_at: new Date().toISOString(),
        }],
      } : old)
      return { prev }
    },
    onError: (_e, _v, ctx) => { if (ctx?.prev) qc.setQueryData(['bug', bugId], ctx.prev) },
    onSettled: () => qc.invalidateQueries({ queryKey: ['bug', bugId] }),
    onSuccess: () => setBody(''),
  })

  return (
    <section className="space-y-4">
      <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Annotations</h2>
      <div className="space-y-3">
        {bug?.annotations.length === 0 && (
          <p className="text-sm text-gray-400">No annotations yet.</p>
        )}
        {bug?.annotations.map((a) => (
          <div key={a.id} className="bg-gray-50 rounded-lg px-4 py-3 space-y-1">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span className="font-medium text-gray-600">{a.author}</span>
              <span>·</span>
              <span>{a.author_type}</span>
              <span>·</span>
              <span>{formatDate(a.created_at)}</span>
            </div>
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{a.body}</p>
          </div>
        ))}
      </div>
      <div className="space-y-2">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={3}
          placeholder="Add an annotation…"
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
        <button
          onClick={() => { if (body.trim()) add.mutate(body.trim()) }}
          disabled={!body.trim() || add.isPending}
          className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {add.isPending ? 'Posting…' : 'Post'}
        </button>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Artifacts section
// ---------------------------------------------------------------------------

function ArtifactsSection({ bugId }: { bugId: string }) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const { data: bug } = useQuery({ queryKey: ['bug', bugId], queryFn: () => bugsApi.get(bugId) })
  const token = getToken()

  const upload = useMutation({
    mutationFn: (file: File) => artifactsApi.upload(bugId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bug', bugId] }),
  })

  function handleFiles(files: FileList | null) {
    if (!files) return
    Array.from(files).forEach((f) => upload.mutate(f))
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Attachments</h2>
      {bug?.artifacts.length === 0 && (
        <p className="text-sm text-gray-400">No attachments.</p>
      )}
      <ul className="space-y-1">
        {bug?.artifacts.map((a) => (
          <li key={a.id} className="flex items-center gap-2 text-sm">
            <a
              href={a.url}
              download={a.filename}
              onClick={(e) => {
                // Fetch with auth header so the backend validates the token
                e.preventDefault()
                fetch(a.url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
                  .then((r) => r.blob())
                  .then((blob) => {
                    const url = URL.createObjectURL(blob)
                    const link = document.createElement('a')
                    link.href = url
                    link.download = a.filename
                    link.click()
                    URL.revokeObjectURL(url)
                  })
              }}
              className="text-blue-600 hover:underline"
            >
              {a.filename}
            </a>
            {a.mime_type && <span className="text-xs text-gray-400">{a.mime_type}</span>}
            <span className="text-xs text-gray-300">{formatDate(a.uploaded_at)}</span>
          </li>
        ))}
      </ul>
      <div className="flex items-center gap-2">
        <input
          ref={fileRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={upload.isPending}
          className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          {upload.isPending ? 'Uploading…' : 'Attach file'}
        </button>
        {upload.isError && <span className="text-xs text-red-500">Upload failed.</span>}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Related bugs section
// ---------------------------------------------------------------------------

function RelatedBugsSection({ bugId }: { bugId: string }) {
  const qc = useQueryClient()
  const [input, setInput] = useState('')
  const [addError, setAddError] = useState('')
  const { data: bug } = useQuery({ queryKey: ['bug', bugId], queryFn: () => bugsApi.get(bugId) })

  const add = useMutation({
    mutationFn: (relatedId: string) => relations.add(bugId, relatedId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['bug', bugId] }); setInput(''); setAddError('') },
    onError: () => setAddError('Could not add relation.'),
  })

  const remove = useMutation({
    mutationFn: (relatedId: string) => relations.remove(bugId, relatedId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bug', bugId] }),
  })

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Related bugs</h2>
      {bug?.related_bugs.length === 0 && (
        <p className="text-sm text-gray-400">No related bugs.</p>
      )}
      <ul className="space-y-1">
        {bug?.related_bugs.map((id) => (
          <li key={id} className="flex items-center gap-2 text-sm">
            <Link to={`/bugs/${id}`} className="text-blue-600 hover:underline font-mono text-xs">
              {id.slice(0, 8)}
            </Link>
            <button
              onClick={() => remove.mutate(id)}
              className="text-xs text-gray-400 hover:text-red-500"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      <div className="flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && input.trim()) add.mutate(input.trim()) }}
          placeholder="Bug ID…"
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
        />
        <button
          onClick={() => { if (input.trim()) add.mutate(input.trim()) }}
          disabled={!input.trim() || add.isPending}
          className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          Add
        </button>
        {addError && <span className="text-xs text-red-500">{addError}</span>}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Close dialog
// ---------------------------------------------------------------------------

const RESOLUTIONS: Resolution[] = ['fixed', 'no_repro', 'duplicate', 'wont_fix']

function CloseDialog({ bugId, onClose }: { bugId: string; onClose: () => void }) {
  const qc = useQueryClient()
  const [resolution, setResolution] = useState<Resolution>('fixed')
  const [note, setNote] = useState('')

  const close = useMutation({
    mutationFn: () => bugsApi.close(bugId, resolution, note.trim() || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bug', bugId] })
      qc.invalidateQueries({ queryKey: ['bugs'] })
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Close bug</h2>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Resolution</label>
          <select
            value={resolution}
            onChange={(e) => setResolution(e.target.value as Resolution)}
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {RESOLUTIONS.map((r) => (
              <option key={r} value={r}>{RESOLUTION_LABEL[r]}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Note (optional)</label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            placeholder="Add a closing note…"
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>
        {close.isError && (
          <p className="text-sm text-red-600">Failed to close bug.</p>
        )}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => close.mutate()}
            disabled={close.isPending}
            className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {close.isPending ? 'Closing…' : 'Close bug'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function BugDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showClose, setShowClose] = useState(false)

  const { data: bug, isLoading, isError } = useQuery({
    queryKey: ['bug', id],
    queryFn: () => bugsApi.get(id!),
    enabled: !!id,
  })

  const reopen = useMutation({
    mutationFn: () => bugsApi.reopen(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bug', id] })
      qc.invalidateQueries({ queryKey: ['bugs'] })
    },
  })

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-8 rounded-lg bg-gray-200 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError || !bug) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <p className="text-red-600 text-sm">Bug not found or failed to load.</p>
        <button onClick={() => navigate(-1)} className="mt-2 text-sm text-blue-600 hover:underline">
          Go back
        </button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">

        {/* Header */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <Link to="/bugs" className="text-xs text-blue-600 hover:underline">← Bugs</Link>
              <h1 className="text-xl font-bold text-gray-900">{bug.title}</h1>
              <p className="text-xs font-mono text-gray-400">{bug.id}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Link
                to={`/bugs/${bug.id}/edit`}
                className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Edit
              </Link>
              {bug.status === 'open' ? (
                <button
                  onClick={() => setShowClose(true)}
                  className="px-3 py-1.5 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors"
                >
                  Close
                </button>
              ) : (
                <button
                  onClick={() => reopen.mutate()}
                  disabled={reopen.isPending}
                  className="px-3 py-1.5 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  {reopen.isPending ? 'Reopening…' : 'Reopen'}
                </button>
              )}
            </div>
          </div>

          {/* Metadata grid */}
          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-2 border-t border-gray-100">
            <Field label="Status">{bug.status}</Field>
            <Field label="Resolution">{RESOLUTION_LABEL[bug.resolution]}</Field>
            <Field label="Product">{bug.product}</Field>
            <Field label="Area">{bug.area}</Field>
            <Field label="Platform">{bug.platform}</Field>
            <Field label="Priority">{bug.priority ? PRIORITY_LABEL[bug.priority] : null}</Field>
            <Field label="Severity">{bug.severity}</Field>
            <Field label="Created">{formatDate(bug.created_at)}</Field>
            <Field label="Updated">{formatDate(bug.updated_at)}</Field>
          </dl>

          {/* Description */}
          {bug.description && (
            <div className="pt-2 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Description</p>
              <p className="text-sm text-gray-800 whitespace-pre-wrap">{bug.description}</p>
            </div>
          )}
        </div>

        {/* Sections */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <AnnotationsSection bugId={bug.id} />
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <ArtifactsSection bugId={bug.id} />
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <RelatedBugsSection bugId={bug.id} />
          </div>
        </div>
      </div>

      {showClose && <CloseDialog bugId={bug.id} onClose={() => setShowClose(false)} />}
    </div>
  )
}
