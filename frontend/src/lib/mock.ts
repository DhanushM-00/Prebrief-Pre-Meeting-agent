import type {
  BriefingResult,
  BriefingRequest,
  CoverageSlice,
  KeyPerson,
  NewsCategory,
  NewsItem,
  OpenQuestion,
  QuestionCategory,
  Sentiment,
  Signal,
  Snapshot,
  SubjectType,
  TalkingPoint,
} from '../types'
import {
  ARCHETYPE_BY_SUFFIX,
  COMPANY_ARCHETYPES,
  PERSON_ARCHETYPES,
} from './archetypes'
import {
  ACCOUNTING_DISPUTES,
  CATEGORY_TOPICS,
  CUSTOMERS,
  TEAMS,
  CITY_SHORT,
  COMPANY_PREFIX,
  COMPANY_PRODUCT_NOUNS,
  COMPANY_SUFFIX,
  CITIES,
  FIRST_NAMES,
  INVESTORS,
  LAST_NAMES,
  MEDIA_TYPES,
  OUTLETS,
  PEOPLE_TITLES,
  REGIONS,
  REGIONS_SHORT,
  TOPIC_NOUNS,
  type Archetype,
  type PersonArchetype,
} from './corpus'
import { pickOpener, TEMPLATES } from './templates'
import { chance, daysAgoIso, int, makeRng, pick, slug, type Rng } from './format'

/* ------------------------------------------------------------------ *
 * Subject type detection
 * ------------------------------------------------------------------ */
export function detectSubjectType(input: string): SubjectType {
  const t = input.trim()
  if (!t) return 'company'
  const corporateHint = /\b(inc|inc\.|ltd|ltd\.|llc|plc|gmbh|corp|corporation|co\.|company|group|holdings|labs|systems|technologies|ventures|partners|bank|airlines|motors)\b/i
  if (corporateHint.test(t)) return 'company'
  const words = t.split(/\s+/)
  if (words.length >= 2) {
    const first = words[0].replace(/^(dr|mr|mrs|ms|prof)\.?\s+/i, '')
    if (FIRST_NAMES.some((n) => n.toLowerCase() === first.toLowerCase())) return 'person'
  }
  if (words.length === 1) return 'company'
  return 'company'
}

/* ------------------------------------------------------------------ *
 * Profile synthesis
 * ------------------------------------------------------------------ */
function makeCompanyName(rng: Rng, subject: string): string {
  const t = subject.trim()
  if (!t) return `${pick(rng, COMPANY_PREFIX)} ${pick(rng, COMPANY_SUFFIX)}`
  return t
}

function makePersonName(rng: Rng, subject: string): string {
  const t = subject.trim()
  if (!t) return `${pick(rng, FIRST_NAMES)} ${pick(rng, LAST_NAMES)}`
  return t
}

function archetypeForCompany(rng: Rng, name: string): Archetype {
  const known = ARCHETYPE_BY_SUFFIX[name]
  if (known) return known
  return pick(rng, COMPANY_ARCHETYPES)
}

function money(rng: Rng, min: number, max: number, unit: 'M' | 'B' = 'M') {
  const v = int(rng, min, max)
  return `$${v}${unit}`
}

/** Format a millions figure as $XM or $X.XB. */
function formatMoney(millions: number) {
  return millions >= 1000 ? `$${(millions / 1000).toFixed(1)}B` : `$${millions}M`
}

/** Plain magnitude, e.g. "12" — templates add the % sign. */
function pct(rng: Rng) {
  return String(int(rng, 4, 48))
}

/** Signed move, e.g. "-7%" — templates embed it verbatim. */
function move(rng: Rng) {
  const sign = chance(rng, 0.38) ? '-' : '+'
  return `${sign}${int(rng, 3, 22)}%`
}

interface Ctx {
  company: string
  person: string
  person2: string
  product: string
  investor: string
  city: string
  region: string
  amount: string
  pct: string
  move: string
  topic: string
  partner: string
  n: number
  letter: string
  exec: string
  role: string
  outlet: string
  media: string
  cityShort: string
  domain: string
  dispute: string
  team: string
  mark: string
  newPerson: string
}

function fill(tpl: string, ctx: Ctx): string {
  return tpl.replace(/\{(\w+)\}/g, (_, key: string) => {
    const v = (ctx as unknown as Record<string, string | number>)[key]
    return v === undefined ? '' : String(v)
  })
}

