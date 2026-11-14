import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Bot, Sparkles, User, X } from 'lucide-react'
import { clsx } from 'clsx'
import { Button, IconButton, Spinner } from './ui'
import { askAgent } from '../lib/api'
import { Markdown } from './Markdown'
import type { BriefingResult, ChatTurn } from '../types'

const SUGGESTIONS = [
  'What is the riskiest thing in the last 30 days?',
  'What should I lead with?',
  'What are the questions I should ask?',
  'Summarise the coverage',
  'Who is the key person here?',
]

export function AgentChat({
  briefing,
  open,
  onClose,
  onCitation,
}: {
  briefing: BriefingResult
  open: boolean
  onClose: () => void
  onCitation?: (id: string) => void
}) {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setTurns([])
    setInput('')
  }, [briefing.id])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  // Escape closes the drawer — the keyboard shortcut people expect from a
  // side panel that floats over the content.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [turns, busy])

  const send = async (raw?: string) => {
    const question = (raw ?? input).trim()
    if (!question || busy) return
    setInput('')
    const userTurn: ChatTurn = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: question,
      createdAt: new Date().toISOString(),
    }
    const history = [...turns, userTurn]
    setTurns(history)
    setBusy(true)
    try {
      const { answer, citations } = await askAgent(briefing, question, history)
      setTurns((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'agent',
          content: answer,
          createdAt: new Date().toISOString(),
          citations,
        },
      ])
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: 'agent',
          content: `Something went wrong reaching the agent: ${
            err instanceof Error ? err.message : 'unknown error'
          }`,
          createdAt: new Date().toISOString(),
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  const newsById = new Map(briefing.news.map((n) => [n.id, n]))

  return (
    <>
      {/* backdrop on mobile */}
      {open && (
        <div
          className="animate-fade fixed inset-0 z-30 bg-black/40 backdrop-blur-[2px] lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={clsx(
          'fixed right-0 top-0 z-40 flex h-full w-full max-w-[420px] flex-col border-l border-line bg-surface shadow-pop transition-transform duration-300',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
        aria-hidden={!open}
      >
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent-text ring-1 ring-accent/20">
              <Sparkles size={15} />
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold tracking-tight text-ink">Briefing agent</div>
              <div className="truncate text-[10.5px] text-faint">
                Grounded in {briefing.stats.articles} items · {briefing.windowDays}d window
              </div>
            </div>
          </div>
          <IconButton label="Close agent" onClick={onClose}>
            <X size={15} />
          </IconButton>
        </div>

        <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {turns.length === 0 && (
            <div className="rounded-xl border border-line bg-surface-2 p-3.5">
              <div className="text-[12.5px] leading-relaxed text-muted">
                I have read the full briefing on{' '}
                <span className="font-medium text-ink">{briefing.snapshot.name}</span>. Ask me
                anything about it — the answers come only from what is inside the window.
              </div>
              <div className="mt-3 space-y-1">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => send(s)}
                    className="block w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-left text-[11.5px] text-muted transition-colors hover:border-accent/40 hover:text-ink"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {turns.map((t) => (
            <div
              key={t.id}
              className={clsx('flex gap-2.5', t.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              {t.role === 'agent' && (
                <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent-text">
                  <Bot size={13} />
                </div>
              )}
              <div
                className={clsx(
                  'max-w-[85%] rounded-xl px-3 py-2 text-[12.5px]',
                  t.role === 'user'
                    ? 'whitespace-pre-wrap bg-accent text-white'
                    : 'border border-line bg-surface-2 text-muted',
                )}
              >
                {t.role === 'user' ? (
                  t.content
                ) : (
                  <Markdown content={t.content} />
                )}
              </div>
              {t.role === 'user' && (
                <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-surface-3 text-muted">
                  <User size={12} />
                </div>
              )}
            </div>
          ))}

          {busy && (
            <div className="flex items-center gap-2.5">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent-text">
                <Bot size={13} />
              </div>
              <div className="flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3 py-2.5">
                <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-accent" />
                <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-accent [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-accent [animation-delay:300ms]" />
                <Spinner className="ml-1 text-faint" />
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-line p-3">
          <div className="flex items-end gap-2 rounded-xl border border-line bg-surface-2 p-1.5 focus-within:border-accent/45">
            <textarea
              ref={inputRef as unknown as React.RefObject<HTMLTextAreaElement>}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send()
                }
              }}
              rows={1}
              placeholder="Ask about this briefing…"
              className="max-h-28 flex-1 resize-none bg-transparent px-1.5 py-1.5 text-[12.5px] text-ink outline-none placeholder:text-faint"
            />
            <Button variant="primary" size="sm" onClick={() => send()} disabled={!input.trim() || busy}>
              <ArrowUp size={13} />
            </Button>
          </div>

          {turns.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {turns
                .flatMap((t) => t.citations ?? [])
                .slice(0, 4)
                .map((cid) => {
                  const item = newsById.get(cid)
                  if (!item) return null
                  return (
                    <button
                      key={cid}
                      type="button"
                      onClick={() => onCitation?.(cid)}
                      className="max-w-full truncate rounded border border-line px-1.5 py-0.5 text-[10.5px] text-faint transition-colors hover:border-accent/40 hover:text-ink"
                    >
                      {item.headline}
                    </button>
                  )
                })}
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
