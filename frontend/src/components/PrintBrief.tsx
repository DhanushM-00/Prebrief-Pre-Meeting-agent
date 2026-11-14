import { CATEGORY_LABEL } from '../lib/templates'
import { fmtDate, fmtDateTime, fmtShortDate } from '../lib/format'
import type { BriefingResult, MeetingContext } from '../types'

/**
 * A self-contained, print-optimised document for the brief.
 *
 * The interactive UI is hidden in print and this document takes its place —
 * styled with explicit light colours so it prints correctly regardless of
 * the active theme (printers rarely render background fills).
 */
export function PrintBrief({
  briefing,
  meeting,
}: {
  briefing: BriefingResult
  meeting?: MeetingContext
}) {
  const s = briefing.snapshot
  const inWin = briefing.news.filter((n) => n.inWindow)
  const key = inWin.filter((n) => n.isKey)
  const lead = key.length ? key : inWin.filter((n) => n.impact === 3).slice(0, 5)

  return (
    <article className="hidden print:block print:bg-white print:text-black">
      <header className="border-b-2 border-black pb-2">
        <div className="text-[9pt] font-bold uppercase tracking-[0.2em] text-neutral-500">
          Pre-meeting brief
        </div>
        <h1 className="mt-1 text-[20pt] font-bold leading-tight">{s.name}</h1>
        <div className="mt-0.5 text-[10pt] text-neutral-600">{s.tagline}</div>

        <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-0.5 text-[8.5pt] text-neutral-700">
          <div>
            <span className="text-neutral-500">Subject type: </span>
            {s.type}
          </div>
          <div>
            <span className="text-neutral-500">Research window: </span>
            last {briefing.windowDays} days ({fmtDate(briefing.windowStart)} →{' '}
            {fmtDate(briefing.windowEnd)})
          </div>
          <div>
            <span className="text-neutral-500">Coverage: </span>
            {briefing.stats.articles} items · {briefing.stats.sources} outlets ·{' '}
            {briefing.stats.categoriesCovered} categories · {briefing.stats.daysCovered} active days
          </div>
          <div>
            <span className="text-neutral-500">Net tone: </span>
            {briefing.stats.avgSentiment > 0 ? '+' : ''}
            {briefing.stats.avgSentiment.toFixed(2)} (
            {briefing.stats.avgSentiment > 0.15
              ? 'net positive'
              : briefing.stats.avgSentiment < -0.15
                ? 'net negative'
                : 'balanced'}
            )
          </div>
          {meeting?.title && (
            <div className="col-span-2">
              <span className="text-neutral-500">Meeting: </span>
              {meeting.title}
              {meeting.date ? ` · ${meeting.date}` : ''}
              {meeting.attendees.length ? ` · ${meeting.attendees.join(', ')}` : ''}
            </div>
          )}
          {meeting?.note && (
            <div className="col-span-2">
              <span className="text-neutral-500">Context: </span>
              {meeting.note}
            </div>
          )}
        </div>
      </header>

      <Section title="Snapshot">
        <table className="w-full border-collapse text-[8.5pt]">
          <tbody>
            {s.facts.map((f) => (
              <tr key={f.label} className="border-b border-neutral-200">
                <td className="w-[26%] py-1 pr-3 align-top font-semibold uppercase tracking-wide text-neutral-500">
                  {f.label}
                </td>
                <td className="py-1 align-top">{f.value}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {s.keyPeople.length > 0 && (
          <div className="mt-2 text-[8.5pt]">
            <span className="font-semibold uppercase tracking-wide text-neutral-500">People: </span>
            {s.keyPeople.map((p) => `${p.name} (${p.role})`).join('  ·  ')}
          </div>
        )}
      </Section>

      <Section title="Signals">
        {briefing.signals.map((sig) => (
          <div key={sig.id} className="mb-1.5 text-[8.5pt] leading-snug">
            <span className="font-bold uppercase">
              {sig.kind === 'risk' ? '⚠ Risk' : sig.kind === 'opportunity' ? '✦ Opportunity' : '◎ Watch'}
            </span>
            <span className="font-semibold"> — {sig.title}.</span> {sig.detail}
          </div>
        ))}
      </Section>

      {lead.length > 0 && (
        <Section title="Headline items">
          {lead.map((n) => (
            <div key={n.id} className="mb-2 break-inside-avoid text-[8.5pt] leading-snug">
              <div className="font-bold">{n.headline}</div>
              <div className="text-neutral-500">
                {n.source} · {fmtDate(n.publishedAt)} · {CATEGORY_LABEL[n.category]} · {n.sentiment}
              </div>
              <div className="mt-0.5">{n.summary}</div>
              <div className="mt-0.5">
                <span className="font-semibold">Why it matters: </span>
                {n.whyItMatters}
              </div>
            </div>
          ))}
        </Section>
      )}

      <Section title={`All coverage — last ${briefing.windowDays} days (${inWin.length} items)`}>
        <table className="w-full border-collapse text-[8pt]">
          <thead>
            <tr className="border-b border-neutral-400 text-left">
              <th className="w-[12%] py-1 pr-2 font-semibold uppercase tracking-wide text-neutral-500">
                Date
              </th>
              <th className="py-1 pr-2 font-semibold uppercase tracking-wide text-neutral-500">
                Headline
              </th>
              <th className="w-[16%] py-1 pr-2 font-semibold uppercase tracking-wide text-neutral-500">
                Source
              </th>
              <th className="w-[14%] py-1 font-semibold uppercase tracking-wide text-neutral-500">
                Category
              </th>
            </tr>
          </thead>
          <tbody>
            {inWin.map((n) => (
              <tr key={n.id} className="border-b border-neutral-200 align-top">
                <td className="py-1 pr-2 whitespace-nowrap text-neutral-500">
                  {fmtShortDate(n.publishedAt)}
                </td>
                <td className="py-1 pr-2">
                  {n.headline}
                  <span className="text-neutral-500"> ({n.sentiment})</span>
                </td>
                <td className="py-1 pr-2">{n.source}</td>
                <td className="py-1">{CATEGORY_LABEL[n.category]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Talking points">
        {briefing.talkingPoints.map((tp, i) => (
          <div key={tp.id} className="mb-1.5 break-inside-avoid text-[8.5pt] leading-snug">
            <div>
              <span className="font-bold">{i + 1}. {tp.text}</span>
            </div>
            <div className="italic">“{tp.opener}”</div>
            <div>
              <span className="font-semibold">Why: </span>
              {tp.rationale}
            </div>
          </div>
        ))}
      </Section>

      <Section title="Questions to ask">
        {briefing.questions.map((q, i) => (
          <div key={q.id} className="mb-1.5 break-inside-avoid text-[8.5pt] leading-snug">
            <div>
              <span className="font-bold">{i + 1}. {q.question}</span>{' '}
              <span className="text-neutral-500">({q.category})</span>
            </div>
            <div>
              <span className="font-semibold">Why: </span>
              {q.why}
            </div>
          </div>
        ))}
      </Section>

      <footer className="mt-4 border-t border-neutral-300 pt-1.5 text-[7.5pt] text-neutral-500">
        Prepared {fmtDateTime(briefing.generatedAt)} · PreBrief
        {briefing.synthetic ? ' · synthetic demo corpus — not real intelligence' : ''}
      </footer>
    </article>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-3.5">
      <h2 className="mb-1 border-b border-neutral-300 pb-0.5 text-[9pt] font-bold uppercase tracking-[0.14em]">
        {title}
      </h2>
      {children}
    </section>
  )
}
