import { useMemo } from 'react'
import { ArrowLeft, Building2, GitCompare, User } from 'lucide-react'
import { Badge, Button, Card, EmptyState, SectionTitle } from './ui'
import { CATEGORY_LABEL } from '../lib/templates'
import { fmtShortDate } from '../lib/format'
import type { HistoryEntry } from '../types'

export function CompareView({
  candidates,
  leftId,
  rightId,
  onPick,
  onBack,
}: {
  candidates: HistoryEntry[]
  leftId: string | null
  rightId: string | null
  onPick: (side: 'left' | 'right', id: string) => void
  onBack: () => void
}) {
  const left = candidates.find((c) => c.id === leftId) ?? null
  const right = candidates.find((c) => c.id === rightId) ?? null

  const rows = useMemo(() => {
    if (!left || !right) return []
    const leftFacts = new Map(left.result.snapshot.facts.map((f) => [f.label, f.value]))
    const rightFacts = new Map(right.result.snapshot.facts.map((f) => [f.label, f.value]))
    const labels = Array.from(
      new Set([...leftFacts.keys(), ...rightFacts.keys()]),
    ).slice(0, 8)
    return labels.map((l) => ({
      label: l,
      left: leftFacts.get(l) ?? '—',
      right: rightFacts.get(l) ?? '—',
    }))
  }, [left, right])

  return (
    <div className="mx-auto max-w-[1100px] px-4 py-6 lg:px-6">
      <div className="mb-4 flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft size={14} />
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="text-[16px] font-semibold tracking-tight text-ink">Compare</h1>
          <div className="text-[11.5px] text-faint">
            Put two subjects side by side before you decide who to prioritise
          </div>
        </div>
      </div>

      {candidates.length < 2 ? (
        <Card>
          <EmptyState
            icon={<GitCompare size={22} />}
            title="Need two briefings to compare"
            body="Research at least two subjects and they will show up here as comparison candidates."
          />
        </Card>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Slot label="Subject A" value={leftId} candidates={candidates} onPick={(id) => onPick('left', id)} />
            <Slot label="Subject B" value={rightId} candidates={candidates} onPick={(id) => onPick('right', id)} />
          </div>

          {left && right && left.id === right.id ? (
            <Card>
              <EmptyState
                icon={<GitCompare size={22} />}
                title="Pick two different subjects"
                body="Both slots are on the same briefing. Choose another one to see a comparison."
              />
            </Card>
          ) : left && right ? (
            <>
              <Card>
                <SectionTitle eyebrow="Comparison" title={`${left.subject} vs ${right.subject}`} />
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[540px] text-left">
                    <thead>
                      <tr className="border-b border-line text-[10px] uppercase tracking-[0.12em] text-faint">
                        <th className="px-5 py-2 font-semibold">Field</th>
                        <th className="px-5 py-2 font-semibold">{left.subject}</th>
                        <th className="px-5 py-2 font-semibold">{right.subject}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => (
                        <tr key={r.label} className="border-b border-line last:border-0">
                          <td className="px-5 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-faint">
                            {r.label}
                          </td>
                          <td className="px-5 py-2.5 text-[12.5px] text-ink">{r.left}</td>
                          <td className="px-5 py-2.5 text-[12.5px] text-ink">{r.right}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              <div className="grid gap-3 sm:grid-cols-2">
                {[
                  { entry: left, accent: 'A' },
                  { entry: right, accent: 'B' },
                ].map(({ entry, accent }) => (
                  <Card key={accent} className="p-4">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-md bg-accent-soft text-[11px] font-semibold text-accent-text">
                        {accent}
                      </span>
                      <span className="truncate text-[13px] font-semibold text-ink">
                        {entry.subject}
                      </span>
                    </div>

                    <div className="mt-3 grid grid-cols-3 gap-2">
                      <div>
                        <div className="text-[10px] uppercase tracking-wide text-faint">Items</div>
                        <div className="tabular text-[15px] font-semibold text-ink">
                          {entry.stats.articles}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-wide text-faint">Outlets</div>
                        <div className="tabular text-[15px] font-semibold text-ink">
                          {entry.stats.sources}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-wide text-faint">Net tone</div>
                        <div className="tabular text-[15px] font-semibold text-ink">
                          {entry.stats.avgSentiment > 0 ? '+' : ''}
                          {entry.stats.avgSentiment.toFixed(2)}
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 border-t border-line pt-2.5">
                      <div className="text-[10px] uppercase tracking-wide text-faint">
                        Top coverage categories
                      </div>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {entry.result.coverage.slice(0, 4).map((c) => (
                          <span
                            key={c.category}
                            className="rounded border border-line px-1.5 py-0.5 text-[10.5px] text-muted"
                          >
                            {CATEGORY_LABEL[c.category]} · {c.count}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="mt-3 border-t border-line pt-2.5">
                      <div className="text-[10px] uppercase tracking-wide text-faint">Lead story</div>
                      <div className="mt-1 text-[12px] leading-relaxed text-ink">
                        {entry.result.news.find((n) => n.isKey)?.headline ??
                          entry.result.news.find((n) => n.inWindow)?.headline ??
                          '—'}
                      </div>
                    </div>

                    <div className="mt-3 space-y-1.5 border-t border-line pt-2.5">
                      {entry.result.news
                        .filter((n) => n.inWindow)
                        .slice(0, 3)
                        .map((n) => (
                          <div key={n.id} className="flex gap-2 text-[11px] leading-relaxed">
                            <span className="tabular shrink-0 text-faint">
                              {fmtShortDate(n.publishedAt)}
                            </span>
                            <span className="text-muted">{n.headline}</span>
                          </div>
                        ))}
                    </div>
                  </Card>
                ))}
              </div>
            </>
          ) : (
            <Card>
              <EmptyState
                icon={<GitCompare size={22} />}
                title="Pick two subjects"
                body="Choose two briefings above to see their coverage, tone and positioning side by side."
              />
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

function Slot({
  label,
  value,
  candidates,
  onPick,
}: {
  label: string
  value: string | null
  candidates: HistoryEntry[]
  onPick: (id: string) => void
}) {
  const current = candidates.find((c) => c.id === value)
  return (
    <Card className="p-3.5">
      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">{label}</div>
      <div className="mt-2 flex items-center gap-2.5">
        {current && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent-text">
            {current.type === 'company' ? <Building2 size={14} /> : <User size={14} />}
          </div>
        )}
        <select
          value={value ?? ''}
          onChange={(e) => onPick(e.target.value)}
          className="h-8 min-w-0 flex-1 rounded-lg border border-line bg-surface-2 px-2 text-[12.5px] text-ink outline-none focus:border-accent/50"
        >
          <option value="">Choose a briefing…</option>
          {candidates.map((c) => (
            <option key={c.id} value={c.id}>
              {c.subject}
            </option>
          ))}
        </select>
      </div>
      {current && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <Badge tone="neutral">{current.type}</Badge>
          <Badge tone="neutral">{current.stats.articles} items</Badge>
        </div>
      )}
    </Card>
  )
}