function buildSnapshot(rng: Rng, req: BriefingRequest, type: SubjectType, archetype: Archetype | PersonArchetype): Snapshot {
  if (type === 'person') {
    const name = makePersonName(rng, req.subject)
    const archetype: PersonArchetype = pick(rng, PERSON_ARCHETYPES)
    const company = `${pick(rng, COMPANY_PREFIX)} ${pick(rng, COMPANY_SUFFIX)}`
    const title = pick(rng, PEOPLE_TITLES[archetype])
    const hq = pick(rng, CITIES)
    const sectorMap: Record<PersonArchetype, string> = {
      founder: 'Enterprise software',
      exec: 'Corporate leadership',
      investor: 'Venture capital',
      operator: 'Corporate leadership',
      creator: 'Technology / media',
      advisor: 'Board & advisory',
    }
    const sector = sectorMap[archetype]
    const years = int(rng, 6, 22)
    const keyPeople: KeyPerson[] = [
      { name, role: title, note: `Subject of this briefing · ${company}` },
      {
        name: `${pick(rng, FIRST_NAMES)} ${pick(rng, LAST_NAMES)}`,
        role: 'Chief of Staff',
        note: 'Often the best first call for anything not on the public record',
      },
      {
        name: `${pick(rng, FIRST_NAMES)} ${pick(rng, LAST_NAMES)}`,
        role: 'Head of Communications',
        note: 'Owns external messaging and press timing',
      },
    ]
    const facts = [
      { label: 'Current role', value: `${title}, ${company}`, hint: 'Verified within the research window' },
      { label: 'Base', value: hq, hint: 'Company headquarters' },
      { label: 'Sector', value: sector },
      { label: 'In role', value: `${years} years` },
      { label: 'Prior', value: `${pick(rng, ['Google', 'Stripe', 'Airbnb', 'Sequoia Capital', 'BCG', 'Spotify', 'Databricks', 'Mozilla'])} · ${pick(rng, ['Product', 'Engineering', 'Investment', 'Operations'])}` },
      { label: 'Board seats', value: `${int(rng, 1, 3)}` },
      { label: 'Public presence', value: `${pick(rng, MEDIA_TYPES)} · ${pick(rng, ['~40K', '~120K', '~300K', '~1M'])} followers` },
      { label: 'Notable', value: `Keynote at ${pick(rng, REGIONS_SHORT)} tech conference, ${int(rng, 2023, 2025)}` },
    ]
    return {
      type: 'person',
      name,
      legalName: name,
      tagline: `${title} at ${company}`,
      sector,
      headquarters: hq,
      founded: `${int(rng, 2010, 2022)}`,
      tags: [sector, archetype, `~${years}y tenure`, company],
      facts,
      keyPeople,
      watchlist: [`Employer: ${company}`, `Sector: ${sector}`, `Board & advisors`, `Public statements`],
      website: `${slug(name)}.example.com`,
    }
  }

  const name = makeCompanyName(rng, req.subject)
  const arch = archetype as Archetype
  const hq = pick(rng, CITIES)
  const sectorMap: Record<Archetype, string> = {
    saas: 'B2B Software',
    fintech: 'Financial technology',
    ai: 'Artificial intelligence',
    ecommerce: 'E-commerce',
    hardware: 'Consumer & industrial hardware',
    healthcare: 'Digital health',
    consumer: 'Consumer subscription',
    marketplace: 'Marketplace',
    devtools: 'Developer infrastructure',
    energy: 'Clean energy',
    media: 'Digital media',
  }
  const sector = sectorMap[arch]
  const founded = int(rng, 2008, 2021)
  const employees = int(rng, 40, 4200)
  const product = pick(rng, COMPANY_PRODUCT_NOUNS[arch])
  const stage = pick(rng, ['Seed', 'Series A', 'Series B', 'Series C', 'Series D', 'Growth', 'Public'])
  const revenueBand = `$${floatBand(rng)}M ARR`
  const valuation = stage === 'Public' ? `${money(rng, 400, 9000, 'B')}` : money(rng, 60, 3200, rng() > 0.7 ? 'B' : 'M')

  const keyPeople: KeyPerson[] = [
    { name: `${pick(rng, FIRST_NAMES)} ${pick(rng, LAST_NAMES)}`, role: 'Chief Executive Officer', note: 'Primary external voice' },
    { name: `${pick(rng, FIRST_NAMES)} ${pick(rng, LAST_NAMES)}`, role: 'Chief Financial Officer', note: 'Owns capital allocation narrative' },
    { name: `${pick(rng, FIRST_NAMES)} ${pick(rng, LAST_NAMES)}`, role: 'Chief Technology Officer', note: 'Product and architecture decisions' },
    { name: `${pick(rng, FIRST_NAMES)} ${pick(rng, LAST_NAMES)}`, role: 'Head of Enterprise Sales', note: 'Customer-side perspective' },
  ]

  const facts = [
    { label: 'Stage', value: stage, hint: stage === 'Public' ? 'Listed' : 'Last round 4 months ago' },
    { label: 'Valuation', value: valuation, hint: 'Most recent mark' },
    { label: 'Revenue', value: revenueBand, hint: 'Trailing twelve months' },
    { label: 'Headcount', value: `~${employees.toLocaleString()}` },
    { label: 'Founded', value: `${founded}`, hint: `${new Date().getFullYear() - founded} years operating` },
    { label: 'Product', value: `${product}`, hint: `${sector} platform` },
    { label: 'HQ', value: hq },
    { label: 'Next milestone', value: pick(rng, ['Enterprise GA launch', 'Series D close', 'Europe entity', 'SOC 2 Type II', 'IPO readiness']) },
  ]

  return {
    type: 'company',
    name,
    legalName: `${name}, Inc.`,
    tagline: `${sector} · ${stage} stage`,
    website: `${slug(name)}.example.com`,
    sector,
    headquarters: hq,
    founded: `${founded}`,
    employeeCount: `~${employees.toLocaleString()}`,
    revenue: revenueBand,
    funding: stage === 'Public' ? 'Publicly traded' : money(rng, 8, 180, 'M'),
    valuation,
    ticker: stage === 'Public' ? slug(name).slice(0, 4).toUpperCase() : undefined,
    tags: [sector, stage, hq.split(',')[0], product],
    facts,
    keyPeople,
    watchlist: [
      `Sector: ${sector}`,
      `Stage: ${stage}`,
      `Competitor set: ${pick(rng, ['2 direct', '3 direct', '4 direct', '2 adjacent'])}`,
      `Hiring: ${pick(rng, ['Active', 'Selective', 'Paused'])}`,
    ],
  }
}

