import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Clock,
  FileText,
  GitCompare,
  History as HistoryIcon,
  MessageSquare,
  Moon,
  Radar,
  Settings2,
  Sun,
  X,
} from 'lucide-react'
import { clsx } from 'clsx'
import { HomeView } from './components/HomeView'
import { BriefingView } from './components/BriefingView'
import { HistoryView, WatchlistView } from './components/LibraryViews'
import { CompareView } from './components/CompareView'
import { ResearchProgress } from './components/ResearchProgress'
import { AgentChat } from './components/AgentChat'
import { MeetingSetup } from './components/MeetingSetup'
import { SettingsPanel } from './components/SettingsPanel'
import { DocumentsView } from './components/DocumentsView'
import { OnePageBriefView } from './components/OnePageBriefView'
import { Button } from './components/ui'
import { runBriefing, RESEARCH_STAGES } from './lib/api'
import { useHistory, useSettings, useWatchlist } from './lib/store'
import { clearBriefHash, parseBriefHash, writeBriefHash } from './lib/link'
import type { BriefingRequest, BriefingResult, HistoryEntry, MeetingContext } from './types'

type View = 'home' | 'briefing' | 'history' | 'watchlist' | 'compare' | 'documents' | 'onepager'

const EMPTY_MEETING: MeetingContext = { title: '', date: '', attendees: [], note: '' }

