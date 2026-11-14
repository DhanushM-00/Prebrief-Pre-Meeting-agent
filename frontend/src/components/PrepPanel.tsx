import { useState } from 'react'
import { Copy, Check, MessageCircleQuestion, Quote } from 'lucide-react'
import { clsx } from 'clsx'
import { Badge, Button, Card, SectionTitle } from './ui'
import { copyText } from '../lib/export'
import type { OpenQuestion, TalkingPoint } from '../types'

export function TalkingPointsPanel({
  points,
  newsById,
  onEvidence,
}: {
  points: TalkingPoint[]
  newsById: Map<string, { headline: string; source: string }>
  onEvidence?: (id: string) => void
}) {
  return (
    <Card>
      <SectionTitle
        eyebrow="Say"
        title="Talking points, with an opener for each"
        count={points.length}
      />
      <div className="space-y-2.5 px-4 pb-4">
        {points.map((tp, i) => (
          <div key={tp.id} className="rounded-xl border border-line bg-surface-2 p-3.5">
            <div className="flex items-start gap-3">
              <span className="tabular mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-accent-soft text-[11px] font-semibold text-accent-text">
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-start gap-1.5 text-[13.5px] font-semibold leading-snug tracking-tight text-ink">
                  <Quote size={13} className="mt-0.5 shrink-0 text-faint" />
                  {tp.text}
                </div>

                <div className="mt-2 rounded-lg border border-line bg-surface px-3 py-2">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">
                    Opener
                  </div>
                  <div className="mt-1 text-[12.5px] italic leading-relaxed text-muted">{tp.opener}</div>
                </div>

                <p className="mt-2 text-[12px] leading-relaxed text-muted">{tp.rationale}</p>

                {tp.evidence.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {tp.evidence.map((id) => {
                      const ev = newsById.get(id)
                      if (!ev) return null
                      return (
                        <button
                          key={id}
                          type="button"
                          onClick={() => onEvidence?.(id)}
                          className="max-w-full truncate rounded-md border border-line bg-surface px-2 py-1 text-[11px] text-faint transition-colors hover:border-accent/40 hover:text-ink"
                        >
                          ↳ {ev.headline}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

export function QuestionsPanel({
  questions,
  newsById,
  onEvidence,
}: {
  questions: OpenQuestion[]
  newsById: Map<string, { headline: string; source: string }>
  onEvidence?: (id: string) => void
}) {
  return (
    <Card>
      <SectionTitle
        eyebrow="Ask"
        title="Questions worth the room"
        count={questions.length}
        action={
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              copyText(
                questions
                  .map((q, i) => `${i + 1}. ${q.question}\n   Why: ${q.why}`)
                  .join('\n\n'),
              )
            }
          >
            <Copy size={12} />
            Copy
          </Button>
        }
      />
      <div className="space-y-2 px-4 pb-4">
        {questions.map((q, i) => (
          <QuestionRow key={q.id} q={q} index={i} newsById={newsById} onEvidence={onEvidence} />
        ))}
      </div>
    </Card>
  )
}

function QuestionRow({
  q,
  index,
  newsById,
  onEvidence,
}: {
  q: OpenQuestion
  index: number
  newsById: Map<string, { headline: string; source: string }>
  onEvidence?: (id: string) => void
}) {
  const [copied, setCopied] = useState(false)
  const [open, setOpen] = useState(false)

  const catTone =
    q.category === 'strategy'
      ? 'accent'
      : q.category === 'business'
        ? 'info'
        : q.category === 'product'
          ? 'positive'
          : q.category === 'team'
            ? 'warning'
            : 'neutral'

  return (
    <div className="rounded-xl border border-line bg-surface-2 p-3.5">
      <div className="flex items-start gap-3">
        <span className="tabular mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-surface text-[11px] font-semibold text-muted ring-1 ring-line">
          {index + 1}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={catTone}>{q.category}</Badge>
          </div>
          <div className="mt-1.5 flex items-start gap-1.5 text-[13.5px] font-medium leading-snug tracking-tight text-ink">
            <MessageCircleQuestion size={14} className="mt-0.5 shrink-0 text-faint" />
            {q.question}
          </div>

          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="mt-1.5 text-[11.5px] font-medium text-accent-text hover:opacity-75"
          >
            {open ? 'Hide rationale' : 'Why this works'}
          </button>

          {open && (
            <div className="animate-rise mt-1.5 text-[12px] leading-relaxed text-muted">{q.why}</div>
          )}

          {q.evidence.length > 0 && onEvidence && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {q.evidence.map((id) => {
                const ev = newsById.get(id)
                if (!ev) return null
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => onEvidence(id)}
                    className="max-w-full truncate rounded-md border border-line bg-surface px-2 py-1 text-[11px] text-faint transition-colors hover:border-accent/40 hover:text-ink"
                  >
                    ↳ {ev.headline}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <Button
          size="sm"
          variant="ghost"
          aria-label="Copy question"
          onClick={async () => {
            const ok = await copyText(q.question)
            if (ok) {
              setCopied(true)
              setTimeout(() => setCopied(false), 1400)
            }
          }}
          className={clsx('shrink-0')}
        >
          {copied ? <Check size={12} className="text-positive" /> : <Copy size={12} />}
        </Button>
      </div>
    </div>
  )
}
