import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertOctagon, RotateCcw } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

/**
 * Catches render-time failures so a broken briefing never leaves the user with
 * a blank page — they get a way out instead.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('PreBrief crashed:', error, info.componentStack)
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    return (
      <div className="flex min-h-screen items-center justify-center bg-bg px-4 text-ink">
        <div className="w-full max-w-md rounded-2xl border border-line bg-surface p-6 text-center shadow-card">
          <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-negative-soft text-negative">
            <AlertOctagon size={21} />
          </div>
          <h1 className="mt-4 text-[16px] font-semibold tracking-tight">Something broke</h1>
          <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">
            The briefing could not be rendered. Reloading usually clears it — your saved history and
            watchlist are stored locally and are untouched.
          </p>
          <pre className="mt-3 max-h-28 overflow-auto rounded-lg border border-line bg-surface-2 px-3 py-2 text-left font-mono text-[10.5px] leading-relaxed text-faint">
            {error.message}
          </pre>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-accent px-3.5 py-2 text-[13px] font-medium text-white transition-opacity hover:opacity-90"
          >
            <RotateCcw size={14} />
            Reload
          </button>
        </div>
      </div>
    )
  }
}