export default function App() {
  const [view, setView] = useState<View>('home')

  const [briefing, setBriefing] = useState<BriefingResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [stageIndex, setStageIndex] = useState(0)
  const [pendingSubject, setPendingSubject] = useState('')
  const [chatOpen, setChatOpen] = useState(false)
  const [meeting, setMeeting] = useState<MeetingContext>(EMPTY_MEETING)
  const [showMeeting, setShowMeeting] = useState(false)
  const [compareLeft, setCompareLeft] = useState<string | null>(null)
  const [compareRight, setCompareRight] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)

  const { settings, update } = useSettings()
  const { entries, add, remove, clear } = useHistory()
  const { items: watchItems, toggle: toggleWatch, has: isWatched } = useWatchlist()
  const abortRef = useRef<AbortController | null>(null)

  /* ---------- research ---------- */
  const research = useCallback(
    async (
      subject: string,
      type: BriefingRequest['type'],
      days: number,
      focus?: string,
      meetingAt?: string,
    ) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      setLoading(true)
      setPendingSubject(subject)
      setStageIndex(0)
      setError(null)
      setView('home')

      try {
        let documentIds: string[] | undefined
        let mergedFocus = focus
        try {
          const raw = sessionStorage.getItem('prebrief.documentIds')
          if (raw) documentIds = JSON.parse(raw) as string[]
          const note = sessionStorage.getItem('prebrief.documentNote')
          if (note) mergedFocus = [focus, note].filter(Boolean).join('\n')
          sessionStorage.removeItem('prebrief.documentIds')
          sessionStorage.removeItem('prebrief.documentNote')
        } catch {
          /* ignore */
        }
        const result = await runBriefing(
          { subject, type, days, focus: mergedFocus, documentIds, meetingAt },
          {
            signal: controller.signal,
            onStage: (_s, i) => setStageIndex(i),
          },
        )
        if (controller.signal.aborted) return
        setBriefing(result)
        add(result)
        writeBriefHash(result.subject, result.type, result.windowDays)
        setView('briefing')
      } catch (err) {

        const message = (err as Error)?.message
        if (message !== 'aborted') {
          console.error(err)
          setError(
            message
              ? `Research failed for "${subject}": ${message}`
              : `Research failed for "${subject}". The agent did not respond.`,
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
          setPendingSubject('')
        }
      }
    },
    [add],
  )

  useEffect(() => () => abortRef.current?.abort(), [])

  // A shared link re-runs the research so the reader sees current coverage
  // rather than a stale snapshot. This handles both the initial load and a
  // hash change while the app is already open (pasting a colleague's link).
  const handledHash = useRef<string | null>(null)
  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash
      if (hash === handledHash.current) return
      const parsed = parseBriefHash(hash)
      if (!parsed) return
      handledHash.current = hash
      research(parsed.subject, parsed.type, parsed.days)
    }
    handleHash()
    window.addEventListener('hashchange', handleHash)
    return () => window.removeEventListener('hashchange', handleHash)
  }, [research])

  /* ---------- keyboard ---------- */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (e.key === '/') {
        e.preventDefault()
        document.querySelector<HTMLInputElement>('input[placeholder*="Company"]')?.focus()
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setView('home')
        setTimeout(
          () => document.querySelector<HTMLInputElement>('input[placeholder*="Company"]')?.focus(),
          60,
        )
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  const openEntry = (entry: HistoryEntry) => {
    setBriefing(entry.result)
    writeBriefHash(entry.subject, entry.result.type, entry.result.windowDays)
    setView('briefing')
  }

  /** Jump to Compare with two distinct briefings pre-selected. */
  /** Leaving a brief for a fresh search clears the shared link. */
  const startFresh = useCallback(() => {
    clearBriefHash()
    setBriefing(null)
    setView('home')
  }, [])

  const goCompare = useCallback(() => {
    if (entries.length >= 2) {
      const validL = entries.find((e) => e.id === compareLeft)?.id
      const validR = entries.find((e) => e.id === compareRight)?.id
      let l = validL
      let r = validR
      if (!l || !r || l === r) {
        l = l ?? entries[0].id
        r = entries.find((e) => e.id !== l)?.id ?? entries[1].id
      }
      setCompareLeft(l)
      setCompareRight(r)
    }
    setView('compare')
  }, [entries, compareLeft, compareRight])

  const nav = (
    <nav className="flex items-center gap-0.5">
      {[
        { id: 'home' as View, label: 'Brief', icon: <Radar size={13} /> },
        { id: 'onepager' as View, label: 'One-pager', icon: <FileText size={13} /> },
        { id: 'documents' as View, label: 'Documents', icon: <FileText size={13} /> },
        { id: 'history' as View, label: 'History', icon: <HistoryIcon size={13} /> },
        { id: 'watchlist' as View, label: 'Watchlist', icon: <Clock size={13} /> },
        { id: 'compare' as View, label: 'Compare', icon: <GitCompare size={13} /> },
      ].map((n) => (
        <button
          key={n.id}
          type="button"
          onClick={() => (n.id === 'compare' ? goCompare() : setView(n.id))}
          className={clsx(
            'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12.5px] font-medium transition-colors',
            view === n.id
              ? 'bg-surface-2 text-ink'
              : 'text-faint hover:bg-surface-2/60 hover:text-muted',
          )}
        >
          {n.icon}
          <span>{n.label}</span>
          {n.id === 'history' && entries.length > 0 && (
            <span className="tabular rounded bg-surface-3 px-1 text-[10px] text-muted">
              {entries.length}
            </span>
          )}
        </button>
      ))}
    </nav>
  )

  return (
    <div className="min-h-screen bg-bg text-ink">
      {/* global bar */}
      <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur-md print:hidden">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-3 px-4 lg:px-6">
          <button
            type="button"
            onClick={() => setView('home')}
            className="flex items-center gap-2.5"
            aria-label="PreBrief home"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-white shadow-sm">
              <Radar size={15} />
            </span>
            <span className="font-display text-[17px] tracking-tight text-ink">PreBrief</span>
          </button>

          <div className="hidden md:block">{nav}</div>

          <div className="ml-auto flex items-center gap-2">
            {briefing && view === 'briefing' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setChatOpen((c) => !c)}
                className={clsx(chatOpen && 'bg-surface-2 text-ink')}
              >
                <MessageSquare size={13} />
                <span className="hidden sm:inline">Agent</span>
              </Button>
            )}
