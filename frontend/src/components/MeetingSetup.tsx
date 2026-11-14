import { useEffect, useState } from 'react'
import { CalendarDays, Check, Users, X } from 'lucide-react'
import { Button } from './ui'
import type { MeetingContext } from '../types'

export function MeetingSetup({
  meeting,
  onSave,
  onClose,
}: {
  meeting: MeetingContext
  onSave: (m: MeetingContext) => void
  onClose: () => void
}) {
  const [title, setTitle] = useState(meeting.title)
  const [date, setDate] = useState(meeting.date)
  const [attendees, setAttendees] = useState(meeting.attendees.join(', '))
  const [note, setNote] = useState(meeting.note)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const save = () => {
    onSave({
      title: title.trim() || 'Untitled meeting',
      date,
      attendees: attendees
        .split(',')
        .map((a) => a.trim())
        .filter(Boolean),
      note: note.trim(),
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="animate-fade absolute inset-0 bg-black/45 backdrop-blur-[2px]" onClick={onClose} />
      <div className="animate-rise relative w-full max-w-md rounded-2xl border border-line bg-surface shadow-pop">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <div>
            <div className="text-[13.5px] font-semibold tracking-tight text-ink">Meeting details</div>
            <div className="text-[11px] text-faint">
              Attached to this brief and included in every export
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-7 w-7 items-center justify-center rounded-lg text-faint hover:bg-surface-2 hover:text-ink"
          >
            <X size={14} />
          </button>
        </div>

        <div className="space-y-3 px-4 py-4">
          <label className="block">
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-faint">
              Meeting
            </span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Series B partner introduction"
              className="mt-1 h-9 w-full rounded-lg border border-line bg-surface-2 px-2.5 text-[12.5px] text-ink outline-none placeholder:text-faint focus:border-accent/50"
            />
          </label>

          <label className="block">
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-faint">
              Date
            </span>
            <div className="relative mt-1">
              <CalendarDays
                size={13}
                className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-faint"
              />
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="h-9 w-full rounded-lg border border-line bg-surface-2 pl-8 pr-2.5 text-[12.5px] text-ink outline-none focus:border-accent/50"
              />
            </div>
          </label>

          <label className="block">
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-faint">
              Attendees
            </span>
            <div className="relative mt-1">
              <Users
                size={13}
                className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-faint"
              />
              <input
                value={attendees}
                onChange={(e) => setAttendees(e.target.value)}
                placeholder="Comma separated"
                className="h-9 w-full rounded-lg border border-line bg-surface-2 pl-8 pr-2.5 text-[12.5px] text-ink outline-none placeholder:text-faint focus:border-accent/50"
              />
            </div>
          </label>

          <label className="block">
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-faint">
              Context
            </span>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder="What is this meeting for? Anything the brief should emphasise."
              className="mt-1 w-full resize-none rounded-lg border border-line bg-surface-2 px-2.5 py-2 text-[12.5px] leading-relaxed text-ink outline-none placeholder:text-faint focus:border-accent/50"
            />
          </label>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-line px-4 py-3">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={save}>
            <Check size={13} />
            Save
          </Button>
        </div>
      </div>
    </div>
  )
}