/* ------------------------------------------------------------------ *
 * News synthesis
 * ------------------------------------------------------------------ */
function focusBoost(focus: string | undefined, category: NewsCategory): number {
  if (!focus) return 1
  const f = focus.toLowerCase()
  const map: Record<string, RegExp> = {
    funding: /fund|rais|invest|capital|vc/,
    earnings: /earn|revenue|profit|margin|arr/,
    product: /product|feature|launch|roadmap|ai|model/,
    partnerships: /partner|channel|integration|alliance/,
    leadership: /ceo|founder|exec|hire|team|leadership/,
    regulation: /regulat|legal|compliance|law/,
    litigation: /lawsuit|litigat|sue|court|legal/,
    markets: /stock|market|investor|share/,
    customers: /customer|client|churn|renew/,
    expansion: /expand|intl|hiring|market|geograph/,
    acquisition: /acqui|merger|buy|ma\b/,
    hiring: /hire|hiring|recruit|talent/,
    social: /social|media|pr|interview|reputation/,
    analysis: /analysis|trend|market|outlook/,
  }
  return map[category]?.test(f) ? 2.6 : 1
}

function chooseCategories(rng: Rng, archetype: Archetype | PersonArchetype, count: number, focus?: string): NewsCategory[] {
  const companyBias: Record<string, NewsCategory[]> = {
    saas: ['product', 'earnings', 'customers', 'leadership', 'partnerships'],
    fintech: ['regulation', 'funding', 'partnerships', 'markets', 'litigation'],
    ai: ['product', 'funding', 'acquisition', 'partnerships', 'regulation'],
    ecommerce: ['expansion', 'markets', 'customers', 'funding', 'partnerships'],
    hardware: ['expansion', 'acquisition', 'markets', 'partnerships'],
    healthcare: ['regulation', 'funding', 'partnerships', 'expansion'],
    consumer: ['markets', 'expansion', 'funding', 'customers'],
    marketplace: ['expansion', 'regulation', 'partnerships', 'litigation'],
    devtools: ['product', 'acquisition', 'hiring', 'analysis'],
    energy: ['expansion', 'markets', 'regulation', 'funding'],
    media: ['social', 'partnerships', 'hiring', 'analysis'],
  }
  const personBias: Record<string, NewsCategory[]> = {
    founder: ['social', 'leadership', 'funding', 'analysis'],
    exec: ['leadership', 'earnings', 'markets', 'social'],
    investor: ['funding', 'analysis', 'acquisition', 'social'],
    operator: ['hiring', 'expansion', 'product', 'analysis'],
    creator: ['social', 'product', 'analysis', 'hiring'],
    advisor: ['analysis', 'leadership', 'social', 'markets'],
  }
  const bias = archetype in companyBias ? companyBias[archetype] : personBias[archetype]
  const all = Object.keys(TEMPLATES) as NewsCategory[]
  const chosen: NewsCategory[] = []
  const pool = [...bias, ...all]
  let guard = 0
  while (chosen.length < count && guard < 500) {
    guard++
    const candidate = pick(rng, pool)
    const weight = focusBoost(focus, candidate) * (bias.includes(candidate) ? 3 : 1)
    if (rng() < Math.min(0.92, weight / 5)) chosen.push(candidate)
  }
  while (chosen.length < count) chosen.push(pick(rng, all))
  return chosen
}