<button
              type="button"
              onClick={() => update({ theme: settings.theme === 'dark' ? 'light' : 'dark' })}
              aria-label="Toggle theme"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-faint transition-colors hover:bg-surface-2 hover:text-ink"
            >
              {settings.theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
            </button>

            <button
              type="button"
              onClick={() => setShowSettings(true)}
              aria-label="Settings"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-faint transition-colors hover:bg-surface-2 hover:text-ink"
            >
              <Settings2 size={14} />
            </button>
</div>
        </div>


        <div className="md:hidden">
          <div className="flex items-center gap-0.5 overflow-x-auto px-3 pb-2">{nav}</div>
        </div>
      </header>

      {/* body */}
      <main>
        {error && (
          <div className="mx-auto max-w-[1400px] px-4 pt-4 lg:px-6">
            <div className="flex items-start gap-2.5 rounded-xl border border-negative/30 bg-negative-soft px-3.5 py-3">
              <AlertTriangle size={15} className="mt-0.5 shrink-0 text-negative" />
              <div className="min-w-0 flex-1 text-[12.5px] leading-relaxed text-negative">
                {error}
              </div>
              <button
                type="button"
                onClick={() => setError(null)}
                aria-label="Dismiss error"
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-negative/70 hover:bg-negative/10 hover:text-negative"
              >
                <X size={13} />
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex min-h-[70vh] items-center justify-center px-4 py-12">
            <ResearchProgress
              currentIndex={stageIndex}
              done={false}
              subject={pendingSubject}
            />
          </div>
        ) : view === 'home' ? (
          <HomeView
            onResearch={research}
            history={entries}
            watchlist={watchItems}
            onOpenHistory={() => setView('history')}
            onOpenWatchlist={() => setView('watchlist')}
            onOpenEntry={openEntry}
            loading={loading}
            defaultType={settings.defaultType}
            defaultDays={settings.defaultDays}
          />
        ) : view === 'briefing' && briefing ? (
          <BriefingView
            briefing={briefing}
            meeting={meeting}
            onNewResearch={startFresh}
            onAsk={() => setChatOpen(true)}
            watched={isWatched(briefing.subject)}
            onToggleWatch={() => toggleWatch(briefing.subject, briefing.type)}
            onSetMeeting={() => setShowMeeting(true)}
          />
        ) : view === 'history' ? (
          <HistoryView
            entries={entries}
            onOpen={openEntry}
            onRemove={remove}
            onClear={clear}
            onBack={() => setView('home')}
          />
        ) : view === 'watchlist' ? (
          <WatchlistView
            items={watchItems}
            onResearch={research}
            onRemove={(s) => toggleWatch(s, 'company')}
            onBack={() => setView('home')}
            onCompare={goCompare}
          />
        ) : view === 'onepager' ? (
          <OnePageBriefView onClose={() => setView('home')} />
        ) : view === 'documents' ? (
          <DocumentsView
            onUseInResearch={(ids, names) => {
              // Attach selected docs to next research run via focus note
              const note = `Using uploaded documents: ${names.join(', ')}`
              sessionStorage.setItem('prebrief.documentIds', JSON.stringify(ids))
              sessionStorage.setItem('prebrief.documentNote', note)
              setView('home')
            }}
          />
        ) : (
          <CompareView
            candidates={entries}
            leftId={compareLeft}
            rightId={compareRight}
            onPick={(side, id) =>
              side === 'left' ? setCompareLeft(id) : setCompareRight(id)
            }
            onBack={() => setView('home')}
          />
        )}
      </main>


      {/* floating agent trigger */}
      {briefing && view === 'briefing' && !chatOpen && (
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          className="fixed bottom-5 right-5 print:hidden z-30 inline-flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2.5 text-[12.5px] font-medium text-ink shadow-pop transition-transform hover:-translate-y-0.5"
        >
          <MessageSquare size={14} className="text-accent-text" />
          Ask the agent
        </button>
      )}

      {briefing && (
        <AgentChat
          briefing={briefing}
          open={chatOpen}
          onClose={() => setChatOpen(false)}
          onCitation={(id) => {
            setChatOpen(false)
            setTimeout(() => {
              const el = document.getElementById(`news-${id}`)
              if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
            }, 120)
          }}
        />
      )}

      {showMeeting && (
        <MeetingSetup
          meeting={meeting}
          onSave={setMeeting}
          onClose={() => setShowMeeting(false)}
        />
      )}

      {showSettings && (
        <SettingsPanel
          settings={settings}
          onChange={update}
          onClose={() => setShowSettings(false)}
        />
      )}

      <footer className="border-t border-line px-4 py-6 text-center text-[11px] text-faint print:hidden lg:px-6">
        PreBrief · {RESEARCH_STAGES.length} research stages ·{' '}
        {briefing ? `${briefing.stats.articles} items in the current window` : 'no active briefing'} ·
        press <kbd className="rounded border border-line px-1 font-mono text-[10px]">/</kbd> to search
      </footer>
    </div>
  )
}

