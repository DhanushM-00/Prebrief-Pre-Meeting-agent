import { useEffect } from 'react'
import { Check, Moon, Settings2, Sun, X } from 'lucide-react'
import { Button, Segmented } from './ui'
import { isLiveBackend } from '../lib/api'
import type { Settings } from '../lib/store'
import type { SubjectTypeInput } from '../types'

const DAY_OPTIONS = [
  { value: 7, label: '7 days' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days' },
  { value: 60, label: '60 days' },
  { value: 90, label: '90 days' },
]

export function SettingsPanel({
  settings,
  onChange,
  onClose,
}: {
  settings: Settings
  onChange: (patch: Partial<Settings>) => void
  onClose: () => void
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="animate-fade absolute inset-0 bg-black/45 backdrop-blur-[2px]" onClick={onClose} />
      <div className="animate-rise relative w-full max-w-sm rounded-2xl border border-line bg-surface shadow-pop">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <div className="flex items-center gap-2">
            <Settings2 size={15} className="text-accent-text" />
            <div>
              <div className="text-[13.5px] font-semibold tracking-tight text-ink">Settings</div>
              <div className="text-[11px] text-faint">Stored on this device</div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close settings"
            className="flex h-7 w-7 items-center justify-center rounded-lg text-faint hover:bg-surface-2 hover:text-ink"
          >
            <X size={14} />
          </button>
        </div>

        <div className="space-y-4 px-4 py-4">
          <div>
            <div className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-faint">
              Theme
            </div>
            <Segmented
              className="mt-1.5"
              value={settings.theme}
              onChange={(theme) => onChange({ theme })}
              options={[
                { value: 'dark', label: 'Dark', icon: <Moon size={11} /> },
                { value: 'light', label: 'Light', icon: <Sun size={11} /> },
              ]}
            />
          </div>

          <div>
            <div className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-faint">
              Default research window
            </div>
            <div className="mt-1.5 grid grid-cols-5 gap-1">
              {DAY_OPTIONS.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => onChange({ defaultDays: d.value })}
                  className={
                    settings.defaultDays === d.value
                      ? 'flex h-7 items-center justify-center rounded-md border border-accent/40 bg-accent-soft text-[11.5px] font-semibold text-accent-text'
                      : 'flex h-7 items-center justify-center rounded-md border border-line bg-surface-2 text-[11.5px] text-muted hover:text-ink'
                  }
                >
                  {d.value}d
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-faint">
              Default subject type
            </div>
            <Segmented
              className="mt-1.5"
              value={settings.defaultType}
              onChange={(defaultType) => onChange({ defaultType: defaultType as SubjectTypeInput })}
              options={[
                { value: 'auto', label: 'Auto-detect' },
                { value: 'company', label: 'Company' },
                { value: 'person', label: 'Person' },
              ]}
            />
          </div>

          <div className="rounded-lg border border-line bg-surface-2 px-3 py-2.5">
            <div className="flex items-center gap-2 text-[11.5px] font-medium text-ink">
              {isLiveBackend ? (
                <>
                  <Check size={12} className="text-positive" />
                  Live agent connected
                </>
              ) : (
                <>
                  <span className="h-1.5 w-1.5 rounded-full bg-warning" />
                  Synthetic demo corpus
                </>
              )}
            </div>
            <div className="mt-1 text-[11px] leading-relaxed text-faint">
              {isLiveBackend
                ? 'Briefings are fetched from the configured agent endpoint.'
                : 'Set VITE_API_BASE_URL to point the app at a real briefing agent.'}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end border-t border-line px-4 py-3">
          <Button variant="primary" size="sm" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </div>
  )
}