function buildNews(
  rng: Rng,
  req: BriefingRequest,
  snapshot: Snapshot,
  type: SubjectType,
  archetype: Archetype | PersonArchetype,
): NewsItem[] {
  const company = type === 'company' ? snapshot.name : (snapshot.watchlist[0]?.replace('Employer: ', '') ?? snapshot.name)
  const person = type === 'person' ? snapshot.name : snapshot.keyPeople[0]?.name ?? 'the CEO'
  const exec = type === 'person' ? snapshot.name : snapshot.keyPeople[0]?.name ?? 'the CEO'
  const product =
    type === 'company'
      ? (snapshot.tags.find((t) => COMPANY_PRODUCT_NOUNS[archetype as Archetype]?.includes(t)) ??
         pick(rng, COMPANY_PRODUCT_NOUNS[archetype as Archetype] ?? COMPANY_PRODUCT_NOUNS.saas))
      : pick(rng, COMPANY_PRODUCT_NOUNS.saas)

  // Keep every valuation figure in the corpus consistent with the snapshot's
  // valuation instead of inventing a new number per story.
  const valuationMillions = parseValuation(snapshot.valuation)
  const markMillions = Math.max(
    5,
    Math.round(valuationMillions * (0.78 + rng() * 0.44)),
  )
  const stageLetter = SERIES_LETTER[snapshot.facts.find((f) => f.label === 'Stage')?.value ?? ''] ?? 'B'

  const ctxBase: Omit<
    Ctx,
    | 'topic'
    | 'partner'
    | 'region'
    | 'city'
    | 'amount'
    | 'pct'
    | 'move'
    | 'n'
    | 'letter'
    | 'outlet'
    | 'media'
    | 'investor'
    | 'cityShort'
    | 'domain'
    | 'dispute'
    | 'team'
    | 'mark'
    | 'newPerson'
  > = {
    company,
    person,
    person2: `${pick(rng, FIRST_NAMES)} ${pick(rng, LAST_NAMES)}`,
    product,
    exec,
    role: pick(rng, ['Engineering', 'Product', 'Revenue', 'Operations', 'Policy']),
  }

  const count = int(rng, 26, 38)
  const categories = chooseCategories(rng, archetype, count, req.focus)

  // Pre-draw when each item was published, then assign categories to those
  // slots. Focus categories are placed into in-window slots first, so asking
  // for "litigation" always surfaces litigation inside the brief rather than
  // letting it fall outside the window.
  const slots: { dayOffset: number; inWindow: boolean }[] = []
  for (let i = 0; i < count; i++) {
    // 0..43, weighted toward recent so short windows still return real coverage
    const dayOffset = Math.floor(Math.pow(rng(), 1.7) * 44)
    slots.push({ dayOffset, inWindow: dayOffset < req.days })
  }

  const inWinSlots = slots.filter((s) => s.inWindow)
  const outSlots = slots.filter((s) => !s.inWindow)
  const focusRelevant = categories.filter((c) => focusBoost(req.focus, c) > 1)
  const neutralCats = categories.filter((c) => focusBoost(req.focus, c) === 1)
  const winCount = inWinSlots.length
  const inWinCats = [
    ...focusRelevant.slice(0, winCount),
    ...neutralCats.slice(0, Math.max(0, winCount - focusRelevant.length)),
  ]
  const outCats = [
    ...focusRelevant.slice(winCount),
    ...neutralCats.slice(Math.max(0, winCount - focusRelevant.length)),
  ]
  const plan: { category: NewsCategory; slot: { dayOffset: number; inWindow: boolean } }[] = [
    ...inWinCats.map((category, i) => ({ category, slot: inWinSlots[i] })),
    ...outCats.map((category, i) => ({ category, slot: outSlots[i] })),
  ]

  const items: NewsItem[] = []
  const usedHeadlines = new Set<string>()
  const mood = (rng() - 0.5) * 1.1

  for (let i = 0; i < plan.length; i++) {
    const { category, slot } = plan[i]
    let tpl = pick(rng, TEMPLATES[category])
    const ctx: Ctx = {
      ...ctxBase,
      investor: pick(rng, INVESTORS),
      city: pick(rng, CITIES),
      region: pick(rng, REGIONS),
      // Deal sizes scale with the company rather than being rolled blind —
      // a $143B debt facility on a $1B company destroys the illusion.
      amount: formatMoney(
        Math.max(4, Math.round(valuationMillions * (0.05 + rng() * 0.4))),
      ),
      pct: pct(rng),
      move: move(rng),
      topic: pick(rng, CATEGORY_TOPICS[category] ?? TOPIC_NOUNS),
      partner:
        category === 'customers'
          ? pick(rng, CUSTOMERS)
          : `${pick(rng, COMPANY_PREFIX)} ${pick(rng, COMPANY_SUFFIX)}`,
      n: int(rng, 12, 340),
      outlet: pick(rng, OUTLETS),
      media: pick(rng, MEDIA_TYPES),
      cityShort: pick(rng, CITY_SHORT),
      domain: pick(rng, ['segment', 'quarterly', 'annual', 'risk-factor', 'revenue-recognition']),
      dispute: pick(rng, ACCOUNTING_DISPUTES),
      team: pick(rng, TEAMS),
      mark: formatMoney(
        Math.max(5, Math.round((markMillions * (0.93 + rng() * 0.14)))),
      ),
      newPerson: `${pick(rng, FIRST_NAMES)} ${pick(rng, LAST_NAMES)}`,
      letter: stageLetter,
    }
    // Headlines must be unique — pick another template from the same category
    // rather than shipping the same story twice.
    let headline = ''
    for (let attempt = 0; attempt < 14; attempt++) {
      headline = fill(tpl.h, ctx)
      if (!usedHeadlines.has(headline)) break
      tpl = pick(rng, TEMPLATES[category])
    }
    if (usedHeadlines.has(headline)) continue
    usedHeadlines.add(headline)

    const summary = fill(tpl.s, ctx)
    const why = fill(tpl.w, ctx)

    const { dayOffset, inWindow } = slot
    const impactRoll = rng()
    const impact: 1 | 2 | 3 = impactRoll > 0.82 ? 3 : impactRoll > 0.48 ? 2 : 1

    // The subject's "month" — some subjects had a good 30 days, some did not.
    // Without this, the template mix alone skews every subject positive.
    let sentiment: Sentiment
    if (tpl.tone === 1) sentiment = mood < -0.5 ? 'neutral' : 'positive'
    else if (tpl.tone === -1) sentiment = mood > 0.5 ? 'neutral' : 'negative'
    // Capital raising is never framed as negative coverage — a bad month does
    // not make landing money into bad news.
    else if (category === 'funding') sentiment = 'neutral'
    else
      sentiment =
        rng() < 0.35
          ? 'neutral'
          : mood > 0.22
            ? 'positive'
            : mood < -0.22
              ? 'negative'
              : 'neutral'
    // A share-price story carries its tone in the move itself — a -12% headline
    // must not end up labelled positive.
    if (tpl.h.includes('{move}')) sentiment = ctx.move.startsWith('-') ? 'negative' : 'positive'

    const cast = [company]
    if (['funding', 'markets'].includes(category)) cast.push(ctx.investor)
    if (['partnerships', 'acquisition', 'customers'].includes(category)) cast.push(ctx.partner)
    if (['leadership', 'hiring', 'social'].includes(category)) cast.push(exec)
    // Entities should be the ones the headline actually names.
    if (category === 'expansion') cast.push(ctx.region)
    if (category === 'hiring') cast.push(ctx.team)
    const entities = Array.from(new Set(cast.filter(Boolean))).slice(0, 4)

    // The opener follows the item's final sentiment, not the template default —
    // otherwise a story can carry a positive badge and a "that disappointed the
    // street" opener.
    const openerTone = sentiment === 'positive' ? 1 : sentiment === 'negative' ? -1 : 0
    const opener = fill(pickOpener(rng, category, openerTone), ctx)

    items.push({
      id: `n-${i}-${slug(headline).slice(0, 10)}`,
      headline,
      summary,
      whyItMatters: why,
      source: ctx.outlet,
      publishedAt: daysAgoIso(dayOffset, int(rng, 6, 20), pick(rng, [0, 5, 12, 18, 25, 31, 38, 44, 51])),
      category,
      sentiment,
      impact,
      entities,
      inWindow,
      isKey: inWindow && impact === 3 && rng() > 0.35,
      opener,
    })
  }

  return items.sort((a, b) => +new Date(b.publishedAt) - +new Date(a.publishedAt))
}

