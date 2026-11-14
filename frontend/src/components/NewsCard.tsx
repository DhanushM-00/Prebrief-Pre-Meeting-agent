import { useState } from 'react'
import { ArrowUpRight, ChevronDown, ChevronUp, ExternalLink, Sparkles } from 'lucide-react'
import { clsx } from 'clsx'
import { Badge, Dot, type Tone } from './ui'
import { CATEGORY_LABEL } from '../lib/templates'
import { relativeLabel, fmtDateTime } from '../lib/format'
import type { NewsItem } from '../types'

const SENTIMENT_TONE: Record<string, Tone> = {
  positive: 'positive',
  negative: 'negative',
  neutral: 'neutral',
}

export function NewsCard({
  item,
  referenced = false,
  onReferenceClick,
}: {
  item: NewsItem
  referenced?: boolean
  onReferenceClick?: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const dim = !item.inWindow

  const [thumbFailed, setThumbFailed] = useState(false)

  return (
    <article
      id={`news-${item.id}`}
      className={clsx(
        'group relative rounded-xl border bg-surface p-4 transition-all duration-200',
        referenced
          ? 'border-accent/45 shadow-[0_0_0_1px_var(--accent-soft)]'
          : 'border-line hover:border-line-strong',
        dim && 'opacity-60',
      )}
    >
      <div className="flex items-start gap-3">
        <div className="mt-1.5 shrink-0">
          <Dot tone={SENTIMENT_TONE[item.sentiment]} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
            <Badge tone="neutral">{CATEGORY_LABEL[item.category]}</Badge>
            <Badge tone={SENTIMENT_TONE[item.sentiment]}>{item.sentiment}</Badge>
            {item.impact === 3 && <Badge tone="warning">High impact</Badge>}
            {item.isKey && (
              <Badge tone="accent" icon={<Sparkles size={9} />}>
                Key item
              </Badge>
            )}
            {dim && <Badge tone="neutral">Outside window</Badge>}
            {item.isInterpretation && (
              <Badge tone="neutral">Heuristic scores</Badge>
            )}
          </div>

          <div className="mt-2 flex gap-3">
            {item.imageUrl && !thumbFailed && (
              <a
                href={item.sourceUrl || item.imageUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="relative h-16 w-24 shrink-0 overflow-hidden rounded-lg border border-line bg-surface-3"
                title="Article image"
              >
                <img
                  src={item.imageUrl}
                  alt=""
                  loading="lazy"
                  className="h-full w-full object-cover"
                  onError={() => setThumbFailed(true)}
                />
              </a>
            )}
            <div className="min-w-0 flex-1">
              <h3 className="text-[14.5px] font-semibold leading-snug tracking-tight text-ink">
                {item.headline}
              </h3>
              <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">{item.summary}</p>
            </div>
          </div>


          <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-faint">
            {item.sourceUrl ? (
              <a
                href={item.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-medium text-muted underline decoration-line-strong underline-offset-2 transition-colors hover:text-ink hover:decoration-accent"
              >
                {item.source}
                <ExternalLink size={10} />
              </a>
            ) : (
              <span className="font-medium text-muted">{item.source}</span>
            )}
            <span title={fmtDateTime(item.publishedAt)}>{relativeLabel(item.publishedAt)}</span>
            {item.entities.slice(0, 3).map((e) => (
              <span key={e} className="rounded border border-line px-1.5 py-px">
                {e}
              </span>
            ))}
          </div>

          <div className="mt-2.5 flex items-center gap-2">
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              className="inline-flex items-center gap-1 text-[11.5px] font-medium text-accent-text transition-opacity hover:opacity-75"
            >
              {expanded ? 'Hide' : 'Why it matters'}
              {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>
            {onReferenceClick && (
              <button
                type="button"
                onClick={() => onReferenceClick(item.id)}
                className="inline-flex items-center gap-1 text-[11.5px] font-medium text-faint transition-colors hover:text-ink"
              >
                Focus in timeline
                <ArrowUpRight size={11} />
              </button>
            )}
          </div>

          {expanded && (
            <div className="animate-rise mt-2 rounded-lg border border-line bg-surface-2 px-3 py-2.5 text-[12px] leading-relaxed text-muted">
              {item.whyItMatters}
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
