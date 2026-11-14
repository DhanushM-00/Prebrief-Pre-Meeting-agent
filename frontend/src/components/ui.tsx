import { type ReactNode, type ButtonHTMLAttributes, type HTMLAttributes } from 'react'
import { clsx } from 'clsx'

/* ---------------- surfaces ---------------- */
export function Card({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        'rounded-xl border border-line bg-surface shadow-card',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

export function SectionTitle({
  eyebrow,
  title,
  count,
  action,
  className,
}: {
  eyebrow?: string
  title: string
  count?: number | string
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={clsx('flex items-end justify-between gap-4 px-5 pt-4 pb-3', className)}>
      <div className="min-w-0">
        {eyebrow && (
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">{eyebrow}</div>
        )}
        <div className="flex items-baseline gap-2">
          <h2 className="truncate text-[15px] font-semibold tracking-tight text-ink">{title}</h2>
          {count !== undefined && (
            <span className="tabular text-[11px] font-medium text-faint">{count}</span>
          )}
        </div>
      </div>
      {action}
    </div>
  )
}

/* ---------------- badges ---------------- */
export type Tone = 'neutral' | 'accent' | 'positive' | 'negative' | 'warning' | 'info'

const TONE_CLASS: Record<Tone, string> = {
  neutral: 'bg-surface-3 text-muted border-line',
  accent: 'bg-accent-soft text-accent-text border-accent/25',
  positive: 'bg-positive-soft text-positive border-positive/25',
  negative: 'bg-negative-soft text-negative border-negative/25',
  warning: 'bg-warning-soft text-warning border-warning/25',
  info: 'bg-info-soft text-info border-info/25',
}

export function Badge({
  tone = 'neutral',
  children,
  className,
  icon,
}: {
  tone?: Tone
  children: ReactNode
  className?: string
  icon?: ReactNode
}) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10.5px] font-medium leading-4',
        TONE_CLASS[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  )
}

export function Dot({ tone = 'neutral' }: { tone?: Tone }) {
  const map: Record<Tone, string> = {
    neutral: 'bg-faint',
    accent: 'bg-accent',
    positive: 'bg-positive',
    negative: 'bg-negative',
    warning: 'bg-warning',
    info: 'bg-info',
  }
  return <span className={clsx('inline-block h-1.5 w-1.5 shrink-0 rounded-full', map[tone])} />
}

/* ---------------- buttons ---------------- */
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'outline' | 'ghost' | 'subtle'
  size?: 'sm' | 'md'
  active?: boolean
}

export function Button({
  variant = 'outline',
  size = 'md',
  active,
  className,
  children,
  ...rest
}: ButtonProps) {
  const base =
    'inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50'
  const sizes = {
    sm: 'h-7 px-2.5 text-[11.5px]',
    md: 'h-9 px-3.5 text-[13px]',
  }
  const variants = {
    primary:
      'bg-accent text-white shadow-sm hover:brightness-110 active:brightness-95 border border-transparent',
    outline: clsx(
      'border border-line bg-surface text-ink hover:bg-surface-2 hover:border-line-strong',
    ),
    ghost: 'text-muted hover:text-ink hover:bg-surface-2 border border-transparent',
    subtle: 'bg-surface-3 text-muted hover:text-ink hover:bg-surface-2 border border-transparent',
  }
  return (
    <button
      type="button"
      className={clsx(
        base,
        sizes[size],
        variants[variant],
        active && 'border-accent/40 bg-accent-soft text-accent-text',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  )
}

export function IconButton({
  label,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={clsx(
        'inline-flex h-8 w-8 items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  )
}

/* ---------------- segmented control ---------------- */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  size = 'md',
  className,
}: {
  options: { value: T; label: string; icon?: ReactNode }[]
  value: T
  onChange: (v: T) => void
  size?: 'sm' | 'md'
  className?: string
}) {
  return (
    <div
      className={clsx(
        'inline-flex items-center gap-0.5 rounded-lg border border-line bg-surface-2 p-0.5',
        className,
      )}
    >
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={clsx(
            'inline-flex items-center gap-1.5 rounded-md font-medium transition-all duration-150',
            size === 'sm' ? 'h-6 px-2 text-[11px]' : 'h-7 px-2.5 text-[12px]',
            value === o.value
              ? 'bg-surface text-ink shadow-sm'
              : 'text-faint hover:text-muted',
          )}
        >
          {o.icon}
          {o.label}
        </button>
      ))}
    </div>
  )
}

/* ---------------- misc ---------------- */
export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={clsx(
        'inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent',
        className,
      )}
    />
  )
}

export function Avatar({
  name,
  size = 40,
  tone = 'accent',
}: {
  name: string
  size?: number
  tone?: 'accent' | 'muted'
}) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')
  return (
    <div
      style={{ width: size, height: size, fontSize: size * 0.34 }}
      className={clsx(
        'flex shrink-0 items-center justify-center rounded-xl font-semibold tracking-tight',
        tone === 'accent'
          ? 'bg-accent-soft text-accent-text ring-1 ring-accent/20'
          : 'bg-surface-3 text-muted ring-1 ring-line',
      )}
    >
      {initials || '?'}
    </div>
  )
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-line bg-surface-2 px-1 py-px font-mono text-[10px] text-faint">
      {children}
    </kbd>
  )
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon?: ReactNode
  title: string
  body?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      {icon && <div className="mb-1 text-faint">{icon}</div>}
      <div className="text-[14px] font-semibold text-ink">{title}</div>
      {body && <div className="max-w-sm text-[12.5px] leading-relaxed text-muted">{body}</div>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string
  value: ReactNode
  hint?: string
  tone?: Tone
}) {
  const valueTone =
    tone === 'positive'
      ? 'text-positive'
      : tone === 'negative'
        ? 'text-negative'
        : tone === 'warning'
          ? 'text-warning'
          : 'text-ink'
  return (
    <div className="min-w-0">
      <div className="truncate text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">
        {label}
      </div>
      <div className={clsx('tabular mt-1 truncate text-[19px] font-semibold tracking-tight', valueTone)}>
        {value}
      </div>
      {hint && <div className="mt-0.5 truncate text-[11px] text-faint">{hint}</div>}
    </div>
  )
}

export function ProgressBar({ value, className }: { value: number; className?: string }) {
  return (
    <div className={clsx('h-1 w-full overflow-hidden rounded-full bg-surface-3', className)}>
      <div
        className="h-full rounded-full bg-accent transition-[width] duration-500"
        style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }}
      />
    </div>
  )
}
