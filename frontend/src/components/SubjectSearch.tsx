import { useEffect, useRef, useState } from 'react'
import { ArrowRight, Building2, ChevronDown, Crosshair, Search, User } from 'lucide-react'
import { clsx } from 'clsx'
import { Button, Segmented } from './ui'
import type { SubjectTypeInput } from '../types'

export interface SearchProps {
  onSubmit: (
    subject: string,
    type: SubjectTypeInput,
    days: number,
    focus?: string,
    meetingAt?: string,
  ) => void
  loading?: boolean
  defaultType?: SubjectTypeInput
  defaultDays?: number
  variant?: 'hero' | 'compact'
  autoFocus?: boolean
}

const DAY_OPTIONS = [7, 14, 30, 60, 90]

function defaultMeetingLocal(): string {
  const d = new Date()
  d.setMinutes(0, 0, 0)
  // datetime-local value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function SubjectSearch({
  onSubmit,
  loading,
  defaultType = 'auto',
  defaultDays = 30,
  variant = 'hero',
  autoFocus,
}: SearchProps) {
  const [value, setValue] = useState('')
  const [type, setType] = useState<SubjectTypeInput>(defaultType)
  const [days, setDays] = useState(defaultDays)
  const [focus, setFocus] = useState('')
  const [showFocus, setShowFocus] = useState(false)
  const [meetingAt, setMeetingAt] = useState(defaultMeetingLocal)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus()
  }, [autoFocus])

  const toOffsetIso = (localValue: string): string => {
    const normalized = localValue.length === 16 ? `${localValue}:00` : localValue
    const d = new Date(normalized)
    if (Number.isNaN(d.getTime())) return normalized
    const pad = (n: number) => String(Math.abs(n)).padStart(2, '0')
    const offsetMin = -d.getTimezoneOffset()
    const sign = offsetMin >= 0 ? '+' : '-'
    const hh = pad(Math.floor(Math.abs(offsetMin) / 60))
    const mm = pad(Math.abs(offsetMin) % 60)
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}${sign}${hh}:${mm}`
  }

  const submit = () => {
    const subject = value.trim()
    if (!subject || loading) return
    onSubmit(subject, type, days, focus.trim() || undefined, toOffsetIso(meetingAt))
  }

  const hero = variant === 'hero'

  return (
    <div className={clsx('w-full', hero ? 'max-w-2xl' : 'max-w-xl')}>
      <div
        className={clsx(
          'group relative rounded-2xl border border-line bg-surface shadow-card transition-shadow focus-within:border-accent/45',
          hero && 'shadow-pop',
        )}
      >
        <div className="flex items-center gap-2 px-3.5 pt-3.5">
          <Search className={clsx('shrink-0', hero ? 'h-4.5 w-4.5' : 'h-4 w-4')} style={{ width: 18, height: 18 }} strokeWidth={2} />
          <input
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submit()
            }}
            placeholder="Company or person you are meeting…"
            className={clsx(
              'w-full bg-transparent text-ink outline-none placeholder:text-faint',
              hero ? 'py-1 text-[17px]' : 'py-0.5 text-[14px]',
            )}
          />
          <Button
            variant="primary"
            size={hero ? 'md' : 'sm'}
            onClick={submit}
            disabled={!value.trim() || loading}
            className="shrink-0"
          >
            {loading ? 'Researching…' : 'Generate Brief'}
            {!loading && <ArrowRight size={14} />}
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-2 px-3.5 pb-3 pt-2">
          <Segmented
            size="sm"
            value={type}
            onChange={setType}
            options={[
              { value: 'auto', label: 'Auto', icon: <Crosshair size={11} /> },
              { value: 'company', label: 'Company', icon: <Building2 size={11} /> },
              { value: 'person', label: 'Person', icon: <User size={11} /> },
            ]}
          />

          <label className="inline-flex h-6 items-center gap-1 rounded-md border border-line bg-surface-2 px-2 text-[11px] font-medium text-muted">
            Meeting
            <input
              type="datetime-local"
              value={meetingAt}
              onChange={(e) => setMeetingAt(e.target.value)}
              className="bg-transparent text-[11px] text-ink outline-none"
            />
          </label>

          <div className="relative">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="h-6 appearance-none rounded-md border border-line bg-surface-2 pl-2 pr-6 text-[11px] font-medium text-muted outline-none hover:text-ink focus:border-accent/50"
            >
              {DAY_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  last {d}d
                </option>
              ))}
            </select>
            <ChevronDown size={11} className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-faint" />
          </div>

          <button
            type="button"
            onClick={() => setShowFocus((s) => !s)}
            className={clsx(
              'h-6 rounded-md border px-2 text-[11px] font-medium transition-colors',
              focus
                ? 'border-accent/40 bg-accent-soft text-accent-text'
                : 'border-line bg-surface-2 text-faint hover:text-muted',
            )}
          >
            {focus ? `Focus: ${focus}` : '+ Add focus'}
          </button>
        </div>

        {showFocus && (
          <div className="animate-rise border-t border-line px-3.5 py-2.5">
            <input
              value={focus}
              onChange={(e) => setFocus(e.target.value)}
              placeholder="Steer the research — e.g. “fundraising, India expansion, litigation”"
              className="w-full bg-transparent text-[13px] text-ink outline-none placeholder:text-faint"
            />
          </div>
        )}
      </div>
    </div>
  )
}
