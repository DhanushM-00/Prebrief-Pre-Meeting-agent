import { Fragment, type ReactNode } from 'react'
import { clsx } from 'clsx'

/**
 * Minimal inline markdown for agent answers — bold, italic, bullet lists and
 * numbered lists. Deliberately tiny: the agent returns a known, small grammar.
 */

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = []
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g
  let last = 0
  let match: RegExpExecArray | null
  let i = 0

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index))
    const token = match[0]
    const key = `${keyPrefix}-i${i++}`
    if (token.startsWith('**')) {
      nodes.push(
        <strong key={key} className="font-semibold text-ink">
          {token.slice(2, -2)}
        </strong>,
      )
    } else if (token.startsWith('`')) {
      nodes.push(
        <code
          key={key}
          className="rounded border border-line bg-surface-3 px-1 py-px font-mono text-[11px]"
        >
          {token.slice(1, -1)}
        </code>,
      )
    } else {
      nodes.push(
        <em key={key} className="italic">
          {token.slice(1, -1)}
        </em>,
      )
    }
    last = match.index + token.length
  }
  if (last < text.length) nodes.push(text.slice(last))
  return nodes
}

export function Markdown({ content, className }: { content: string; className?: string }) {
  const lines = content.split('\n')
  const blocks: ReactNode[] = []
  let list: { type: 'ul' | 'ol'; items: string[] } | null = null

  const flush = (key: string) => {
    if (!list) return
    const items = list.items.map((item, idx) => (
      <li key={idx} className="flex gap-2">
        <span className="shrink-0 text-faint">{list!.type === 'ol' ? `${idx + 1}.` : '•'}</span>
        <span>{renderInline(item, `${key}-${idx}`)}</span>
      </li>
    ))
    blocks.push(
      list.type === 'ol' ? (
        <ol key={key} className="my-1.5 space-y-1">
          {items}
        </ol>
      ) : (
        <ul key={key} className="my-1.5 space-y-1">
          {items}
        </ul>
      ),
    )
    list = null
  }

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd()
    const key = `b${idx}`

    if (!line.trim()) {
      flush(`${key}-flush`)
      return
    }

    const bullet = line.match(/^\s*[-*]\s+(.*)$/)
    const ordered = line.match(/^\s*(\d+)\.\s+(.*)$/)

    if (bullet) {
      if (!list || list.type !== 'ul') {
        flush(`${key}-flush`)
        list = { type: 'ul', items: [] }
      }
      list.items.push(bullet[1])
      return
    }
    if (ordered) {
      if (!list || list.type !== 'ol') {
        flush(`${key}-flush`)
        list = { type: 'ol', items: [] }
      }
      list.items.push(ordered[2])
      return
    }

    flush(`${key}-flush`)
    blocks.push(
      <p key={key} className="my-1.5 first:mt-0 last:mb-0">
        {renderInline(line, key)}
      </p>,
    )
  })
  flush('tail')

  return <div className={clsx('leading-relaxed', className)}>{blocks.map((b, i) => <Fragment key={i}>{b}</Fragment>)}</div>
}