/* ------------------------------------------------------------------ *
 * Derived intelligence
 * ------------------------------------------------------------------ */
function buildSignals(news: NewsItem[]): Signal[] {
  const inWin = news.filter((n) => n.inWindow)
  const signals: Signal[] = []

  const negatives = inWin.filter((n) => n.sentiment === 'negative' && n.impact >= 2)
  const positives = inWin.filter((n) => n.sentiment === 'positive' && n.impact >= 2)

  if (negatives.length) {
    const cluster = negatives.slice(0, 3)
    signals.push({
      id: 'sig-risk-1',
      kind: 'risk',
      title: 'Adverse cluster in the last 30 days',
      detail: `${cluster.length} notable negative items in-window, led by "${truncate(cluster[0].headline, 70)}". Expect this to be on their agenda even if it is not on yours.`,
      evidence: cluster.map((n) => n.id),
      severity: cluster.some((n) => n.impact === 3) ? 3 : 2,
    })
  }

  if (positives.length) {
    const cluster = positives.slice(0, 3)
    signals.push({
      id: 'sig-opp-1',
      kind: 'opportunity',
      title: 'Momentum you can build on',
      detail: `${cluster.length} notable positive items, led by "${truncate(cluster[0].headline, 70)}". Naming something they are proud of — and asking them to extend it — is the cheapest way to build rapport.`,
      evidence: cluster.map((n) => n.id),
      severity: 2,
    })
  }

  const byCategory = new Map<NewsCategory, number>()
  inWin.forEach((n) => byCategory.set(n.category, (byCategory.get(n.category) ?? 0) + 1))
  const topCat = [...byCategory.entries()].sort((a, b) => b[1] - a[1])[0]
  if (topCat) {
    signals.push({
      id: 'sig-watch-1',
      kind: 'watch',
      title: `Narrative is concentrating on ${topCat[0]}`,
      detail: `${topCat[1]} of the ${inWin.length} in-window items touch ${topCat[0]}. Coverage concentration means it is the frame external stakeholders are using — meeting well means meeting inside that frame, or deliberately outside it.`,
      evidence: inWin.filter((n) => n.category === topCat[0]).slice(0, 3).map((n) => n.id),
      severity: 1,
    })
  }

  const spike = inWin.filter((n) => n.impact === 3)
  if (spike.length >= 2) {
    signals.push({
      id: 'sig-watch-2',
      kind: 'watch',
      title: 'Two or more high-impact events in one window',
      detail: `${spike.length} items were classified as high impact. When multiple material events land close together, teams are usually mid-firefight rather than in a reflective state — keep the agenda short.`,
      evidence: spike.slice(0, 3).map((n) => n.id),
      severity: 2,
    })
  }

  if (signals.length === 0) {
    signals.push({
      id: 'sig-watch-0',
      kind: 'watch',
      title: 'Quiet window',
      detail: 'Low-volume coverage in the last 30 days. That cuts both ways: there may be little new to learn, or simply poor public coverage.',
      evidence: inWin.slice(0, 2).map((n) => n.id),
      severity: 1,
    })
  }

  return signals
}

