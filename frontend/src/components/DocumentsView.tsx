import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react'
import {
  FileText,
  Loader2,
  Search,
  Trash2,
  Upload,
  RefreshCw,
  Download,
  MessageSquare,
  X,
  FileSpreadsheet,
  Presentation,
  File,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Button, Card } from './ui'
import {
  chatDocuments,
  deleteDocument,
  downloadDocument,
  formatBytes,
  getDocument,
  listDocuments,
  reprocessDocument,
  uploadDocument,
  type DocumentDetail,
  type DocumentItem,
} from '../lib/documentsApi'

const ACCEPT = '.pdf,.docx,.txt,.csv,.pptx'

function TypeIcon({ ext }: { ext: string }) {
  if (ext === 'pdf' || ext === 'txt' || ext === 'docx') return <FileText size={16} />
  if (ext === 'csv') return <FileSpreadsheet size={16} />
  if (ext === 'pptx') return <Presentation size={16} />
  return <File size={16} />
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ready: 'bg-positive-soft text-positive',
    processing: 'bg-info-soft text-info',
    pending: 'bg-warning-soft text-warning',
    failed: 'bg-negative-soft text-negative',
  }
  return (
    <span className={clsx('rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide', map[status] || 'bg-surface-3 text-muted')}>
      {status}
    </span>
  )
}

interface Props {
  /** Called when user selects documents to attach to research */
  onUseInResearch?: (ids: string[], names: string[]) => void
}

