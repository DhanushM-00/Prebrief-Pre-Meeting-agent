import { useCallback, useEffect, useState } from 'react'
import type { HistoryEntry, BriefingResult } from '../types'

const KEY_HISTORY = 'prebrief.history.v1'
const KEY_WATCH = 'prebrief.watch.v1'
const KEY_SETTINGS = 'prebrief.settings.v1'

function read<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function write<T>(key: string, value: T) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* quota or private mode — non-fatal */
  }
}

export function useLocalState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => read(key, initial))
  useEffect(() => {
    write(key, value)
  }, [key, value])
  return [value, setValue] as const
}

/* ---------------- history ---------------- */
export interface HistoryState {
  entries: HistoryEntry[]
}

export function useHistory() {
  const [entries, setEntries] = useLocalState<HistoryEntry[]>(KEY_HISTORY, [])

  const add = useCallback(
    (result: BriefingResult) => {
      setEntries((prev) => {
        const entry: HistoryEntry = {
          id: result.id,
          subject: result.subject,
          type: result.type,
          generatedAt: result.generatedAt,
          headline:
            result.news.find((n) => n.isKey)?.headline ??
            result.news.find((n) => n.inWindow)?.headline ??
            'No in-window coverage',
          stats: result.stats,
          result,
        }
        const without = prev.filter((e) => e.subject.toLowerCase() !== result.subject.toLowerCase())
        return [entry, ...without].slice(0, 40)
      })
    },
    [setEntries],
  )

  const remove = useCallback(
    (id: string) => setEntries((prev) => prev.filter((e) => e.id !== id)),
    [setEntries],
  )

  const clear = useCallback(() => setEntries([]), [setEntries])

  return { entries, add, remove, clear }
}

/* ---------------- watchlist ---------------- */
export interface WatchItem {
  subject: string
  type: 'company' | 'person'
  addedAt: string
  lastBriefedAt?: string
}

export function useWatchlist() {
  const [items, setItems] = useLocalState<WatchItem[]>(KEY_WATCH, [])

  const toggle = useCallback(
    (subject: string, type: 'company' | 'person') => {
      setItems((prev) => {
        const exists = prev.some((i) => i.subject.toLowerCase() === subject.toLowerCase())
        if (exists) return prev.filter((i) => i.subject.toLowerCase() !== subject.toLowerCase())
        return [{ subject, type, addedAt: new Date().toISOString() }, ...prev]
      })
    },
    [setItems],
  )

  const has = useCallback(
    (subject: string) => items.some((i) => i.subject.toLowerCase() === subject.toLowerCase()),
    [items],
  )

  const remove = useCallback(
    (subject: string) =>
      setItems((prev) => prev.filter((i) => i.subject.toLowerCase() !== subject.toLowerCase())),
    [setItems],
  )

  return { items, toggle, has, remove }
}

/* ---------------- settings ---------------- */
export interface Settings {
  theme: 'dark' | 'light'
  /** Window pre-selected on the search bar. */
  defaultDays: number
  /** Subject type pre-selected on the search bar. */
  defaultType: 'auto' | 'company' | 'person'
}

export const DEFAULT_SETTINGS: Settings = {
  theme: 'dark',
  defaultDays: 30,
  defaultType: 'auto',
}

export function useSettings() {
  const [settings, setSettings] = useLocalState<Settings>(KEY_SETTINGS, DEFAULT_SETTINGS)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', settings.theme === 'dark')
    document.documentElement.classList.toggle('light', settings.theme === 'light')
  }, [settings.theme])

  const update = useCallback(
    (patch: Partial<Settings>) => setSettings((prev) => ({ ...prev, ...patch })),
    [setSettings],
  )

  return { settings, update }
}
