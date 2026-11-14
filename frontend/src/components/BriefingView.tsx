import { lazy, Suspense, useMemo, useState } from 'react'
import {
  ArrowLeft,
  Bell,
  BellRing,
  BookOpen,
  CalendarDays,
  ChartNoAxesColumn,
  ExternalLink,
  LayoutGrid,
  MessageSquare,
  Newspaper,
  Quote,
  RefreshCw,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Badge, Button, Card, SectionTitle, Stat } from './ui'
import { SnapshotPanel } from './SnapshotPanel'
import { PrintBrief } from './PrintBrief'
import { NewsTimeline } from './NewsTimeline'
import { SignalsPanel } from './SignalsPanel'
import { QuestionsPanel, TalkingPointsPanel } from './PrepPanel'
import { ExportMenu } from './ExportMenu'
import { NewsCard } from './NewsCard'
import { ImageGallery } from './ImageGallery'
import { CATEGORY_LABEL } from '../lib/templates'
import { fmtDate, fmtDateTime, relativeTime } from '../lib/format'
import type { BriefingResult, MeetingContext } from '../types'

// Charts pull in a large charting library — load them only when the tab is opened.
const AnalyticsPanel = lazy(() =>
  import('./AnalyticsPanel').then((m) => ({ default: m.AnalyticsPanel })),
)

type Tab = 'overview' | 'coverage' | 'visuals' | 'analytics' | 'prep' | 'sources'

const TABS: { id: Tab; label: string; icon: typeof LayoutGrid }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutGrid },
  { id: 'coverage', label: 'Coverage', icon: Newspaper },
  { id: 'visuals', label: 'Visuals', icon: LayoutGrid },
  { id: 'analytics', label: 'Signals', icon: ChartNoAxesColumn },
  { id: 'prep', label: 'Prep', icon: Quote },
  { id: 'sources', label: 'Sources', icon: BookOpen },
]

