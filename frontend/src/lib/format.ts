import { differenceInCalendarDays, format, formatDistanceToNowStrict, isSameDay, parseISO } from 'date-fns'

/** Deterministic PRNG (mulberry32) so a given subject always yields the same briefing. */
export function makeRng(seed: string) {
  let h = 1779033703 ^ seed.length
  for (let i = 0; i < seed.length; i++) {
    h = Math.imul(h ^ seed.charCodeAt(i), 3432918353)
    h = (h << 13) | (h >>> 19)
  }
  let a = h >>> 0
  return function rng() {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export type Rng = () => number

export const pick = <T,>(rng: Rng, arr: readonly T[]): T => arr[Math.floor(rng() * arr.length) % arr.length]

export const pickMany = <T,>(rng: Rng, arr: readonly T[], count: number): T[] => {
  const pool = [...arr]
  const out: T[] = []
  const n = Math.min(count, pool.length)
  for (let i = 0; i < n; i++) out.push(pool.splice(Math.floor(rng() * pool.length), 1)[0])
  return out
}

export const int = (rng: Rng, min: number, max: number) => Math.floor(rng() * (max - min + 1)) + min
export const float = (rng: Rng, min: number, max: number) => rng() * (max - min) + min
export const chance = (rng: Rng, p: number) => rng() < p
export const slug = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')

/* ---------------- dates ---------------- */

export const fmtDate = (iso: string) => format(parseISO(iso), 'd MMM yyyy')
export const fmtShortDate = (iso: string) => format(parseISO(iso), 'd MMM')
export const fmtDateTime = (iso: string) => format(parseISO(iso), 'd MMM yyyy, HH:mm')

export const relativeTime = (iso: string) => {
  const diff = differenceInCalendarDays(new Date(), parseISO(iso))
  if (diff <= 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  if (diff < 7) return `${diff} days ago`
  if (diff < 30) return `${diff} days ago`
  return fmtDate(iso)
}

export const daysAgoIso = (days: number, hour = 9, minute = 30) => {
  const d = new Date()
  d.setDate(d.getDate() - days)
  d.setHours(hour, minute, 0, 0)
  return d.toISOString()
}

export const daysBetween = (a: string, b: string) =>
  Math.abs(differenceInCalendarDays(parseISO(a), parseISO(b)))

export const isToday = (iso: string) => isSameDay(parseISO(iso), new Date())

export const relativeLabel = (iso: string) => {
  const d = differenceInCalendarDays(new Date(), parseISO(iso))
  if (d <= 0) return 'Today'
  if (d === 1) return 'Yesterday'
  if (d < 7) return `${d}d ago`
  return `${d}d ago`
}

export function formatDistance(iso: string) {
  try {
    return formatDistanceToNowStrict(parseISO(iso), { addSuffix: true })
  } catch {
    return iso
  }
}
