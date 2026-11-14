import { useState } from 'react'
import { Download, ExternalLink, FileJson, Printer, RefreshCw } from 'lucide-react'
import { Badge, Button, Card, SectionTitle } from './ui'
import { downloadOnePagerJson, downloadOnePagerPdf, generateOnePager } from '../lib/api'
import type { OnePageBrief, OnePageRequest } from '../types'

function BulletList({
  title,
  items,
  empty,
}: {
  title: string
  items: { text: string; isAnalysis?: boolean }[]
  empty: string
}) {
  return (
    <div className="space-y-1.5">
      <h3 className="text-[12px] font-semibold uppercase tracking-wide text-faint">{title}</h3>
      {items.length === 0 ? (
        <p className="text-[12.5px] italic text-muted">{empty}</p>
      ) : (
        <ul className="space-y-1">
          {items.map((b, i) => (
            <li key={i} className="text-[13px] leading-snug text-ink">
              <span className="text-faint">• </span>
              {b.text}
              {b.isAnalysis && (
                <Badge tone="neutral" className="ml-1.5">
                  Analysis
                </Badge>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function OnePageBriefView({
  initial,
  onClose,
}: {
  initial?: Partial<OnePageRequest>
  onClose?: () => void
}) {
  const [entityName, setEntityName] = useState(initial?.entityName ?? '')
  const [entityType, setEntityType] = useState<OnePageRequest['entityType']>(
    initial?.entityType ?? 'auto',
  )
  const [meetingAt, setMeetingAt] = useState(
    initial?.meetingAt ?? new Date().toISOString().slice(0, 16),
  )
  const [context, setContext] = useState(initial?.meetingContext ?? '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [brief, setBrief] = useState<OnePageBrief | null>(null)

  /** Convert datetime-local value to ISO with the browser's real timezone offset (never append bare Z). */
  function toOffsetIso(localValue: string): string {
    // localValue is "YYYY-MM-DDTHH:mm" or with seconds
    const normalized = localValue.length === 16 ? `${localValue}:00` : localValue
    const d = new Date(normalized)
    if (Number.isNaN(d.getTime())) {
      // Fallback: keep as-is rather than inventing Z
      return normalized
    }
    const pad = (n: number) => String(Math.abs(n)).padStart(2, '0')
    const offsetMin = -d.getTimezoneOffset()
    const sign = offsetMin >= 0 ? '+' : '-'
    const hh = pad(Math.floor(Math.abs(offsetMin) / 60))
    const mm = pad(Math.abs(offsetMin) % 60)
    const yyyy = d.getFullYear()
    const mo = pad(d.getMonth() + 1)
    const day = pad(d.getDate())
    const h = pad(d.getHours())
    const mi = pad(d.getMinutes())
    const ss = pad(d.getSeconds())
    return `${yyyy}-${mo}-${day}T${h}:${mi}:${ss}${sign}${hh}:${mm}`
  }

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const req: OnePageRequest = {
        entityName: entityName.trim(),
        entityType,
        meetingAt: toOffsetIso(meetingAt),
        meetingContext: context.trim() || undefined,
        windowDays: 30,
      }
      const result = await generateOnePager(req)
      setBrief(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate brief')
    } finally {
      setLoading(false)
    }
  }

  async function onPdf() {
    if (!brief) return
    try {
      await downloadOnePagerPdf({
        entityName: brief.entityName,
        entityType: brief.entityType,
        meetingAt: brief.meetingAt,
        meetingContext: context || undefined,
        windowDays: 30,
        researchSessionId: brief.researchSessionId,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'PDF download failed')
    }
  }

  async function onJson() {
    if (!brief) return
    try {
      await downloadOnePagerJson({
        entityName: brief.entityName,
        entityType: brief.entityType,
        meetingAt: brief.meetingAt,
        meetingContext: context || undefined,
        windowDays: 30,
        researchSessionId: brief.researchSessionId,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'JSON download failed')
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold text-ink">One-page meeting brief</h1>
          <p className="text-[12px] text-muted">
            Research window is the 30 days ending on the meeting date. Every fact is cited.
          </p>
        </div>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        )}
      </div>

      <Card className="space-y-3 p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-[12px] font-medium text-muted">
            Entity name
            <input
              className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink"
              value={entityName}
              onChange={(e) => setEntityName(e.target.value)}
              placeholder="Company or person"
            />
          </label>
          <label className="block text-[12px] font-medium text-muted">
            Type
            <select
              className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink"
              value={entityType}
              onChange={(e) => setEntityType(e.target.value as OnePageRequest['entityType'])}
            >
              <option value="auto">Auto</option>
              <option value="company">Company</option>
              <option value="person">Person</option>
            </select>
          </label>
          <label className="block text-[12px] font-medium text-muted">
            Meeting date & time
            <input
              type="datetime-local"
              className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink"
              value={meetingAt}
              onChange={(e) => setMeetingAt(e.target.value)}
            />
          </label>
          <label className="block text-[12px] font-medium text-muted">
            Meeting context (optional)
            <input
              className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="e.g. partnership discussion"
            />
          </label>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={run} disabled={loading || !entityName.trim()}>
            {loading ? 'Researching…' : brief ? 'Regenerate brief' : 'Generate one-page brief'}
            <RefreshCw size={14} className={loading ? 'ml-1.5 animate-spin' : 'ml-1.5'} />
          </Button>
        </div>
        {error && <p className="text-sm text-negative">{error}</p>}
      </Card>

      {brief && (
        <Card className="space-y-4 p-5 print:border-0 print:shadow-none" id="one-page-preview">
          <div className="flex flex-wrap items-start justify-between gap-2 border-b border-line pb-3">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-ink">{brief.entityName}</h2>
              <p className="mt-1 text-[12px] text-muted">
                {brief.entityType} · Meeting {brief.meetingAt.slice(0, 16)} · Research{' '}
                {brief.researchWindowStart.slice(0, 10)} – {brief.researchWindowEnd.slice(0, 10)} ·
                Generated {brief.generatedAt.slice(0, 10)}
              </p>
              {!brief.pageFits && brief.overflowNote && (
                <p className="mt-1 text-[11px] text-warning">{brief.overflowNote}</p>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5 print:hidden">
              <Button size="sm" variant="subtle" onClick={onPdf}>
                <Download size={13} className="mr-1" /> PDF
              </Button>
              <Button size="sm" variant="ghost" onClick={onJson}>
                <FileJson size={13} className="mr-1" /> JSON
              </Button>
              <Button size="sm" variant="ghost" onClick={() => window.print()}>
                <Printer size={13} className="mr-1" /> Print
              </Button>
            </div>
          </div>

          <section>
            <SectionTitle title="A · Executive snapshot" />
            <p className="mt-1 text-[13.5px] leading-relaxed text-ink">{brief.executiveSnapshot}</p>
          </section>

          <section className="space-y-3">
            <SectionTitle title="B · Last 30 days" />
            <BulletList title="News" items={brief.news} empty="No verified news in window." />
            <BulletList
              title="Hires & leadership"
              items={brief.hiresAndLeadership}
              empty="No verified hires or leadership changes in window."
            />
            <BulletList
              title="Product & service launches"
              items={brief.productAndServiceLaunches}
              empty="No verified launches in window."
            />
          </section>

          <section>
            <SectionTitle title="C · What matters for this meeting" />
            <p className="mb-1 text-[11px] italic text-faint">Analytical notes — not verified facts</p>
            <BulletList title="" items={brief.whatMatters} empty="—" />
          </section>

          <section>
            <SectionTitle title="D · Open questions" />
            <ol className="mt-1 list-decimal space-y-1 pl-4 text-[13px] text-ink">
              {brief.openQuestions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ol>
          </section>

          <section className="border-t border-line pt-3">
            <SectionTitle title="Sources" />
            <ul className="mt-1 space-y-1">
              {brief.citations.map((c) => (
                <li key={c.index} className="text-[11.5px] text-muted">
                  <span className="font-medium text-ink">[{c.index}]</span>{' '}
                  {c.publisher}
                  {c.publishedAt ? ` · ${c.publishedAt.slice(0, 10)}` : ''} — {c.title}{' '}
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-0.5 text-accent-text hover:underline"
                  >
                    Open <ExternalLink size={10} />
                  </a>
                </li>
              ))}
            </ul>
            {brief.limitations.length > 0 && (
              <div className="mt-3">
                <h3 className="text-[11px] font-semibold uppercase text-faint">Coverage limitations</h3>
                <ul className="mt-1 space-y-0.5 text-[11.5px] text-muted">
                  {brief.limitations.map((l, i) => (
                    <li key={i}>• {l}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        </Card>
      )}
    </div>
  )
}
