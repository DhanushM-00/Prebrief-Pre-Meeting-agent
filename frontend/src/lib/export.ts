import type { BriefingResult, MeetingContext } from '../types'
import { CATEGORY_LABEL } from './templates'
import { fmtDate, fmtDateTime, fmtShortDate } from './format'

export function briefingToMarkdown(b: BriefingResult, meeting?: MeetingContext): string {
  const s = b.snapshot
  const inWin = b.news.filter((n) => n.inWindow)
  const key = inWin.filter((n) => n.isKey)

  const lines: string[] = []

  lines.push(`# Pre-Meeting Brief — ${s.name}`)
  lines.push('')
  lines.push(`**Subject type:** ${s.type}  |  **Research window:** last ${b.windowDays} days (${fmtDate(b.windowStart)} → ${fmtDate(b.windowEnd)})  |  **Prepared:** ${fmtDateTime(b.generatedAt)}`)
  if (meeting) {
    lines.push(`**Meeting:** ${meeting.title}${meeting.date ? ` · ${meeting.date}` : ''}${meeting.attendees.length ? ` · with ${meeting.attendees.join(', ')}` : ''}`)
  }
  lines.push('')
  lines.push(`> ${s.tagline}`)
  lines.push('')

  lines.push('## Snapshot')
  lines.push('')
  lines.push('| | |')
  lines.push('|---|---|')
  s.facts.forEach((f) => lines.push(`| **${f.label}** | ${f.value} |`))
  lines.push('')

  if (s.keyPeople.length) {
    lines.push('### Key people')
    lines.push('')
    s.keyPeople.forEach((p) => lines.push(`- **${p.name}** — ${p.role}${p.note ? ` · ${p.note}` : ''}`))
    lines.push('')
  }

  lines.push('## Signals')
  lines.push('')
  b.signals.forEach((sig) => {
    const tag = sig.kind === 'risk' ? '⚠️ Risk' : sig.kind === 'opportunity' ? '✦ Opportunity' : '◎ Watch'
    lines.push(`- **${tag} — ${sig.title}.** ${sig.detail}`)
  })
  lines.push('')

  if (key.length) {
    lines.push('## Headline items')
    lines.push('')
    key.forEach((n) => {
      lines.push(`### ${n.headline}`)
      lines.push(`*${n.source} · ${fmtDate(n.publishedAt)} · ${CATEGORY_LABEL[n.category]} · ${n.sentiment}*`)
      lines.push('')
      lines.push(n.summary)
      lines.push('')
      lines.push(`**Why it matters:** ${n.whyItMatters}`)
      lines.push('')
    })
  }

  lines.push(`## All coverage — last ${b.windowDays} days (${inWin.length} items)`)
  lines.push('')
  lines.push('| Date | Headline | Source | Category | Sentiment |')
  lines.push('|---|---|---|---|---|')
  inWin.forEach((n) => {
    lines.push(`| ${fmtShortDate(n.publishedAt)} | ${n.headline} | ${n.source} | ${CATEGORY_LABEL[n.category]} | ${n.sentiment} |`)
  })
  lines.push('')

  lines.push('## Talking points')
  lines.push('')
  b.talkingPoints.forEach((tp, i) => {
    lines.push(`${i + 1}. **${tp.text}**`)
    lines.push(`   - Opener: ${tp.opener}`)
    lines.push(`   - Why: ${tp.rationale}`)
  })
  lines.push('')

  lines.push('## Questions to ask')
  lines.push('')
  b.questions.forEach((q, i) => {
    lines.push(`${i + 1}. **${q.question}**`)
    lines.push(`   - Why: ${q.why}`)
  })
  lines.push('')

  lines.push('## Sources')
  lines.push('')
  b.sources.forEach((src) => {
    lines.push(`- ${src.name} — ${src.headline} (${fmtDate(src.publishedAt)})`)
  })
  lines.push('')
  lines.push('---')
  lines.push(
    `_Coverage: ${b.stats.articles} in-window items · ${b.stats.sources} outlets · ${b.stats.categoriesCovered} categories · ${b.stats.daysCovered} active days._`,
  )
  if (b.synthetic) {
    lines.push('')
    lines.push('_Synthetic demo corpus — not real intelligence._')
  }
  return lines.join('\n')
}

/**
 * A one-screen summary sized for a phone or a glance before walking in.
 * Deliberately short — the full brief is a document, this is a prompt.
 */
export function cheatSheet(b: BriefingResult, meeting?: MeetingContext): string {
  const s = b.snapshot
  const inWin = b.news.filter((n) => n.inWindow)
  const key = inWin.filter((n) => n.isKey).slice(0, 3)
  const topFacts = s.facts.slice(0, 4).map((f) => `${f.label}: ${f.value}`)
  const tone =
    b.stats.avgSentiment > 0.15
      ? 'net positive'
      : b.stats.avgSentiment < -0.15
        ? 'net negative'
        : 'balanced'

  const lines: string[] = []
  lines.push(`PRE-MEETING BRIEF — ${s.name}`)
  if (meeting?.title) lines.push(`${meeting.title}${meeting.date ? ` · ${meeting.date}` : ''}`)
  lines.push(`last ${b.windowDays} days · ${b.stats.articles} items · ${b.stats.sources} outlets · tone ${tone}`)
  lines.push('')
  if (topFacts.length) {
    lines.push(topFacts.join('  |  '))
    lines.push('')
  }
  if (key.length) {
    lines.push('HEADLINES')
    key.forEach((n) => lines.push(`• ${n.headline} (${n.source}, ${fmtShortDate(n.publishedAt)})`))
    lines.push('')
  }
  if (b.signals.length) {
    lines.push('SIGNALS')
    b.signals.forEach((sig) => lines.push(`• ${sig.kind.toUpperCase()}: ${sig.title}`))
    lines.push('')
  }
  if (b.talkingPoints.length) {
    lines.push('OPEN WITH')
    b.talkingPoints.slice(0, 3).forEach((tp, i) => lines.push(`${i + 1}. ${tp.opener}`))
    lines.push('')
  }
  if (b.questions.length) {
    lines.push('ASK')
    b.questions.slice(0, 3).forEach((q, i) => lines.push(`${i + 1}. ${q.question}`))
  }
  if (b.synthetic) lines.push('\n(synthetic demo data — not real intelligence)')
  return lines.join('\n')
}

export function downloadFile(filename: string, content: string, mime = 'text/markdown') {  const blob = new Blob([content], { type: `${mime};charset=utf-8` })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      return ok
    } catch {
      return false
    }
  }
}

export function printBriefing() {
  window.print()
}

export function slugFile(name: string) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
    .slice(0, 60)
}
