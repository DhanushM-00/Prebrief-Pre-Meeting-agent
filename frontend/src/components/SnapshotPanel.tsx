import { Building2, Globe, MapPin, User, Users } from 'lucide-react'
import { Badge, Card, SectionTitle } from './ui'
import type { BriefingResult } from '../types'

export function SnapshotPanel({ briefing }: { briefing: BriefingResult }) {
  const s = briefing.snapshot
  const isCompany = s.type === 'company'

  return (
    <div className="space-y-4">
      <Card className="overflow-hidden">
        <div className="border-b border-line bg-surface-2 px-5 py-4">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent-text ring-1 ring-accent/20">
              {isCompany ? <Building2 size={19} /> : <User size={19} />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-[18px] font-semibold tracking-tight text-ink">{s.name}</h1>
                <Badge tone="accent">{s.type}</Badge>
              </div>
              <div className="mt-0.5 truncate text-[12.5px] text-muted">{s.tagline}</div>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-faint">
                {s.website && (
                  <span className="inline-flex items-center gap-1">
                    <Globe size={10} />
                    {s.website.replace('.example.com', '.com')}
                  </span>
                )}
                {s.headquarters && (
                  <span className="inline-flex items-center gap-1">
                    <MapPin size={10} />
                    {s.headquarters}
                  </span>
                )}
                {s.sector && (
                  <span className="inline-flex items-center gap-1">
                    <Users size={10} />
                    {s.sector}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {s.tags.map((t) => (
              <span
                key={t}
                className="rounded-md border border-line bg-surface px-1.5 py-0.5 text-[10.5px] text-muted"
              >
                {t}
              </span>
            ))}
          </div>
        </div>

        <div className="grid gap-x-6 gap-y-3.5 px-5 py-4 sm:grid-cols-2">
          {s.facts.map((f) => (
            <div key={f.label} className="min-w-0">
              <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">
                {f.label}
              </div>
              <div className="mt-0.5 truncate text-[13px] font-medium text-ink">{f.value}</div>
              {f.hint && <div className="mt-0.5 truncate text-[10.5px] text-faint">{f.hint}</div>}
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle eyebrow="People" title="Who you are dealing with" count={s.keyPeople.length} />
        <div className="space-y-1 px-3 pb-4">
          {s.keyPeople.map((p) => (
            <div
              key={`${p.name}-${p.role}`}
              className="flex items-start gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-surface-2"
            >
              <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-3 text-[10.5px] font-semibold text-muted">
                {p.name
                  .split(' ')
                  .slice(0, 2)
                  .map((w) => w[0])
                  .join('')}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-[12.5px] font-medium text-ink">{p.name}</div>
                <div className="truncate text-[11.5px] text-muted">{p.role}</div>
                {p.note && <div className="mt-0.5 text-[10.5px] leading-relaxed text-faint">{p.note}</div>}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle eyebrow="Context" title="Keep on the radar" />
        <div className="flex flex-wrap gap-1.5 px-4 pb-4">
          {s.watchlist.map((w) => (
            <span
              key={w}
              className="rounded-md border border-line bg-surface-2 px-2 py-1 text-[11px] text-muted"
            >
              {w}
            </span>
          ))}
        </div>
      </Card>
    </div>
  )
}
