import type { BriefingRequest, BriefingResult, ChatTurn } from '../types'
import { generateBriefing } from './mock'

/**
 * Backend contract (see README):
 *   POST {base}/briefing  body: BriefingRequest   -> BriefingResult
 *   POST {base}/chat      body: {briefingId, question, history} -> {answer, citations?}
 *
 * When VITE_API_BASE_URL is unset the app runs against the synthetic demo corpus.
 */
import { API_BASE, http, isBackendConfigured, ApiError } from './http'

/** True when VITE_API_BASE_URL is set. Demo/mock only when explicitly enabled. */
export const isLiveBackend = isBackendConfigured
const BASE = API_BASE
const DEMO_MODE = (import.meta.env?.VITE_DEMO_MODE as string | undefined) === '1'


export interface ResearchStage {
  id: string
  label: string
  detail: string
}

export const RESEARCH_STAGES: ResearchStage[] = [
  { id: 'resolve', label: 'Resolving subject', detail: 'Disambiguating company vs. person, locking the entity' },
  { id: 'profile', label: 'Building profile', detail: 'Pulling sector, stage, headcount, key people' },
  { id: 'news', label: 'Scanning last 30 days', detail: 'Sweeping outlets, filings, press and social' },
  { id: 'dedupe', label: 'Deduplicating & scoring', detail: 'Clustering coverage, tagging sentiment and impact' },
  { id: 'synthesise', label: 'Synthesising', detail: 'Deriving signals, talking points and open questions' },
]

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))

export interface RunOptions {
  /** Called as each stage begins, so the UI can narrate progress. */
  onStage?: (stage: ResearchStage, index: number, total: number) => void
  signal?: AbortSignal
}

export async function runBriefing(req: BriefingRequest, opts: RunOptions = {}): Promise<BriefingResult> {
  if (BASE && !DEMO_MODE) return runLiveBriefing(req, opts)
  if (!DEMO_MODE) {
    throw new ApiError(
      'Backend is not configured. Set VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1 in frontend/.env',
      0,
      { code: 'config_error' },
    )
  }
  // Explicit demo mode only
  for (let i = 0; i < RESEARCH_STAGES.length; i++) {
    if (opts.signal?.aborted) throw new Error('aborted')
    opts.onStage?.(RESEARCH_STAGES[i], i, RESEARCH_STAGES.length)
    await wait(320 + i * 90)
  }
  if (opts.signal?.aborted) throw new Error('aborted')
  await wait(260)
  return generateBriefing(req)
}

async function runLiveBriefing(req: BriefingRequest, opts: RunOptions): Promise<BriefingResult> {
  // Narrate stages optimistically while the request is in flight
  const stages = RESEARCH_STAGES
  let stageTimer: ReturnType<typeof setInterval> | null = null
  let idx = 0
  opts.onStage?.(stages[0], 0, stages.length)
  stageTimer = setInterval(() => {
    idx = Math.min(idx + 1, stages.length - 1)
    opts.onStage?.(stages[idx], idx, stages.length)
  }, 900)
  try {
    return await http.post<BriefingResult>('/briefing', req, { signal: opts.signal, timeoutMs: 180_000 })
  } finally {
    if (stageTimer) clearInterval(stageTimer)
  }
}


/* ------------------------------------------------------------------ *
 * Follow-up agent
 * ------------------------------------------------------------------ */
export async function askAgent(
  briefing: BriefingResult,
  question: string,
  history: ChatTurn[] = [],
  opts: { signal?: AbortSignal } = {},
): Promise<{ answer: string; citations: string[] }> {
  // Prefer backend evidence-grounded chat when the API is configured.
  if (BASE && !DEMO_MODE) {
    try {
      const body = {
        question,
        research_session_id: (briefing as { researchSessionId?: string }).researchSessionId
          ?? (briefing as { id?: string }).id
          ?? undefined,
        entity_name: briefing.subject ?? briefing.snapshot?.name,
        history: history.map((t) => ({ role: t.role, content: t.content })),
      }
      const res = await http.post<{
        answer: string
        citations?: string[]
        citation_details?: { id: string; title?: string; url?: string }[]
      }>('/chat', body, { signal: opts.signal, timeoutMs: 60_000 })
      return {
        answer: res.answer,
        citations: res.citations ?? [],
      }
    } catch (err) {
      // Fall back to local grounded answer if chat endpoint fails (older backend).
      console.warn('Backend chat unavailable, using local grounded answer', err)
    }
  }
  await wait(200)
  return groundedAnswer(briefing, question)
}