function buildTalkingPoints(news: NewsItem[], snapshot: Snapshot): TalkingPoint[] {
  const inWin = news.filter((n) => n.inWindow)
  const ranked = [...inWin].sort((a, b) => b.impact - a.impact || +new Date(b.publishedAt) - +new Date(a.publishedAt))
  const points: TalkingPoint[] = []

  ranked.slice(0, 5).forEach((n, i) => {
    const opener =
      i === 0
        ? `I'd like to start from something recent: "${truncate(n.headline, 70)}."`
        : (n.opener ?? `I'd like to understand more about ${n.category.toLowerCase()} from your side.`)
    points.push({
      id: `tp-${n.id}`,
      text: n.headline,
      rationale: n.whyItMatters,
      opener,
      evidence: [n.id],
    })
  })

  // A structural point grounded in the profile rather than a headline.
  points.push({
    id: 'tp-profile',
    text: `Anchor the conversation in ${snapshot.type === 'company' ? 'their position in the market' : 'their current mandate'}`,
    rationale:
      snapshot.type === 'company'
        ? `They are ${snapshot.tagline?.toLowerCase() ?? 'positioned'} and headquartered in ${snapshot.headquarters}. Framing the meeting inside their own stated positioning gets an answer rather than a pitch.`
        : `Their role is ${snapshot.tagline}. Understanding the mandate they are measured on explains which questions they can actually answer.`,
    opener: `Before we go further — I would like to understand how you are being measured right now.`,
    evidence: [],
  })

  return points
}

