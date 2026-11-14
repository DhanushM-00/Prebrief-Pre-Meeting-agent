import { AlertTriangle, CircleDot, Lightbulb } from 'lucide-react'
import { clsx } from 'clsx'
import { Badge, Card, SectionTitle } from './ui'
import type { Signal } from '../types'

const KIND_META = {
  risk: {
    label: 'Risk',
    icon: AlertTriangle,
    tone: 'negative' as const,
    ring: 'border-negative/25 bg-negative-soft',
    iconColor: 'text-negative',
  },
  opportunity: {
    label: 'Opportunity',
    icon: Lightbulb,
    tone: 'positive' as const,
    ring: 'border-positive/25 bg-positive-soft',
    iconColor: 'text-positive',
  },
  watch: {
    label: 'Watch',
    icon: CircleDot,
    tone: 'warning' as const,
    ring: 'border-warning/25 bg-warning-soft',
    iconColor: 'text-warning',
  },
}

export function SignalsPanel({
  signals,
  newsById,
  onEvidence,
}: {
  signals: Signal[]
  newsById: Map<string, { headline: string; source: string }>
  onEvidence?: (id: string) => void
}) {
  return (
    <Card>
      <SectionTitle
        eyebrow="Read"
        title="Signals worth carrying into the room"
        count={signals.length}
      />
      <div className="space-y-2.5 px-4 pb-4">
        {signals.map((sig) => {
          const meta = KIND_META[sig.kind]
          const Icon = meta.icon
          return (
            <div
              key={sig.id}
              className={clsx('rounded-xl border p-3.5', meta.ring)}
            >
              <div className="flex items-start gap-3">
                <Icon size={16} className={clsx('mt-0.5 shrink-0', meta.iconColor)} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={meta.tone}>{meta.label}</Badge>
                    <span className="text-[13.5px] font-semibold tracking-tight text-ink">
                      {sig.title}
                    </span>
                  </div>
                  <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">{sig.detail}</p>

                  {sig.evidence.length > 0 && (
                    <div className="mt-2.5 flex flex-wrap gap-1.5">
                      {sig.evidence.map((id) => {
                        const ev = newsById.get(id)
                        if (!ev) return null
                        return (
                          <button
                            key={id}
                            type="button"
                            onClick={() => onEvidence?.(id)}
                            className="max-w-full truncate rounded-md border border-line bg-surface px-2 py-1 text-[11px] text-muted transition-colors hover:border-accent/40 hover:text-ink"
                          >
                            {ev.headline}
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