export function DocumentsView({ onUseInResearch }: Props) {
  const [items, setItems] = useState<DocumentItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploads, setUploads] = useState<Record<string, { name: string; pct: number; error?: string }>>({})
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [detail, setDetail] = useState<DocumentDetail | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatQ, setChatQ] = useState('')
  const [chatAnswer, setChatAnswer] = useState<string | null>(null)
  const [chatCitations, setChatCitations] = useState<Array<{ documentName?: string; location?: string; excerpt?: string }>>([])
  const [chatLoading, setChatLoading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const abortMap = useRef<Map<string, AbortController>>(new Map())

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listDocuments({
        q: query || undefined,
        status: statusFilter || undefined,
      })
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }, [query, statusFilter])

  useEffect(() => {
    void refresh()
  }, [refresh])

  async function handleFiles(files: FileList | File[]) {
    const list = Array.from(files)
    for (const file of list) {
      const key = `${file.name}-${file.size}-${Date.now()}`
      const controller = new AbortController()
      abortMap.current.set(key, controller)
      setUploads((u) => ({ ...u, [key]: { name: file.name, pct: 0 } }))
      try {
        await uploadDocument(file, {
          signal: controller.signal,
          onProgress: (pct) =>
            setUploads((u) => ({ ...u, [key]: { ...u[key], pct } })),
        })
        setUploads((u) => {
          const next = { ...u }
          delete next[key]
          return next
        })
      } catch (err) {
        const msg = (err as Error).message
        if (msg === 'aborted') {
          setUploads((u) => {
            const next = { ...u }
            delete next[key]
            return next
          })
        } else {
          setUploads((u) => ({ ...u, [key]: { ...u[key], pct: 0, error: msg } }))
        }
      } finally {
        abortMap.current.delete(key)
      }
    }
    void refresh()
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files?.length) void handleFiles(e.dataTransfer.files)
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function openDetail(id: string) {
    try {
      const d = await getDocument(id)
      setDetail(d)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function onDelete(id: string) {
    if (!confirm('Delete this document?')) return
    try {
      await deleteDocument(id)
      setSelected((s) => {
        const n = new Set(s)
        n.delete(id)
        return n
      })
      if (detail?.id === id) setDetail(null)
      void refresh()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function onChat() {
    if (!chatQ.trim()) return
    setChatLoading(true)
    setChatAnswer(null)
    try {
      const ids = selected.size ? Array.from(selected) : undefined
      const res = await chatDocuments(chatQ.trim(), ids)
      setChatAnswer(res.answer)
      setChatCitations(res.citations)
    } catch (err) {
      setChatAnswer((err as Error).message)
      setChatCitations([])
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-[1100px] px-4 py-8 lg:px-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink">Documents</h1>
          <p className="mt-1 text-sm text-muted">
            Upload PDFs, Word, PowerPoint, text and CSV files. Extracted content can feed research and document chat.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selected.size > 0 && onUseInResearch && (
            <Button
              size="sm"
              onClick={() => {
                const ids = Array.from(selected)
                const names = items.filter((i) => selected.has(i.id)).map((i) => i.originalFilename)
                onUseInResearch(ids, names)
              }}
            >
              Use {selected.size} in research
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={() => setChatOpen((v) => !v)}>
            <MessageSquare size={14} />
            Ask docs
          </Button>
          <Button size="sm" onClick={() => fileRef.current?.click()}>
            <Upload size={14} />
            Upload
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept={ACCEPT}
            multiple
            className="hidden"
            onChange={(e) => e.target.files && void handleFiles(e.target.files)}
          />
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={clsx(
          'mb-6 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors',
          dragOver ? 'border-accent bg-accent-soft' : 'border-line bg-surface',
        )}
      >
        <Upload className="mx-auto mb-3 h-8 w-8 text-faint" />
        <p className="text-sm text-ink">Drag & drop files here, or browse</p>
        <p className="mt-1 text-xs text-faint">PDF, DOCX, PPTX, TXT, CSV · max 25 MB each</p>
        <Button size="sm" className="mt-4" variant="ghost" onClick={() => fileRef.current?.click()}>
          Browse files
        </Button>
      </div>

      {/* In-flight uploads */}
      {Object.keys(uploads).length > 0 && (
        <div className="mb-4 space-y-2">
          {Object.entries(uploads).map(([key, u]) => (
            <div key={key} className="flex items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2">
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm text-ink">{u.name}</div>
                {u.error ? (
                  <div className="text-xs text-negative">{u.error}</div>
                ) : (
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-3">
                    <div className="h-full bg-accent transition-all" style={{ width: `${u.pct}%` }} />
                  </div>
                )}
              </div>
              {!u.error && (
                <button
                  type="button"
                  className="text-xs text-muted hover:text-ink"
                  onClick={() => abortMap.current.get(key)?.abort()}
                >
                  Cancel
                </button>
              )}
              {u.error && (
                <button
                  type="button"
                  className="text-xs text-muted hover:text-ink"
                  onClick={() =>
                    setUploads((prev) => {
                      const n = { ...prev }
                      delete n[key]
                      return n
                    })
                  }
                >
                  Dismiss
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[180px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search files…"
            className="w-full rounded-lg border border-line bg-surface py-2 pl-9 pr-3 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-line bg-surface px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="ready">Ready</option>
          <option value="processing">Processing</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
        </select>
        <Button size="sm" variant="ghost" onClick={() => void refresh()}>
          <RefreshCw size={14} />
        </Button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-negative/30 bg-negative-soft px-3 py-2 text-sm text-negative">
          {error}
        </div>
      )}

      {/* List */}
      <Card className="overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading documents…
          </div>
        ) : items.length === 0 ? (
          <div className="py-16 text-center text-sm text-muted">No documents yet. Upload your first file.</div>
        ) : (
          <ul className="divide-y divide-line">
            {items.map((doc) => (
              <li
                key={doc.id}
                className="flex flex-wrap items-center gap-3 px-4 py-3 hover:bg-surface-2/60"
              >
                <input
                  type="checkbox"
                  checked={selected.has(doc.id)}
                  onChange={() => toggleSelect(doc.id)}
                  className="h-4 w-4 rounded border-line"
                />
                <span className="text-muted">
                  <TypeIcon ext={doc.extension} />
                </span>
                <button
                  type="button"
                  className="min-w-0 flex-1 text-left"
                  onClick={() => void openDetail(doc.id)}
                >
                  <div className="truncate text-sm font-medium text-ink">{doc.originalFilename}</div>
                  <div className="mt-0.5 flex flex-wrap gap-x-3 text-[11px] text-faint">
                    <span>{formatBytes(doc.sizeBytes)}</span>
                    <span className="uppercase">{doc.extension}</span>
                    <span>{doc.createdAt ? new Date(doc.createdAt).toLocaleString() : ''}</span>
                    {doc.hasExtractedText && <span>Text extracted</span>}
                    {doc.hasIntelligence && <span>AI summary</span>}
                  </div>
                </button>
                <StatusBadge status={doc.status} />
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    title="Download"
                    className="rounded p-1.5 text-faint hover:bg-surface-3 hover:text-ink"
                    onClick={() => void downloadDocument(doc.id, doc.originalFilename)}
                  >
                    <Download size={14} />
                  </button>
                  <button
                    type="button"
                    title="Reprocess"
                    className="rounded p-1.5 text-faint hover:bg-surface-3 hover:text-ink"
                    onClick={() => void reprocessDocument(doc.id).then(refresh)}
                  >
                    <RefreshCw size={14} />
                  </button>
                  <button
                    type="button"
                    title="Delete"
                    className="rounded p-1.5 text-faint hover:bg-negative-soft hover:text-negative"
                    onClick={() => void onDelete(doc.id)}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {total > 0 && (
          <div className="border-t border-line px-4 py-2 text-[11px] text-faint">
            {total} document{total === 1 ? '' : 's'}
          </div>
        )}
      </Card>

      {/* Detail drawer */}
      {detail && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={() => setDetail(null)}>
          <div
            className="flex h-full w-full max-w-lg flex-col bg-surface shadow-pop"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <h2 className="truncate text-sm font-semibold text-ink">{detail.originalFilename}</h2>
              <button type="button" onClick={() => setDetail(null)} className="rounded p-1 text-faint hover:text-ink">
                <X size={16} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
              <div className="flex flex-wrap gap-2 text-xs text-muted">
                <StatusBadge status={detail.status} />
                <span>{formatBytes(detail.sizeBytes)}</span>
                {detail.pageCount != null && <span>{detail.pageCount} pages/slides</span>}
                {detail.wordCount != null && <span>{detail.wordCount} words</span>}
              </div>
              {detail.statusMessage && (
                <p className="text-xs text-warning">{String(detail.statusMessage)}</p>
              )}
              {detail.intelligence ? (
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">AI summary</h3>
                  <pre className="whitespace-pre-wrap rounded-lg bg-surface-2 p-3 text-xs text-ink">
                    {JSON.stringify(detail.intelligence, null, 2) as string}
                  </pre>
                </div>
              ) : null}
              {detail.extractedTextPreview && (
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">Extracted text</h3>
                  <pre className="max-h-80 overflow-y-auto whitespace-pre-wrap rounded-lg bg-surface-2 p-3 text-xs text-ink">
                    {detail.extractedTextPreview}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Document chat panel */}
      {chatOpen && (
        <div className="fixed bottom-4 right-4 z-40 w-full max-w-md rounded-2xl border border-line bg-surface shadow-pop">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <span className="text-sm font-medium text-ink">
              Ask your documents{selected.size ? ` (${selected.size} selected)` : ''}
            </span>
            <button type="button" onClick={() => setChatOpen(false)} className="text-faint hover:text-ink">
              <X size={16} />
            </button>
          </div>
          <div className="max-h-64 space-y-2 overflow-y-auto p-4 text-sm">
            {chatAnswer && (
              <>
                <p className="whitespace-pre-wrap text-ink">{chatAnswer}</p>
                {chatCitations.length > 0 && (
                  <div className="mt-2 space-y-1 border-t border-line pt-2">
                    <div className="text-[10px] font-semibold uppercase text-faint">Sources</div>
                    {chatCitations.map((c, i) => (
                      <div key={i} className="rounded bg-surface-2 px-2 py-1.5 text-[11px] text-muted">
                        <span className="font-medium text-ink">{c.documentName}</span>
                        {c.location && <span> · {c.location}</span>}
                        {c.excerpt && <div className="mt-0.5 line-clamp-2 text-faint">{c.excerpt}</div>}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
            {!chatAnswer && !chatLoading && (
              <p className="text-xs text-faint">Answers cite page/slide locations from your uploads.</p>
            )}
            {chatLoading && (
              <div className="flex items-center gap-2 text-muted">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Thinking…
              </div>
            )}
          </div>
          <div className="flex gap-2 border-t border-line p-3">
            <input
              value={chatQ}
              onChange={(e) => setChatQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void onChat()}
              placeholder="Ask a question…"
              className="flex-1 rounded-lg border border-line bg-surface-2 px-3 py-2 text-sm outline-none focus:border-accent"
            />
            <Button size="sm" onClick={() => void onChat()} disabled={chatLoading}>
              Ask
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