export function BriefingView({
  briefing,
  meeting,
  onNewResearch,
  onAsk,
  watched,
  onToggleWatch,
  onSetMeeting,
}: {
  briefing: BriefingResult
  meeting?: MeetingContext
  onNewResearch: () => void
  onAsk: () => void
  watched: boolean
  onToggleWatch: () => void
  onSetMeeting?: () => void
}) {
  const [tab, setTab] = useState<Tab>('overview')
  const [highlighted, setHighlighted] = useState<string | null>(null)

  const newsById = useMemo(
    () => new Map(briefing.news.map((n) => [n.id, n])),
    [briefing.news],
  )

  const inWindow = useMemo(() => briefing.news.filter((n) => n.inWindow), [briefing.news])
  const keyItems = useMemo(() => inWindow.filter((n) => n.isKey), [inWindow])
  const shownKey = keyItems.length ? keyItems : inWindow.filter((n) => n.impact === 3).slice(0, 4)

  const gotoEvidence = (id: string) => {
    setHighlighted(id)
    setTab('coverage')
    setTimeout(() => {
      document.getElementById(`news-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 90)
  }

  return (
    <div className="min-h-full">
      {/* ---------- header ---------- */}
      <header className="sticky top-14 z-30 border-b border-line bg-bg/85 backdrop-blur-md print:hidden">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-3 px-4 py-2.5 lg:px-6">
          <Button variant="ghost" size="sm" onClick={onNewResearch} aria-label="Back">
            <ArrowLeft size={14} />
          </Button>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-[14px] font-semibold tracking-tight text-ink">
                {briefing.snapshot.name}
              </h1>
              <Badge tone="neutral">{briefing.type}</Badge>
              {briefing.synthetic && (
                <Badge tone="warning" className="hidden sm:inline-flex">
                  Demo data
                </Badge>
              )}
            </div>
            <div className="truncate text-[11px] text-faint">
              {briefing.stats.articles} items · {briefing.stats.sources} outlets · last{' '}
              {briefing.windowDays} days · generated {relativeTime(briefing.generatedAt)}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onSetMeeting && (
              <Button
                variant="outline"
                size="sm"
                onClick={onSetMeeting}
                className="hidden lg:inline-flex"
                title="Attach meeting details to this brief"
              >
                <CalendarDays size={13} />
                {meeting?.title ? meeting.title : 'Meeting'}
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={onToggleWatch}
              active={watched}
              aria-label={watched ? 'Remove from watchlist' : 'Add to watchlist'}
            >
              {watched ? <BellRing size={13} /> : <Bell size={13} />}
              <span className="hidden md:inline">{watched ? 'Watching' : 'Watch'}</span>
            </Button>

            <Button variant="outline" size="sm" onClick={onAsk}>
              <MessageSquare size={13} />
              <span className="hidden md:inline">Ask agent</span>
            </Button>

            <ExportMenu briefing={briefing} meeting={meeting} compact />
          </div>
        </div>

        {/* tabs */}
        <div className="mx-auto max-w-[1400px] px-2 lg:px-4">
          <div className="flex items-center gap-0.5 overflow-x-auto">
            {TABS.map((t) => {
              const Icon = t.icon
              const active = tab === t.id
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTab(t.id)}
                  className={clsx(
                    'relative flex items-center gap-1.5 whitespace-nowrap px-3 py-2 text-[12.5px] font-medium transition-colors',
                    active ? 'text-ink' : 'text-faint hover:text-muted',
                  )}
                >
                  <Icon size={13} />
                  {t.label}
                  {active && (
                    <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent" />
                  )}
                </button>
              )
            })}
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1400px] px-4 py-5 lg:px-6">
        {briefing.synthetic && (
          <div className="mb-4 flex items-start gap-2.5 rounded-xl border border-warning/30 bg-warning-soft px-3.5 py-2.5 print:hidden">
            <div className="text-[11.5px] leading-relaxed text-warning">
              <span className="font-semibold">Demo corpus.</span> Every company, person, figure
              and headline below is synthetic — it exists to exercise the interface, not to inform
              a real meeting. Point the app at a live backend to use real intelligence.
            </div>
          </div>
        )}

        <div className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)] print:hidden">
          {/* ---------- left rail ---------- */}
          <aside className="lg:sticky lg:top-[156px] lg:max-h-[calc(100vh-120px)] lg:overflow-y-auto lg:pr-1">
            <SnapshotPanel briefing={briefing} />
          </aside>

          {/* ---------- main ---------- */}
          <main className="min-w-0 space-y-4">
            {tab === 'overview' && (
              <OverviewTab
                briefing={briefing}
                keyItems={shownKey}
                onGotoEvidence={gotoEvidence}
                onOpenCoverage={() => setTab('coverage')}
                onOpenPrep={() => setTab('prep')}
              />
            )}

            {tab === 'coverage' && (
              <NewsTimeline
                news={briefing.news}
                windowDays={briefing.windowDays}
                highlighted={highlighted}
                onClearHighlight={() => setHighlighted(null)}
              />
            )}

            {tab === 'visuals' && (
              <ImageGallery
                images={briefing.images ?? []}
                subject={briefing.subject}
                subjectType={briefing.type}
              />
            )}

            {tab === 'analytics' && (
              <>
                <Suspense fallback={<ChartSkeleton />}>
                  <AnalyticsPanel briefing={briefing} />
                </Suspense>
                <SignalsPanel
                  signals={briefing.signals}
                  newsById={newsById}
                  onEvidence={gotoEvidence}
                />
              </>
            )}

            {tab === 'prep' && (
              <>
                <TalkingPointsPanel
                  points={briefing.talkingPoints}
                  newsById={newsById}
                  onEvidence={gotoEvidence}
                />
                <QuestionsPanel
                  questions={briefing.questions}
                  newsById={newsById}
                  onEvidence={gotoEvidence}
                />
              </>
            )}

            {tab === 'sources' && <SourcesTab briefing={briefing} />}
          </main>
        </div>
      </div>

      {/* Paper version — replaces the whole app chrome when printing. */}
      <PrintBrief briefing={briefing} meeting={meeting} />
    </div>
  )
}

/* ------------------------------------------------------------------ */
function ChartSkeleton() {
  return (
    <Card className="p-5">
      <div className="h-[210px] w-full overflow-hidden rounded-xl bg-surface-2 shimmer" />
    </Card>
  )
}

/* ------------------------------------------------------------------ */
function OverviewTab({
  briefing,
  keyItems,
  onGotoEvidence,
  onOpenCoverage,
  onOpenPrep,
}: {
  briefing: BriefingResult
  keyItems: BriefingResult['news']
  onGotoEvidence: (id: string) => void
  onOpenCoverage: () => void
  onOpenPrep: () => void
}) {
  const avg = briefing.stats.avgSentiment
  const tone = avg > 0.15 ? 'positive' : avg < -0.15 ? 'negative' : 'neutral'

  return (
    <div className="space-y-4">
      <Card className="px-5 py-4">
        <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3 lg:grid-cols-5">
          <Stat label="In-window items" value={briefing.stats.articles} hint={`${briefing.stats.daysCovered} active days`} />
          <Stat label="Outlets" value={briefing.stats.sources} hint="distinct sources" />
          <Stat
            label="Net tone"
            value={`${avg > 0 ? '+' : ''}${avg.toFixed(2)}`}
            hint={tone === 'positive' ? 'net positive' : tone === 'negative' ? 'net negative' : 'balanced'}
            tone={tone === 'neutral' ? undefined : tone}
          />
          <Stat label="Key items" value={briefing.stats.keyItems} hint="flagged high-impact" />
          <Stat
            label="Categories"
            value={briefing.stats.categoriesCovered}
            hint={`across ${briefing.windowDays} days`}
          />
        </div>
      </Card>

      <Card>
        <SectionTitle
          eyebrow="Headlines"
          title="What actually happened"
          count={keyItems.length}
          action={
            <Button size="sm" variant="ghost" onClick={onOpenCoverage}>
              <RefreshCw size={12} />
              All coverage
            </Button>
          }
        />
        <div className="space-y-2.5 px-4 pb-4">
          {keyItems.length === 0 && (
            <div className="rounded-lg border border-dashed border-line px-4 py-6 text-center text-[12.5px] text-muted">
              No high-impact item in the window. Quiet cycles are common — it usually means the
              information you need is in the talking points and questions, not the headlines.
            </div>
          )}
          {keyItems.map((n) => (
            <NewsCard key={n.id} item={n} onReferenceClick={onGotoEvidence} />
          ))}
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle eyebrow="Signals" title="What to carry in" count={briefing.signals.length} />
          <div className="space-y-2 px-4 pb-4">
            {briefing.signals.map((sig) => {
              const color =
                sig.kind === 'risk'
                  ? 'text-negative'
                  : sig.kind === 'opportunity'
                    ? 'text-positive'
                    : 'text-warning'
              const glyph = sig.kind === 'risk' ? '▲' : sig.kind === 'opportunity' ? '✦' : '◎'
              return (
                <div key={sig.id} className="flex gap-2.5">
                  <span className={clsx('mt-0.5 text-[11px]', color)}>{glyph}</span>
                  <div className="min-w-0">
                    <div className="text-[12.5px] font-medium text-ink">{sig.title}</div>
                    <div className="mt-0.5 text-[11.5px] leading-relaxed text-muted">{sig.detail}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </Card>

        <Card>
          <SectionTitle
            eyebrow="Prep"
            title="Open with one of these"
            count={briefing.talkingPoints.length}
            action={
              <Button size="sm" variant="ghost" onClick={onOpenPrep}>
                Full prep
              </Button>
            }
          />
          <div className="space-y-2 px-4 pb-4">
            {briefing.talkingPoints.slice(0, 4).map((tp, i) => (
              <div key={tp.id} className="flex gap-2.5">
                <span className="tabular mt-0.5 flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded bg-accent-soft text-[10px] font-semibold text-accent-text">
                  {i + 1}
                </span>
                <div className="min-w-0">
                  <div className="text-[12.5px] font-medium leading-snug text-ink">{tp.text}</div>
                  <div className="mt-0.5 text-[11.5px] italic leading-relaxed text-muted">
                    “{tp.opener}”
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <SectionTitle eyebrow="Coverage map" title="Category breakdown in the window" />
        <div className="flex flex-wrap gap-2 px-4 pb-4">
          {briefing.coverage.map((c) => {
            const max = briefing.coverage[0]?.count || 1
            return (
              <div
                key={c.category}
                className="min-w-[150px] flex-1 rounded-lg border border-line bg-surface-2 px-3 py-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11.5px] font-medium text-ink">{CATEGORY_LABEL[c.category]}</span>
                  <span className="tabular text-[11px] text-faint">{c.count}</span>
                </div>
                <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-surface-3">
                  <div
                    className="h-full rounded-full bg-accent/70"
                    style={{ width: `${(c.count / max) * 100}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}

/* ------------------------------------------------------------------ */
function SourcesTab({ briefing }: { briefing: BriefingResult }) {
  const bySource = useMemo(() => {
    const map = new Map<string, number>()
    briefing.news
      .filter((n) => n.inWindow)
      .forEach((n) => map.set(n.source, (map.get(n.source) ?? 0) + 1))
    return [...map.entries()].sort((a, b) => b[1] - a[1])
  }, [briefing.news])

  const outsideCount = briefing.news.length - briefing.news.filter((n) => n.inWindow).length

  return (
    <div className="space-y-4">
      <Card>
        <SectionTitle
          eyebrow="Provenance"
          title="Outlets covered in the window"
          count={bySource.length}
        />
        <div className="flex flex-wrap gap-1.5 px-4 pb-4">
          {bySource.map(([name, count]) => (
            <span
              key={name}
              className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface-2 px-2 py-1 text-[11px] text-muted"
            >
              {name}
              <span className="tabular text-faint">{count}</span>
            </span>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle
          eyebrow="Index"
          title="Every item, in full"
          count={briefing.sources.length}
          action={
            outsideCount > 0 ? (
              <span className="text-[11px] text-faint">
                {outsideCount} outside the {briefing.windowDays}-day window
              </span>
            ) : undefined
          }
        />
        <div className="divide-y divide-line">
          {briefing.sources.map((s) => (
            <div key={s.id} className="flex items-start gap-3 px-5 py-2.5">
              <span className="tabular mt-0.5 w-14 shrink-0 text-[11px] text-faint">
                {fmtDate(s.publishedAt).slice(0, 6)}
              </span>
              <div className="min-w-0 flex-1">
                <div
                  className={clsx(
                    'truncate text-[12.5px]',
                    s.inWindow ? 'text-ink' : 'text-faint',
                  )}
                >
                  {s.headline}
                </div>
                <div className="mt-0.5 flex items-center gap-2 text-[10.5px] text-faint">
                  {s.url ? (
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 underline decoration-line-strong underline-offset-2 transition-colors hover:text-ink hover:decoration-accent"
                    >
                      {s.name}
                      <ExternalLink size={9} />
                    </a>
                  ) : (
                    <span>{s.name}</span>
                  )}
                  <span>·</span>
                  <span>{CATEGORY_LABEL[s.category]}</span>
                  {!s.inWindow && (
                    <>
                      <span>·</span>
                      <span className="text-warning/80">outside window</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="border-t border-line px-5 py-3 text-[11px] text-faint">
          Research window {fmtDate(briefing.windowStart)} → {fmtDate(briefing.windowEnd)} · briefing
          assembled {fmtDateTime(briefing.generatedAt)}
        </div>
      </Card>
    </div>
  )
}
