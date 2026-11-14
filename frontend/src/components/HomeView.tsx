import { ArrowRight, Building2, Clock, Radar, Sparkles, User } from 'lucide-react'
import { Badge, Button, Card, EmptyState, SectionTitle } from './ui'
import { SubjectSearch } from './SubjectSearch'
import { DEMO_COMPANIES, DEMO_PEOPLE } from '../lib/archetypes'
import { relativeTime } from '../lib/format'
import type { BriefingRequest, HistoryEntry } from '../types'
import type { WatchItem } from '../lib/store'

export function HomeView({
  onResearch,
  history,
  watchlist,
  onOpenHistory,
  onOpenWatchlist,
  onOpenEntry,
  loading,
  defaultType,
  defaultDays,
}: {
  onResearch: (
    subject: string,
    type: BriefingRequest['type'],
    days: number,
    focus?: string,
    meetingAt?: string,
  ) => void

  history: HistoryEntry[]
  watchlist: WatchItem[]
  onOpenHistory: () => void
  onOpenWatchlist: () => void
  onOpenEntry: (entry: HistoryEntry) => void
  loading: boolean
  defaultType: BriefingRequest['type']
  defaultDays: number
}) {
  return (
    <div className="mx-auto max-w-[1100px] px-4 py-10 lg:px-6 lg:py-16">
      {/* hero */}
      <div className="relative overflow-hidden rounded-2xl border border-line bg-surface px-5 py-10 shadow-card sm:px-10 lg:px-14 lg:py-14">
        <div className="grain pointer-events-none absolute inset-0 opacity-60" />
        <div
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full opacity-[0.18] blur-3xl"
          style={{ background: 'radial-gradient(circle, var(--accent), transparent 70%)' }}
        />

        <div className="relative">
          <Badge tone="accent" icon={<Sparkles size={10} />}>
            Pre-meeting intelligence
          </Badge>

          <h1 className="font-display mt-4 max-w-2xl text-[34px] leading-[1.08] tracking-tight text-ink sm:text-[46px]">
            Prepare your next meeting.
          </h1>

          <p className="mt-3 max-w-xl text-[14px] leading-relaxed text-muted">
            Enter a company or person and the meeting date. PreBrief researches the previous 30 days
            of news, hires, and launches, then produces a one-page brief where every factual claim
            is backed by a source.
          </p>

          <div className="mt-7">
            <SubjectSearch
              onSubmit={onResearch}
              loading={loading}
              defaultType={defaultType}
              defaultDays={defaultDays}
              variant="hero"
            />
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-[11px] text-faint">Try:</span>
            {DEMO_COMPANIES.slice(0, 3).map((c) => (
              <button
                key={c.name}
                type="button"
                onClick={() => onResearch(c.name, 'company', defaultDays)}
                className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface-2 px-2 py-1 text-[11px] text-muted transition-colors hover:border-accent/40 hover:text-ink"
              >
                <Building2 size={10} />
                {c.name}
              </button>
            ))}
            {DEMO_PEOPLE.slice(0, 2).map((p) => (
              <button
                key={p.name}
                type="button"
                onClick={() => onResearch(p.name, 'person', defaultDays)}
                className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface-2 px-2 py-1 text-[11px] text-muted transition-colors hover:border-accent/40 hover:text-ink"
              >
                <User size={10} />
                {p.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* capabilities */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            icon: <Radar size={15} />,
            title: '30-day sweep',
            body: 'Every outlet, filing and press mention inside a hard window — older items are indexed but excluded.',
          },
          {
            icon: <Sparkles size={15} />,
            title: 'Signal over noise',
            body: 'Coverage clustered by theme, scored for tone and impact, and reduced to the handful of things that move.',
          },
          {
            icon: <Clock size={15} />,
            title: 'Prep that survives contact',
            body: 'An opener per talking point, with the rationale — so you know why the question is worth the follow-up.',
          },
          {
            icon: <ArrowRight size={15} />,
            title: 'Ask the brief',
            body: 'Follow-up questions answered from the dossier only. If the window does not cover it, the agent says so.',
          },
        ].map((f) => (
          <Card key={f.title} className="p-4">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-soft text-accent-text">
              {f.icon}
            </div>
            <div className="mt-2.5 text-[13px] font-semibold tracking-tight text-ink">{f.title}</div>
            <div className="mt-1 text-[11.5px] leading-relaxed text-muted">{f.body}</div>
          </Card>
        ))}
      </div>

      {/* recent */}
      <div className="mt-8">
        <Card>
          <SectionTitle
            eyebrow="Recent"
            title="Your briefings"
            count={history.length}
            action={
              history.length > 0 && (
                <Button size="sm" variant="ghost" onClick={onOpenHistory}>
                  View all
                </Button>
              )
            }
          />
          {history.length === 0 ? (
            <EmptyState
              icon={<Sparkles size={22} />}
              title="No briefings yet"
              body="Research a company or person above and it will show up here, ready to reopen before your next meeting."
            />
          ) : (
            <div className="grid gap-2.5 px-4 pb-4 sm:grid-cols-2">
              {history.slice(0, 4).map((h) => (
                <button
                  key={h.id}
                  type="button"
                  onClick={() => onOpenEntry(h)}
                  className="group rounded-xl border border-line bg-surface-2 p-3.5 text-left transition-colors hover:border-accent/40"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-md bg-surface-3 text-[10px] font-semibold text-muted">
                      {h.subject.slice(0, 2).toUpperCase()}
                    </span>
                    <span className="truncate text-[13px] font-semibold text-ink">{h.subject}</span>
                    <Badge tone="neutral" className="ml-auto shrink-0">
                      {h.type}
                    </Badge>
                  </div>
                  <div className="mt-1.5 line-clamp-2 text-[11.5px] leading-relaxed text-muted">
                    {h.headline}
                  </div>
                  <div className="mt-2 flex items-center gap-2 text-[10.5px] text-faint">
                    <span>{h.stats.articles} items</span>
                    <span>·</span>
                    <span>{h.stats.sources} outlets</span>
                    <span>·</span>
                    <span>{relativeTime(h.generatedAt)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* watchlist */}
      {watchlist.length > 0 && (
        <div className="mt-4">
          <Card>
            <SectionTitle
              eyebrow="Watchlist"
              title="Subjects you are tracking"
              count={watchlist.length}
              action={
                <Button size="sm" variant="ghost" onClick={onOpenWatchlist}>
                  Manage
                </Button>
              }
            />
            <div className="flex flex-wrap gap-2 px-4 pb-4">
              {watchlist.map((w) => (
                <button
                  key={w.subject}
                  type="button"
                  onClick={() => onResearch(w.subject, w.type, defaultDays)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface-2 px-2.5 py-1.5 text-[12px] text-muted transition-colors hover:border-accent/40 hover:text-ink"
                >
                  {w.type === 'company' ? <Building2 size={12} /> : <User size={12} />}
                  {w.subject}
                </button>
              ))}
            </div>
          </Card>
        </div>
      )}

      <p className="mt-6 text-center text-[11px] text-faint">
        Synthetic demo corpus — every name, figure and headline is fabricated. Configure a backend
        endpoint to research real subjects.
      </p>
    </div>
  )
}
