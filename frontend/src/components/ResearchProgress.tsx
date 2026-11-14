import { Check, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'
import { RESEARCH_STAGES } from '../lib/api'

export function ResearchProgress({
  currentIndex,
  done,
  subject,
}: {
  currentIndex: number
  done: boolean
  subject: string
}) {
  return (
    <div className="mx-auto w-full max-w-lg px-1">
      <div className="mb-6 text-center">
        <div className="font-display text-[26px] leading-tight text-ink">
          Researching <span className="text-accent-text">{subject}</span>
        </div>
        <div className="mt-1 text-[12.5px] text-muted">
          {done ? 'Briefing assembled' : 'Scanning coverage, filings and press'}
        </div>
      </div>

      <div className="rounded-xl border border-line bg-surface shadow-card">
        {RESEARCH_STAGES.map((stage, i) => {
          const state = i < currentIndex ? 'done' : i === currentIndex ? 'active' : 'todo'
          return (
            <div
              key={stage.id}
              className={clsx(
                'flex items-start gap-3 px-4 py-3 transition-colors',
                i !== RESEARCH_STAGES.length - 1 && 'border-b border-line',
                state === 'todo' && 'opacity-45',
              )}
            >
              <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center">
                {state === 'done' ? (
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-positive/15 text-positive">
                    <Check size={11} strokeWidth={3} />
                  </span>
                ) : state === 'active' ? (
                  <Loader2 size={16} className="animate-spin text-accent" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-faint" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div
                  className={clsx(
                    'text-[13px] font-medium',
                    state === 'active' ? 'text-ink' : 'text-muted',
                  )}
                >
                  {stage.label}
                </div>
                {state === 'active' && (
                  <div className="mt-0.5 text-[11.5px] leading-relaxed text-faint">{stage.detail}</div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <p className="mt-4 text-center text-[11px] leading-relaxed text-faint">
        {done
          ? 'Done. Opening your briefing.'
          : 'Coverage is restricted to the selected window — older items are indexed but excluded from the brief.'}
      </p>
    </div>
  )
}