const STOP = new Set([
  'the', 'a', 'an', 'of', 'and', 'or', 'to', 'in', 'on', 'for', 'is', 'was', 'are', 'were',
  'what', 'who', 'how', 'why', 'when', 'where', 'did', 'does', 'do', 'has', 'have', 'had',
  'me', 'about', 'their', 'they', 'them', 'his', 'her', 'its', 'our', 'your', 'we', 'you',
  'that', 'this', 'these', 'those', 'be', 'been', 'it', 'as', 'at', 'by', 'with', 'from',
  'tell', 'give', 'know', 'want', 'need', 'can', 'could', 'would', 'should', 'will',
])

function tokenize(s: string) {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 2 && !STOP.has(w))
}

function scoreText(qTokens: string[], text: string) {
  const t = text.toLowerCase()
  let score = 0
  for (const tok of qTokens) {
    if (t.includes(tok)) score += 1
  }
  return score
}

function groundedAnswer(briefing: BriefingResult, question: string): { answer: string; citations: string[] } {
  const q = question.trim()
  const qt = tokenize(q)
  const inWin = briefing.news.filter((n) => n.inWindow)
  const name = briefing.snapshot.name

  const hits = inWin
    .map((n) => ({
      n,
      s:
        scoreText(qt, n.headline) * 3 +
        scoreText(qt, n.summary) * 2 +
        scoreText(qt, n.whyItMatters) * 2 +
        scoreText(qt, n.category) * 3 +
        scoreText(qt, n.entities.join(' ')) * 2 +
        (n.sentiment === 'negative' && /risk|worst|bad|concern|threat|problem|loss/.test(q) ? 3 : 0) +
        (n.sentiment === 'positive' && /good|great|strong|best|opportunit|momentum|win/.test(q) ? 3 : 0),
    }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s)

  const cites: string[] = []
  const cite = (n: { id: string } | string | undefined) => {
    if (!n) return
    const id = typeof n === 'string' ? n : n.id
    if (id && !cites.includes(id)) cites.push(id)
  }

  const lower = q.toLowerCase()

  // --- identity ---
  if (/^(hi|hey|hello|yo)\b/.test(lower) || /who are you|what are you|what is this/.test(lower)) {
    return {
      answer: `I'm the briefing agent. Give me a company or a person and I research the last ${briefing.windowDays} days of coverage, then hand back a dossier: the signal map, what to talk about, what to ask, and what's risky.\n\nRight now I'm holding a briefing on **${name}** — ${briefing.stats.articles} in-window articles across ${briefing.stats.sources} outlets. Ask me anything about it.`,
      citations: [],
    }
  }

  // --- what is / who is this ---
  if (/\b(who is|what is|tell me about|summar(y|ise|ize)|overview|profile|background|introduce)\b/.test(lower) && hits.length < 2) {
    const s = briefing.snapshot
    const facts = s.facts.slice(0, 6).map((f) => `**${f.label}:** ${f.value}`).join('  \n')
    return {
      answer: `**${s.name}** — ${s.tagline}\n\n${facts}\n\n${
        briefing.stats.keyItems
          ? `The headline story in the window: ${briefing.news.find((n) => n.isKey)?.headline ?? '—'}`
          : 'Nothing in the window was high-impact — a quiet news cycle.'
      }`,
      citations: [],
    }
  }

  // --- risk ---
  if (/risk|worst|bad|negative|concern|threat|problem|fail|loss|litigat|regulat/.test(lower)) {
    const risks = briefing.signals.filter((s) => s.kind === 'risk')
    const neg = inWin.filter((n) => n.sentiment === 'negative').slice(0, 3)
    neg.forEach((n) => cite(n))
    return {
      answer: `${
        risks.length
          ? `**${risks[0].title}.** ${risks[0].detail}`
          : 'Nothing in the window reads as a material negative.'
      }${
        neg.length
          ? `\n\nThe specific negative items:\n${neg.map((n) => `- **${n.headline}** — ${n.source}, ${n.summary}`).join('\n')}`
          : ''
      }${neg.length ? '\n\nThese are the ones to raise first, because raising them yourself buys you the room to ask everything else.' : ''}`,
      citations: cites,
    }
  }

  // --- opportunity / momentum ---
  if (/opportunit|momentum|strength|good news|upbeat|win|advantage|bull/.test(lower)) {
    const opps = briefing.signals.filter((s) => s.kind === 'opportunity')
    const pos = inWin.filter((n) => n.sentiment === 'positive').slice(0, 3)
    pos.forEach((n) => cite(n))
    return {
      answer: `${
        opps.length ? `**${opps[0].title}.** ${opps[0].detail}` : 'No clear positive momentum signal in the window.'
      }${
        pos.length
          ? `\n\nSupporting coverage:\n${pos.map((n) => `- **${n.headline}** — ${n.source}, ${n.summary}`).join('\n')}`
          : ''
      }`,
      citations: cites,
    }
  }

  // --- money / funding ---
  if (/fund|rais|money|capital|valu|invest|series|arr|revenue|profit|margin|financial/.test(lower)) {
    const money_ = inWin.filter((n) => ['funding', 'earnings', 'markets'].includes(n.category)).slice(0, 4)
    money_.forEach((n) => cite(n))
    const facts = briefing.snapshot.facts.filter((f) =>
      /stage|valuation|revenue|fund|hiring|headcount/i.test(f.label),
    )
    return {
      answer: `${
        facts.length ? facts.map((f) => `**${f.label}:** ${f.value}`).join('  \n') + '\n\n' : ''
      }${
        money_.length
          ? money_.map((n) => `**${n.headline}**  \n${n.summary}  \n*${n.source} · ${n.category}*`).join('\n\n')
          : 'No financial coverage inside the window.'
      }`,
      citations: cites,
    }
  }

  // --- talking points ---
  if (/talk(ing)? point|how do i|what should i say|open(er)?|agenda|convince/.test(lower)) {
    briefing.talkingPoints.slice(0, 4).forEach((tp) => tp.evidence.forEach((id) => cite(id)))
    return {
      answer: `Here is how I'd open the meeting:\n\n${briefing.talkingPoints
        .slice(0, 4)
        .map((tp, i) => `${i + 1}. ${tp.opener}\n   *Why:* ${tp.rationale}`)
        .join('\n\n')}`,
      citations: cites,
    }
  }

  // --- questions ---
  if (/\bquestion|ask(ing)? (them|the|about)|questions to|what should i ask/.test(lower)) {
    briefing.questions.forEach((q) => q.evidence.forEach((id) => cite(id)))
    return {
      answer: `Seven questions worth the room:\n\n${briefing.questions
        .map((q, i) => `${i + 1}. **${q.question}**\n   *Why it works:* ${q.why}`)
        .join('\n\n')}`,
      citations: cites,
    }
  }

  // --- people ---
  if (/who (works|is there|are (the|our))|key people|team|leadership|contact|who will i meet/.test(lower)) {
    return {
      answer: `People you'll want to know about:\n\n${briefing.snapshot.keyPeople
        .map((p) => `- **${p.name}** — ${p.role}${p.note ? `\n  ${p.note}` : ''}`)
        .join('\n')}`,
      citations: [],
    }
  }

  // --- generic retrieval ---
  if (hits.length) {
    const top = hits.slice(0, 3)
    top.forEach((h) => cite(h.n))
    const lead = top[0].n
    return {
      answer: `Based on the ${briefing.windowDays}-day window, here's what the coverage actually says:\n\n${top
        .map(
          (h, i) =>
            `${i + 1}. **${h.n.headline}**  \n${h.n.summary}  \n*${h.n.source} · ${h.n.category} · ${h.n.sentiment}*  \n→ ${h.n.whyItMatters}`,
        )
        .join('\n\n')}\n\n${
        lead ? `If you want one thread to pull, start with: *"${lead.headline}"* — it has the most downstream coverage.` : ''
      }`,
      citations: cites,
    }
  }

  // --- fallback: say what is actually known ---
  return {
    answer: `I don't have anything in the ${briefing.windowDays}-day window that speaks directly to that.\n\nWhat I do have on **${name}**:\n${briefing.grounding
      .slice(0, 3)
      .map((g) => `- ${g}`)
      .join('\n')}\n\nTry naming a category — funding, leadership, litigation, customers — or ask for the risk summary.`,
    citations: [],
  }
}

/* ------------------------------------------------------------------ *
 * Stage 5 one-page brief
 * ------------------------------------------------------------------ */
import type { OnePageBrief, OnePageRequest } from '../types'

function toWireOnePage(req: OnePageRequest): Record<string, unknown> {
  return {
    entityName: req.entityName,
    entityType: req.entityType,
    meetingAt: req.meetingAt,
    meetingContext: req.meetingContext,
    windowDays: req.windowDays ?? 30,
    researchSessionId: req.researchSessionId,
  }
}

export async function generateOnePager(req: OnePageRequest, signal?: AbortSignal): Promise<OnePageBrief> {
  return http.post<OnePageBrief>('/one-pager', toWireOnePage(req), { signal, timeoutMs: 180_000 })
}

export async function downloadOnePagerPdf(req: OnePageRequest): Promise<void> {
  const blob = await http.blob('/one-pager/pdf', {
    method: 'POST',
    body: toWireOnePage(req),
    timeoutMs: 180_000,
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `prebrief-${req.entityName.replace(/\s+/g, '-').toLowerCase().slice(0, 40)}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

export async function downloadOnePagerJson(req: OnePageRequest): Promise<void> {
  const data = await http.post<unknown>('/one-pager/json', toWireOnePage(req), { timeoutMs: 180_000 })
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `prebrief-${req.entityName.replace(/\s+/g, '-').toLowerCase().slice(0, 40)}.json`
  a.click()
  URL.revokeObjectURL(url)
}
