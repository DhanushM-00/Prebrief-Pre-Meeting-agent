import { useEffect, useRef, useState } from 'react'
import { Check, Copy, Download, FileText, Link2, Printer, ScrollText } from 'lucide-react'
import { clsx } from 'clsx'
import { Button } from './ui'
import {
  briefingToMarkdown,
  cheatSheet,
  copyText,
  downloadFile,
  printBriefing,
  slugFile,
} from '../lib/export'
import { briefUrl } from '../lib/link'
import type { BriefingResult, MeetingContext } from '../types'

interface Props {
  briefing: BriefingResult
  meeting?: MeetingContext
  compact?: boolean
}

export function ExportMenu({ briefing, meeting, compact }: Props) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const md = () => briefingToMarkdown(briefing, meeting)
  const base = `${slugFile(briefing.snapshot.name)}-brief-${briefing.windowDays}d`

  const doCopy = async (label: string, text: string) => {
    const ok = await copyText(text)
    if (ok) {
      setCopied(label)
      setTimeout(() => setCopied(null), 1500)
    }
  }

  const items = [
    {
      key: 'cheat',
      icon: ScrollText,
      label: 'Copy cheat sheet',
      run: () => doCopy('cheat', cheatSheet(briefing, meeting)),
    },
    {
      key: 'md',
      icon: Copy,
      label: 'Copy as Markdown',
      run: () => doCopy('md', md()),
    },
    {
      key: 'link',
      icon: Link2,
      label: 'Copy link to this brief',
      run: () => doCopy('link', briefUrl(briefing.subject, briefing.type, briefing.windowDays)),
    },
    {
      key: 'json',
      icon: Download,
      label: 'Download .md',
      run: () => downloadFile(`${base}.md`, md()),
    },
    {
      key: 'jsonfile',
      icon: FileText,
      label: 'Download raw .json',
      run: () => downloadFile(`${base}.json`, JSON.stringify(briefing, null, 2), 'application/json'),
    },
    {
      key: 'print',
      icon: Printer,
      label: 'Print / Save as PDF',
      run: () => {
        setOpen(false)
        setTimeout(printBriefing, 120)
      },
    },
  ]

  return (
    <div className="relative" ref={ref}>
      <Button
        variant="outline"
        size={compact ? 'sm' : 'md'}
        onClick={() => setOpen((o) => !o)}
        className={clsx(open && 'border-accent/40 bg-accent-soft text-accent-text')}
      >
        <Download size={compact ? 12 : 14} />
        Export
      </Button>

      {open && (
        <div className="animate-rise absolute right-0 z-50 mt-1.5 w-56 overflow-hidden rounded-xl border border-line bg-surface shadow-pop">
          <div className="border-b border-line px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">
            Brief exports
          </div>
          <div className="p-1">
            {items.map((it) => {
              const Icon = it.icon
              const isCopied = copied === it.key
              return (
                <button
                  key={it.key}
                  type="button"
                  onClick={() => {
                    it.run()
                    if (it.key !== 'print') setOpen(false)
                  }}
                  className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[12.5px] text-muted transition-colors hover:bg-surface-2 hover:text-ink"
                >
                  {isCopied ? (
                    <Check size={13} className="text-positive" />
                  ) : (
                    <Icon size={13} className="text-faint" />
                  )}
                  {isCopied ? 'Copied to clipboard' : it.label}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