function buildQuestions(news: NewsItem[]): OpenQuestion[] {
  const inWin = news.filter((n) => n.inWindow)
  const questions: OpenQuestion[] = []
  const seen = new Set<string>()

  const bank: { q: string; why: string; cat: QuestionCategory; cat2?: NewsCategory }[] = [
    {
      q: 'What changed in the last 30 days that is not yet public?',
      why: 'Gives them room to be candid without putting a specific claim on the record, and reliably surfaces the internal narrative.',
      cat: 'strategy',
    },
    {
      q: 'What would you do differently if you had twice the current budget?',
      why: 'Reveals their real constraint without asking them to admit it, and gets prioritisation logic instead of a list.',
      cat: 'strategy',
    },
    {
      q: 'Where is the gap between what you have announced and what is actually shipping?',
      why: 'Announcements are lagging indicators; the gap between announced and shipped is where the real risk lives.',
      cat: 'product',
    },
    {
      q: 'What is the assumption in your plan that worries you most?',
      why: 'A high-signal question that is almost always answered honestly, because it asks about doubt rather than performance.',
      cat: 'business',
    },
    {
      q: 'Who is the customer you are least able to serve well right now, and why?',
      why: 'Shows you understand the segmentation, and their answer reveals what is breaking at the edges.',
      cat: 'business',
    },
    {
      q: 'How does this decision look to the team that has to implement it?',
      why: 'Tests whether the plan is believed internally or only defended externally.',
      cat: 'team',
    },
    {
      q: 'What is the competitive move you are most worried about in the next two quarters?',
      why: 'Their answer tells you which competitor to track and what their roadmap is defensive against.',
      cat: 'market',
    },
    {
      q: 'What are you deliberately not doing yet, and when will you start?',
      why: 'Surfaces the sequence behind their roadmap and usually reveals a dependency nobody has mentioned.',
      cat: 'product',
    },
  ]

  const negative = inWin.find((n) => n.sentiment === 'negative' && n.impact >= 2)
  if (negative) {
    questions.push({
      id: 'q-negative',
      question: `How are you thinking about "${truncate(negative.headline, 60)}"?`,
      why: `It was widely covered as a negative development. Asking them to explain it — rather than waiting for them to raise it — usually gets a more complete answer.`,
      category: 'strategy',
      evidence: [negative.id],
    })
  }

  const positive = inWin.find((n) => n.sentiment === 'positive' && n.impact >= 2)
  if (positive) {
    questions.push({
      id: 'q-positive',
      question: `What would need to be true for the momentum behind "${truncate(positive.headline, 55)}" to continue?`,
      why: 'Extends something they are proud of, which reads as interest rather than interrogation, and pulls out their success criteria.',
      category: 'business',
      evidence: [positive.id],
    })
  }

  for (const b of bank) {
    if (questions.length >= 6) break
    if (seen.has(b.q)) continue
    seen.add(b.q)
    const evidence =
      b.cat2 && inWin.find((n) => n.category === b.cat2)?.id
        ? [inWin.find((n) => n.category === b.cat2)!.id]
        : []
    questions.push({ id: `q-${questions.length}`, question: b.q, why: b.why, category: b.cat, evidence })
  }

  const noise = inWin.find((n) => n.category === 'expansion' || n.category === 'hiring')
  if (noise && questions.length < 7) {
    questions.push({
      id: 'q-plan',
      question: `How confident are you in the hiring and expansion plan you have described publicly?`,
      why: 'Public plans are usually a floor rather than a forecast. Their real number is the useful one.',
      category: 'team',
      evidence: [noise.id],
    })
  }

  return questions.slice(0, 7)
}

function buildTrend(news: NewsItem[], days: number) {
  const today = new Date()
  const buckets = new Map<string, { score: number; count: number }>()
  for (let i = 0; i < days; i++) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    buckets.set(d.toISOString().slice(0, 10), { score: 0, count: 0 })
  }
  news.forEach((n) => {
    if (!n.inWindow) return
    const key = n.publishedAt.slice(0, 10)
    const b = buckets.get(key)
    if (!b) return
    const v = n.sentiment === 'positive' ? 1 : n.sentiment === 'negative' ? -1 : 0
    b.score += v
    b.count += 1
  })
  const ordered = [...buckets.entries()].sort((a, b) => a[0].localeCompare(b[0]))

  // Tone is reported as a trailing 7-day mean so the line shows trend without
  // drawing a false "neutral" on days nobody wrote about. Volume stays daily and
  // exact, so the reader can always see how much the tone rests on.
  const SMOOTH = 7
  return ordered.map(([date, b], idx) => {
    const from = Math.max(0, idx - (SMOOTH - 1))
    const window = ordered.slice(from, idx + 1)
    const total = window.reduce((acc, [, v]) => acc + v.count, 0)
    const sum = window.reduce((acc, [, v]) => acc + v.score, 0)
    return {
      date,
      score: total ? Number((sum / total).toFixed(2)) : null,
      volume: b.count,
    }
  })
}

