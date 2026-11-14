import { useMemo, useState } from 'react'
import { ArrowLeft, Building2, GitCompare, Trash2, User, X } from 'lucide-react'
import { Badge, Button, Card, EmptyState } from './ui'
import { fmtDate, relativeTime } from '../lib/format'
import type { BriefingRequest, HistoryEntry } from '../types'
import type { WatchItem } from '../lib/store'

export function HistoryView({
  entries,
  onOpen,
  onRemove,
  onClear,
  onBack,
}: {
  entries: HistoryEntry[]
  onOpen: (e: HistoryEntry) => void
  onRemove: (id: string) => void
  onClear: () => void
  onBack: () => void
}) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return entries
    return entries.filter(
      (e) =>
        e.subject.toLowerCase().includes(q) ||
        e.headline.toLowerCase().includes(q) ||
        e.result.news.some((n) => n.headline.toLowerCase().includes(q)),
    )
  }, [entries, query])

  return (
    <div className="mx-auto max-w-[1000px] px-4 py-6 lg:px-6">
      <div className="mb-4 flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft size={14} />
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="text-[16px] font-semibold tracking-tight text-ink">Briefing history</h1>
          <div className="text-[11.5px] text-faint">
            {entries.length} saved briefing{entries.length === 1 ? '' : 's'} · stored locally on this
            device
          </div>
        </div>
        {entries.length > 0 && (
          <Button variant="ghost" size="sm" onClick={onClear}>
            <Trash2 size={12} />
            Clear
          </Button>
        )}
      </div>

      {entries.length > 0 && (
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search subjects and headlines…"
          className="mb-4 h-9 w-full rounded-lg border border-line bg-surface px-3 text-[12.5px] text-ink outline-none placeholder:text-faint focus:border-accent/50"
        />
      )}

      {filtered.length === 0 ? (
        <Card>
          <EmptyState
            title={entries.length === 0 ? 'No briefings yet' : 'Nothing matches'}
            body={
              entries.length === 0
                ? 'Run a research from the home screen and it will be archived here automatically.'
                : 'Try a different subject or headline fragment.'
            }
          />
        </Card>
      ) : (
        <div className="space-y-2.5">
          {filtered.map((e) => (
            <Card key={e.id} className="group p-4">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent-text ring-1 ring-accent/20">
                  {e.type === 'company' ? <Building2 size={15} /> : <User size={15} />}
                </div>
                <button
                  type="button"
                  onClick={() => onOpen(e)}
                  className="min-w-0 flex-1 text-left"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="truncate text-[14px] font-semibold tracking-tight text-ink">
                      {e.subject}
                    </span>
                    <Badge tone="neutral">{e.type}</Badge>
                  </div>
                  <div className="mt-1 line-clamp-2 text-[12px] leading-relaxed text-muted">
                    {e.headline}
                  </div>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10.5px] text-faint">
                    <span>{e.stats.articles} items</span>
                    <span>·</span>
                    <span>{e.stats.sources} outlets</span>
                    <span>·</span>
                    <span>{e.stats.keyItems} key</span>
                    <span>·</span>
                    <span title={fmtDate(e.generatedAt)}>{relativeTime(e.generatedAt)}</span>
                  </div>
                </button>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label="Delete briefing"
                  onClick={() => onRemove(e.id)}
                  className="opacity-0 transition-opacity group-hover:opacity-100"
                >
                  <Trash2 size={12} />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export function WatchlistView({
  items,
  onResearch,
  onRemove,
  onBack,
  onCompare,
}: {
  items: WatchItem[]
  onResearch: (subject: string, type: BriefingRequest['type'], days: number) => void
  onRemove: (subject: string) => void
  onBack: () => void
  onCompare: () => void
}) {
  return (
    <div className="mx-auto max-w-[1000px] px-4 py-6 lg:px-6">
      <div className="mb-4 flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft size={14} />
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="text-[16px] font-semibold tracking-tight text-ink">Watchlist</h1>
          <div className="text-[11.5px] text-faint">
            Subjects you are tracking across meetings
          </div>
        </div>
        {items.length >= 2 && (
          <Button variant="outline" size="sm" onClick={onCompare}>
            <GitCompare size={13} />
            Compare
          </Button>
        )}
      </div>

      {items.length === 0 ? (
        <Card>
          <EmptyState
            title="Nothing on the watchlist"
            body="Use the bell button on any briefing to track a subject. Watched subjects appear on the home screen for one-click refresh."
          />
        </Card>
      ) : (
        <div className="grid gap-2.5 sm:grid-cols-2">
          {items.map((w) => (
            <Card key={w.subject} className="group p-4">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-3 text-muted">
                  {w.type === 'company' ? <Building2 size={15} /> : <User size={15} />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13.5px] font-semibold tracking-tight text-ink">
                    {w.subject}
                  </div>
                  <div className="text-[11px] text-faint">
                    Added {fmtDate(w.addedAt)}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label="Remove from watchlist"
                  onClick={() => onRemove(w.subject)}
                  className="opacity-0 transition-opacity group-hover:opacity-100"
                >
                  <X size={12} />
                </Button>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="mt-3 w-full"
                onClick={() => onResearch(w.subject, w.type, 30)}
              >
                Refresh briefing
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
