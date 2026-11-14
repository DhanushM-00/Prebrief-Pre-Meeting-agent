import type { SubjectType, SubjectTypeInput } from '../types'

/**
 * Briefs are shareable by link. The hash carries the research request, not the
 * result — opening the link re-runs the research so the reader always gets
 * current coverage rather than a stale snapshot.
 *
 *   #/brief/<subject>?d=30&t=auto
 */
const DAY_OPTIONS = [7, 14, 30, 60, 90]

export function briefHash(
  subject: string,
  type: SubjectTypeInput = 'auto',
  days = 30,
): string {
  const params = new URLSearchParams({ d: String(days), t: type })
  return `#/brief/${encodeURIComponent(subject)}?${params.toString()}`
}

export function briefUrl(
  subject: string,
  type: SubjectTypeInput = 'auto',
  days = 30,
): string {
  if (typeof window === 'undefined') return ''
  const { origin, pathname } = window.location
  return `${origin}${pathname}${briefHash(subject, type, days)}`
}

export interface ParsedBriefLink {
  subject: string
  type: SubjectTypeInput
  days: number
}

export function parseBriefHash(hash: string): ParsedBriefLink | null {
  if (!hash) return null
  const match = hash.match(/^#\/brief\/(.+?)(?:\?(.*))?$/)
  if (!match) return null

  let subject: string
  try {
    subject = decodeURIComponent(match[1])
  } catch {
    subject = match[1]
  }
  if (!subject.trim()) return null

  const params = new URLSearchParams(match[2] ?? '')
  const rawDays = Number(params.get('d'))
  const days = DAY_OPTIONS.includes(rawDays) ? rawDays : 30
  const rawType = params.get('t')
  const type: SubjectTypeInput =
    rawType === 'company' || rawType === 'person' ? (rawType as SubjectType) : 'auto'

  return { subject, type, days }
}

/** Push the current brief into the address bar without adding a history entry. */
export function writeBriefHash(
  subject: string,
  type: SubjectTypeInput,
  days: number,
): void {
  if (typeof window === 'undefined') return
  const next = briefHash(subject, type, days)
  if (window.location.hash === next) return
  window.history.replaceState(null, '', next)
}

export function clearBriefHash(): void {
  if (typeof window === 'undefined') return
  if (!window.location.hash.startsWith('#/brief/')) return
  window.history.replaceState(null, '', window.location.pathname + window.location.search)
}
