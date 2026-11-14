/* ------------------------------------------------------------------ *
 * PreBrief domain model
 * The shapes here are the exact contract the backend must return.
 * See README.md -> "Backend contract".
 * ------------------------------------------------------------------ */

export type SubjectType = 'company' | 'person'
export type SubjectTypeInput = SubjectType | 'auto'

export type Sentiment = 'positive' | 'neutral' | 'negative'

export type NewsCategory =
  | 'funding'
  | 'earnings'
  | 'product'
  | 'partnerships'
  | 'leadership'
  | 'regulation'
  | 'litigation'
  | 'markets'
  | 'customers'
  | 'expansion'
  | 'acquisition'
  | 'hiring'
  | 'social'
  | 'analysis'

export interface NewsItem {
  id: string
  headline: string
  /** 1–2 sentence factual summary of what happened. */
  summary: string
  /** Why this matters for the upcoming meeting. */
  whyItMatters: string
  source: string
  sourceUrl?: string
  publishedAt: string
  category: NewsCategory
  sentiment: Sentiment
  /** 1 = minor, 2 = notable, 3 = major. */
  impact: 1 | 2 | 3
  entities: string[]
  /** false when the item falls outside the active 30-day research window. */
  inWindow: boolean
  /** Headline items are surfaced on the snapshot surface. */
  isKey?: boolean
  /** A natural way to open this item in conversation. */
  opener?: string
  /** Article-linked thumbnail (from the source page), if available. */
  imageUrl?: string
  imageSource?: string
  clusterId?: string
  relevanceScore?: number
  /** True when sentiment/impact are heuristic, not verified facts. */
  isInterpretation?: boolean
}

export interface ImageAsset {
  id: string
  url: string
  thumbnailUrl?: string
  title?: string
  altText?: string
  category: string
  sourcePageUrl?: string
  sourceName?: string
  attribution?: string
  licenseNote?: string
  retrievedAt: string
  confidence?: string
}

export interface BriefFact {
  label: string
  value: string
  hint?: string
}

export interface KeyPerson {
  name: string
  role: string
  note?: string
}

export interface Snapshot {
  type: SubjectType
  name: string
  legalName?: string
  tagline: string
  website?: string
  sector?: string
  headquarters?: string
  founded?: string
  employeeCount?: string
  revenue?: string
  funding?: string
  valuation?: string
  ticker?: string
  tags: string[]
  facts: BriefFact[]
  keyPeople: KeyPerson[]
  /** e.g. "Competitor: Acme" — context chips for the meeting. */
  watchlist: string[]
}

export type SignalKind = 'opportunity' | 'risk' | 'watch'

export interface Signal {
  id: string
  kind: SignalKind
  title: string
  detail: string
  /** News ids backing this signal. */
  evidence: string[]
  severity: 1 | 2 | 3
}

export interface TalkingPoint {
  id: string
  text: string
  rationale: string
  /** A natural way to open the topic. */
  opener: string
  /** News ids backing this point. */
  evidence: string[]
}

export type QuestionCategory = 'business' | 'product' | 'strategy' | 'team' | 'market'

export interface OpenQuestion {
  id: string
  question: string
  why: string
  category: QuestionCategory
  /** News ids backing this question. */
  evidence: string[]
}

export interface SourceEntry {
  id: string
  name: string
  url?: string
  publishedAt: string
  headline: string
  category: NewsCategory
  /** false when the item sits outside the active research window. */
  inWindow: boolean
}

export interface SentimentPoint {
  date: string
  /** -1 (very negative) … +1 (very positive). null = no coverage that day. */
  score: number | null
  volume: number
}

export interface CoverageSlice {
  category: NewsCategory
  count: number
}

export interface BriefingStats {
  articles: number
  sources: number
  keyItems: number
  avgSentiment: number
  daysCovered: number
  categoriesCovered: number
}

export interface BriefingResult {
  id: string
  subject: string
  type: SubjectType
  generatedAt: string
  windowDays: number
  windowStart: string
  windowEnd: string
  snapshot: Snapshot
  news: NewsItem[]
  signals: Signal[]
  talkingPoints: TalkingPoint[]
  questions: OpenQuestion[]
  sources: SourceEntry[]
  sentimentTrend: SentimentPoint[]
  coverage: CoverageSlice[]
  stats: BriefingStats
  /** Grounding lines the follow-up chat agent is allowed to cite. */
  grounding: string[]
  /** Set when the payload came from the demo corpus rather than a live backend. */
  synthetic?: boolean
  /** Visual profile / gallery from image discovery. */
  images?: ImageAsset[]
}

export interface BriefingRequest {
  subject: string
  type: SubjectTypeInput
  days: number
  /** Optional steering, e.g. "fundraising, India expansion". */
  focus?: string
  /** Free-form meeting context. */
  meetingNote?: string
  /** Optional uploaded document IDs to use as research context. */
  documentIds?: string[]
  /** Meeting date/time anchors the 30-day research window (ISO). */
  meetingAt?: string
}

export interface ChatTurn {
  id: string
  role: 'user' | 'agent'
  content: string
  createdAt: string
  citations?: string[]
}

export interface MeetingContext {
  title: string
  date: string
  attendees: string[]
  note: string
}

export interface HistoryEntry {
  id: string
  subject: string
  type: SubjectType
  generatedAt: string
  headline: string
  stats: BriefingStats
  result: BriefingResult
}

/* ---------- Stage 5 one-page brief ---------- */
export interface CitationRef {
  index: number
  sourceId: string
  title: string
  publisher: string
  url: string
  publishedAt?: string
}

export interface BriefBullet {
  text: string
  citationIndexes: number[]
  category?: string
  isAnalysis?: boolean
}

export interface OnePageBrief {
  id: string
  entityName: string
  entityType: 'company' | 'person'
  meetingAt: string
  researchWindowStart: string
  researchWindowEnd: string
  generatedAt: string
  executiveSnapshot: string
  news: BriefBullet[]
  hiresAndLeadership: BriefBullet[]
  productAndServiceLaunches: BriefBullet[]
  whatMatters: BriefBullet[]
  openQuestions: string[]
  citations: CitationRef[]
  limitations: string[]
  researchSessionId?: string
  provider: string
  pageFits: boolean
  overflowNote?: string
}

export interface OnePageRequest {
  entityName: string
  entityType: 'company' | 'person' | 'auto'
  meetingAt: string
  meetingContext?: string
  windowDays?: number
  researchSessionId?: string
}