function buildCoverage(news: NewsItem[]): CoverageSlice[] {
  const inWin = news.filter((n) => n.inWindow)
  const map = new Map<NewsCategory, number>()
  inWin.forEach((n) => map.set(n.category, (map.get(n.category) ?? 0) + 1))
  return [...map.entries()].map(([category, count]) => ({ category, count })).sort((a, b) => b.count - a.count)
}

/* ------------------------------------------------------------------ *
 * Entry point
 * ------------------------------------------------------------------ */
export function generateBriefing(req: BriefingRequest): BriefingResult {
  const type: SubjectType = req.type === 'auto' ? detectSubjectType(req.subject) : req.type
  const rng = makeRng(`${req.subject.toLowerCase()}|${type}|${req.days}|${req.focus ?? ''}`)
  const archetype: Archetype | PersonArchetype =
    type === 'person' ? pick(rng, PERSON_ARCHETYPES) : archetypeForCompany(rng, req.subject.trim() || 'x')
  const snapshot = buildSnapshot(rng, req, type, archetype)
  const news = buildNews(rng, req, snapshot, type, archetype)
  const inWin = news.filter((n) => n.inWindow)

  const signals = buildSignals(news)
  const talkingPoints = buildTalkingPoints(news, snapshot)
  const questions = buildQuestions(news)
  const sources = news.map((n) => ({
    id: `s-${n.id}`,
    name: n.source,
    url: undefined,
    publishedAt: n.publishedAt,
    headline: n.headline,
    category: n.category,
    inWindow: n.inWindow,
  }))

  const sentimentVals: number[] = inWin.map((n) =>
    n.sentiment === 'positive' ? 1 : n.sentiment === 'negative' ? -1 : 0,
  )
  const avgSentiment = sentimentVals.length
    ? sentimentVals.reduce((a, b) => a + b, 0) / sentimentVals.length
    : 0

  const daysCovered = new Set(inWin.map((n) => n.publishedAt.slice(0, 10))).size
  const distinctSources = new Set(inWin.map((n) => n.source)).size
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - req.days)

  const grounding = [
    `${inWin.length} news items published within the last ${req.days} days.`,
    `Distinct outlets: ${distinctSources}.`,
    `Most-covered categories: ${buildCoverage(news)
      .slice(0, 3)
      .map((c) => c.category)
      .join(', ')}.`,
    `Key people named: ${snapshot.keyPeople.map((k) => `${k.name} (${k.role})`).join('; ')}.`,
    `Stage and positioning: ${snapshot.tagline ?? ''}. ${snapshot.headquarters ?? ''}`.trim(),
  ]

  return {
    id: `b-${slug(req.subject)}-${Date.now()}`,
    subject: req.subject,
    type,
    generatedAt: new Date().toISOString(),
    windowDays: req.days,
    windowStart: start.toISOString(),
    windowEnd: end.toISOString(),
    snapshot,
    news,
    signals,
    talkingPoints,
    questions,
    sources,
    sentimentTrend: buildTrend(news, req.days),
    coverage: buildCoverage(news),
    stats: {
      articles: inWin.length,
      sources: distinctSources,
      keyItems: inWin.filter((n) => n.isKey).length,
      avgSentiment: Number(avgSentiment.toFixed(2)),
      daysCovered,
      categoriesCovered: buildCoverage(news).length,
    },
    grounding,
    synthetic: true,
  }
}

/** "1038M" / "4.2B" -> millions, so every valuation story agrees with the snapshot. */
function parseValuation(v: string | undefined): number {
  if (!v) return 200
  const m = v.match(/\$([\d.]+)\s*([MB])/i)
  if (!m) return 200
  const num = parseFloat(m[1])
  if (Number.isNaN(num)) return 200
  return m[2].toUpperCase() === 'B' ? Math.round(num * 1000) : Math.round(num)
}

/** The next round after the company's current stage. */
const SERIES_LETTER: Record<string, string> = {
  Seed: 'A',
  'Series A': 'B',
  'Series B': 'C',
  'Series C': 'D',
  'Series D': 'E',
  Growth: 'F',
}

function truncate(s: string, n: number) {
  return s.length > n ? `${s.slice(0, n - 1).trimEnd()}…` : s
}

function floatBand(rng: Rng) {
  const v = int(rng, 4, 980)
  return v
}
