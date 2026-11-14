import { useMemo, useState } from 'react'
import { Filter, Inbox, Search, X } from 'lucide-react'
import { clsx } from 'clsx'
import { Badge, Button, EmptyState, Segmented } from './ui'
import { NewsCard } from './NewsCard'
import { CATEGORY_LABEL, CATEGORY_ORDER } from '../lib/templates'
import { relativeLabel } from '../lib/format'
import type { NewsCategory, NewsItem, Sentiment } from '../types'

type Sort = 'newest' | 'oldest' | 'impact'

export function NewsTimeline({
  news,
  windowDays,
  highlighted,
  onClearHighlight,
}: {
  news: NewsItem[]
  windowDays: number
  highlighted?: string | null
  onClearHighlight?: () => void
}) {
  const [query, setQuery] = useState('')
  const [cats, setCats] = useState<NewsCategory[]>([])
  const [sentiment, setSentiment] = useState<Sentiment | 'all'>('all')
  const [impact, setImpact] = useState<number | 'all'>('all')
  const [sort, setSort] = useState<Sort>('newest')
  const [showOutOfWindow, setShowOutOfWindow] = useState(false)

  const inWindow = news.filter((n) => n.inWindow)
  const outWindow = news.filter((n) => !n.inWindow)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    const filteredItems = inWindow.filter((n) => {
      if (cats.length && !cats.includes(n.category)) return false
      if (sentiment !== 'all' && n.sentiment !== sentiment) return false
      if (impact !== 'all' && n.impact < impact) return false
      if (q) {
        const hay = `${n.headline} ${n.summary} ${n.whyItMatters} ${n.entities.join(' ')} ${n.source}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
    const sorted = [...filteredItems]
    if (sort === 'newest') sorted.sort((a, b) => +new Date(b.publishedAt) - +new Date(a.publishedAt))
    if (sort === 'oldest') sorted.sort((a, b) => +new Date(a.publishedAt) - +new Date(b.publishedAt))
    if (sort === 'impact')
      sorted.sort((a, b) => b.impact - a.impact || +new Date(b.publishedAt) - +new Date(a.publishedAt))
    return sorted
  }, [inWindow, query, cats, sentiment, impact, sort])

  const grouped = useMemo(() => {
    const map = new Map<string, NewsItem[]>()
    filtered.forEach((n) => {
      const key = n.publishedAt.slice(0, 10)
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(n)
    })
    return [...map.entries()].sort((a, b) => b[0].localeCompare(a[0]))
  }, [filtered])

  const availableCats = useMemo(() => {
    const counts = new Map<NewsCategory, number>()
    inWindow.forEach((n) => counts.set(n.category, (counts.get(n.category) ?? 0) + 1))
    return CATEGORY_ORDER.filter((c) => counts.has(c)).map((c) => ({
      category: c,
      count: counts.get(c)!,
    }))
  }, [inWindow])

  const toggleCat = (c: NewsCategory) =>
    setCats((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]))

  const activeFilters = cats.length + (sentiment !== 'all' ? 1 : 0) + (impact !== 'all' ? 1 : 0) + (query ? 1 : 0)

  const clearAll = () => {
    setCats([])
    setSentiment('all')
    setImpact('all')
    setQuery('')
  }

  return (
    <div className="space-y-3">
      {/* filter bar */}
      <div className="rounded-xl border border-line bg-surface p-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[180px] flex-1">
            <Search
              size={13}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-faint"
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by keyword, entity or source…"
              className="h-8 w-full rounded-lg border border-line bg-surface-2 pl-8 pr-2.5 text-[12.5px] text-ink outline-none placeholder:text-faint focus:border-accent/50"
            />
          </div>

          <Segmented
            size="sm"
            value={sentiment}
            onChange={setSentiment}
            options={[
              { value: 'all', label: 'Any tone' },
              { value: 'positive', label: 'Positive' },
              { value: 'neutral', label: 'Neutral' },
              { value: 'negative', label: 'Negative' },
            ]}
          />

          <Segmented
            size="sm"
            value={String(impact)}
            onChange={(v) => setImpact(v === 'all' ? 'all' : Number(v))}
            options={[
              { value: 'all', label: 'Any impact' },
              { value: '2', label: 'Notable+' },
              { value: '3', label: 'High only' },
            ]}
          />

          <Segmented
            size="sm"
            value={sort}
            onChange={setSort}
            options={[
              { value: 'newest', label: 'Newest' },
              { value: 'oldest', label: 'Oldest' },
              { value: 'impact', label: 'Impact' },
            ]}
          />
        </div>

        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          <Filter size={11} className="text-faint" />
          {availableCats.map(({ category, count }) => (
            <button
              key={category}
              type="button"
              onClick={() => toggleCat(category)}
              className={clsx(
                'inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors',
                cats.includes(category)
                  ? 'border-accent/40 bg-accent-soft text-accent-text'
                  : 'border-line bg-surface-2 text-faint hover:text-muted',
              )}
            >
              {CATEGORY_LABEL[category]}
              <span className="tabular opacity-60">{count}</span>
            </button>
          ))}
          {activeFilters > 0 && (
            <button
              type="button"
              onClick={clearAll}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-negative hover:bg-negative-soft"
            >
              <X size={10} />
              clear {activeFilters}
            </button>
          )}
        </div>
      </div>

      {highlighted && (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-accent/40 bg-accent-soft px-3 py-2">
          <div className="text-[12px] text-accent-text">
            Jumped to the item referenced by your selection.
          </div>
          <Button size="sm" variant="ghost" onClick={onClearHighlight}>
            <X size={12} />
          </Button>
        </div>
      )}

      {/* grouped timeline */}
      {grouped.length === 0 ? (
        <div className="rounded-xl border border-line bg-surface">
          <EmptyState
            icon={<Inbox size={22} />}
            title="Nothing matches those filters"
            body="Loosen the filters or clear the keyword to see the full window."
            action={
              <Button size="sm" variant="outline" onClick={clearAll}>
                Clear filters
              </Button>
            }
          />
        </div>
      ) : (
        <div className="space-y-4">
          {grouped.map(([date, items]) => (
            <div key={date} className="animate-rise">
              <div className="sticky top-[148px] z-10 mb-2 flex items-center gap-2 bg-bg/85 py-1 backdrop-blur-sm">
                <span className="tabular text-[11.5px] font-semibold text-ink">{relativeLabel(`${date}T12:00:00Z`)}</span>
                <span className="text-[11px] text-faint">{date}</span>
                <span className="h-px flex-1 bg-line" />
                <Badge tone="neutral">{items.length}</Badge>
              </div>
              <div className="space-y-2.5">
                {items.map((n) => (
                  <NewsCard
                    key={n.id}
                    item={n}
                    referenced={highlighted === n.id}
                    onReferenceClick={() => {
                      document
                        .getElementById(`news-${n.id}`)
                        ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                    }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* out of window */}
      {outWindow.length > 0 && (
        <div className="rounded-xl border border-dashed border-line bg-surface-2">
          <button
            type="button"
            onClick={() => setShowOutOfWindow((s) => !s)}
            className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
          >
            <div>
              <div className="text-[12.5px] font-medium text-muted">
                {outWindow.length} items indexed outside the {windowDays}-day window
              </div>
              <div className="text-[11px] text-faint">
                Excluded from the brief by design — open only if you need the back-story.
              </div>
            </div>
            <Badge tone="neutral">{showOutOfWindow ? 'Hide' : 'Show'}</Badge>
          </button>
          {showOutOfWindow && (
            <div className="space-y-2.5 px-3 pb-3">
              {outWindow.map((n) => (
                <NewsCard key={n.id} item={n} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
