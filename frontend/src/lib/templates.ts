import type { NewsCategory } from '../types'

export interface Template {
  h: string
  s: string
  w: string
  /** -1 negative, 0 neutral, 1 positive */
  tone: -1 | 0 | 1
  /** relative likelihood weight */
  weight?: number
}

/**
 * Tokens: {company} {person} {person2} {product} {investor} {city} {cityShort} {region}
 * {amount} {pct} {move} {topic} {partner} {n} {letter} {exec} {role} {outlet} {media} {domain}
 * {dispute} {team} {mark} {newPerson}
 */
export const TEMPLATES: Record<NewsCategory, Template[]> = {
  funding: [
    {
      h: '{company} raises {amount} in Series {letter} round led by {investor}',
      s: '{investor} led a {amount} Series {letter} round for {company}, valuing the business above its previous mark.',
      w: 'A fresh primary raise gives the team more optionality and signals investor conviction — worth knowing what they intend to spend it on.',
      tone: 1,
    },
    {
      h: '{company} lands {amount} to expand {region} operations',
      s: 'The company said the {amount} facility will fund hiring and go-to-market expansion across {region}.',
      w: 'Capital tied to a specific region usually comes with local hiring and partner targets that show up in the roadmap.',
      tone: 0,
    },
    {
      h: '{company} closes {amount} debt facility, avoids equity raise',
      s: '{company} arranged a {amount} debt facility rather than taking a new equity round.',
      w: 'Choosing debt over dilution usually signals confidence in near-term cash generation; it also raises questions about covenants.',
      tone: 0,
    },
    {
      h: 'Investors reportedly pass on {company} at a {mark} valuation',
      s: 'Late-stage investors walked away from a marketed round that would have implied roughly {mark} in valuation.',
      w: 'A passed round is the most direct signal of a valuation reset, and it changes the conversation about headcount and pricing.',
      tone: -1,
    },
  ],
  earnings: [
    {
      h: '{company} posts {pct}% revenue growth as {topic} expands',
      s: '{company} reported revenue growth of {pct}% with gains concentrated in {topic}.',
      w: 'Growth quality tells you which part of the business to lead with and which part to probe.',
      tone: 1,
    },
    {
      h: '{company} misses estimates on {topic}, cuts outlook',
      s: '{company} reported results below consensus and trimmed its outlook, citing slower {topic}.',
      w: 'A guidance cut is the single most common reason a meeting starts from a defensive place — go in knowing what moved.',
      tone: -1,
    },
    {
      h: '{company} hits profitability for the first time',
      s: '{company} reported its first profitable quarter, with operating margin turning positive.',
      w: 'Crossing into profitability changes the fundamental conversation from runway to allocation of that profit.',
      tone: 1,
    },
    {
      h: '{company} revenue flat, {topic} remains the swing factor',
      s: 'Quarterly revenue was broadly flat, with {topic} determining whether growth returns.',
      w: 'Flat revenue with one swing factor usually means the meeting should test that factor directly.',
      tone: 0,
    },
  ],
  product: [
    {
      h: '{company} ships {product}, promising {topic} gains',
      s: 'The new {product} release focuses on {topic} and is available to all customers from launch.',
      w: 'A shipping release is a safe opener — asking what it displaces gets you more than asking whether it works.',
      tone: 1,
    },
    {
      h: '{company} open-sources core {product} technology',
      s: '{company} moved the core of {product} to an open licence, publishing the model weights and training code.',
      w: 'Open-sourcing is usually a distribution or ecosystem play; understanding the monetization path is the real question.',
      tone: 1,
    },
    {
      h: '{company} rolls back {product} release after {topic} complaints',
      s: '{company} withdrew a recent {product} update following customer reports tied to {topic}.',
      w: 'A rollback is a live reliability issue — it is a factual, non-confrontational topic that opens useful technical conversation.',
      tone: -1,
    },
    {
      h: '{company} previews {product} roadmap at developer event',
      s: 'At its developer event {company} outlined the next two quarters of {product} work.',
      w: 'Roadmap previews tell you what the team believes is next — ask what is deliberately absent.',
      tone: 0,
    },
  ],
  partnerships: [
    {
      h: '{company} signs {partner} to bring {product} to {region}',
      s: '{company} and {partner} announced a multi-year partnership covering {product} distribution in {region}.',
      w: 'Distribution partnerships quietly define which markets a company can win; this one just got bigger.',
      tone: 1,
    },
    {
      h: '{company} and {partner} integrate {product} into enterprise suite',
      s: 'The companies connected {product} with {partner} enterprise tooling, enabling shared identity and reporting.',
      w: 'Integration depth is a leading indicator of enterprise stickiness — worth confirming who owns the relationship.',
      tone: 1,
    },
    {
      h: '{company} partnership with {partner} comes under scrutiny',
      s: 'Regulators and customers alike have questioned {company}’s arrangement with {partner}.',
      w: 'A questioned partnership becomes a reputational item — expect it to come up whether or not you raise it.',
      tone: -1,
    },
  ],
  leadership: [
    {
      h: '{exec} to step down as {company} CEO, {person2} named successor',
      s: '{exec} will leave {company}, with {person2} taking the chief executive role after an internal transition.',
      w: 'A leadership transition changes who you are actually meeting and what authority their answers carry.',
      tone: 0,
    },
    {
      h: '{company} appoints {newPerson} as {role}',
      s: '{company} named {newPerson} as {role}, joining from a peer in the industry.',
      w: 'New leadership hires usually carry a 90-day agenda — that agenda is often what they want to discuss.',
      tone: 0,
    },
    {
      h: '{exec} increases stake in {company} after results',
      s: '{exec} bought a meaningful stake in {company} following the latest quarterly results.',
      w: 'Insider buying aligns the person in front of you with the equity outcome — useful context for direct questions.',
      tone: 1,
    },
    {
      h: '{company} restructures leadership team amid {topic} push',
      s: '{company} reorganised several leadership functions as it pushes harder on {topic}.',
      w: 'Reorgs usually signal accountability being reassigned; that tells you which function owns the next milestone.',
      tone: 0,
    },
  ],
  regulation: [
    {
      h: 'Regulators open inquiry into {company} over {topic}',
      s: 'A regulator opened a formal inquiry into how {company} handles {topic}.',
      w: 'An open inquiry is material and usually known internally — acknowledging it early protects trust in the room.',
      tone: -1,
    },
    {
      h: '{company} wins regulatory clearance in {region} on {topic}',
      s: '{company} received regulatory clearance in {region} on how it handles {topic}.',
      w: 'Approvals remove a gating risk that was likely being modelled internally; it frees up a growth lever.',
      tone: 1,
    },
    {
      h: '{company} publishes transparency report on {topic}',
      s: '{company} released a detailed disclosure on how it handles {topic} and its supply chain.',
      w: 'Proactive disclosure is a posture signal — it indicates how the team expects to be challenged.',
      tone: 0,
    },
  ],
  litigation: [
    {
      h: '{company} sued over {topic} by former employees',
      s: 'A group of former employees filed a claim against {company}, centred on {topic}.',
      w: 'Employment litigation surfaces internal culture facts that rarely appear in any deck.',
      tone: -1,
    },
    {
      h: 'Judge sets hearing date in {company} case',
      s: 'The court scheduled a hearing in the dispute involving {company}, with a decision expected within the quarter.',
      w: 'A dated hearing is a concrete timeline you can ask about without being accusatory.',
      tone: -1,
    },
    {
      h: '{company} settles dispute without admitting fault',
      s: '{company} settled the matter confidentially, with no admission of wrongdoing.',
      w: 'Confidential settlements are rarely fully settled internally — ask what changed in policy.',
      tone: 0,
    },
  ],
  markets: [
    {
      h: '{company} shares {move} as {topic} comes into focus',
      s: '{company} stock moved {move} as investors focused on {topic}.',
      w: 'How the market received the last update is the baseline expectation they will be measuring against in the room.',
      tone: 1,
    },
    {
      h: '{company} valuation reported at {mark} in secondary sale',
      s: 'A secondary transaction valued {company} at approximately {mark}.',
      w: 'Secondary marks are the market’s most honest price — it is often more useful than the last primary round.',
      tone: 0,
    },
    {
      h: 'Short-seller report targets {company} accounting over {dispute}',
      s: 'A short-seller published a report disputing how {company} accounts for {dispute} in its {domain} disclosure.',
      w: 'Accusations of this kind define the defensive posture — know the substance before you ask anything adjacent.',
      tone: -1,
    },
  ],
  customers: [
    {
      h: '{partner} signs {company} for {topic} across {region}',
      s: '{partner} selected {product} for {topic} across its {region} operations.',
      w: 'Named enterprise wins show what actually sells — the selection criteria they used is worth copying.',
      tone: 1,
    },
    {
      h: '{company} renews key account despite competitive bidding',
      s: '{company} retained a major account through a renewal cycle in which two competitors bid.',
      w: 'Winning a contested renewal is the clearest evidence of product pull versus contract inertia.',
      tone: 1,
    },
    {
      h: '{company} loses {partner} as customer',
      s: '{company} confirmed that {partner} moved its business to a competing provider.',
      w: 'Churn has a cause that is usually known internally and rarely explained externally — this is the best diagnostic question you can ask.',
      tone: -1,
    },
  ],
  expansion: [
    {
      h: '{company} opens {cityShort} office',
      s: '{company} opened a new office in {cityShort}, its third in that market.',
      w: 'A new office is a bet on revenue that has not landed yet — useful for testing conviction.',
      tone: 1,
    },
    {
      h: '{company} to hire {n} in {region} over next year',
      s: '{company} plans to add {n} roles in {region}, concentrated in engineering and go-to-market.',
      w: 'Hiring plans are the closest thing to a public forecast they will give you.',
      tone: 1,
    },
    {
      h: '{company} scales back expansion in {region}',
      s: '{company} paused hiring and new deployments in {region} as costs came under pressure.',
      w: 'A pullback in one region while expanding in another is a prioritisation signal you can map directly.',
      tone: -1,
    },
  ],
  acquisition: [
    {
      h: '{company} acquires {partner} for {amount}',
      s: '{company} agreed to buy {partner} for {amount}, adding {product} capabilities to its platform.',
      w: 'Acquisitions reveal what a company thinks it cannot build — that is often the fastest read on their strategy.',
      tone: 1,
    },
    {
      h: '{company} in talks to acquire {partner}',
      s: 'Reports indicate {company} is in advanced talks to acquire {partner}.',
      w: 'Unconfirmed deals are safe to raise neutrally and will tell you how candid they intend to be.',
      tone: 0,
    },
    {
      h: '{company} divests {product} line',
      s: '{company} agreed to sell its {product} business, refocusing on the core platform.',
      w: 'Divestitures are usually about focus and capital discipline — the proceeds tell you what they will do next.',
      tone: 0,
    },
  ],
  hiring: [
    {
      h: '{company} names {newPerson} head of {team}',
      s: '{company} appointed {newPerson} to lead {team}, a newly consolidated function.',
      w: 'A new head of function means their priorities are the priorities for the next two quarters.',
      tone: 0,
    },
    {
      h: '{company} to hire {n} across {role} teams',
      s: '{company} confirmed {n} open roles, most of them in {role} functions.',
      w: 'Role mix tells you where the constraint is believed to be, whether or not that is true.',
      tone: 1,
    },
    {
      h: 'Layoffs at {company} affect {n} employees',
      s: '{company} restructured teams, cutting {n} roles concentrated in a single function.',
      w: 'Layoffs change who in the room can answer for what — and they are usually under-discussed externally.',
      tone: -1,
    },
  ],
  social: [
    {
      h: '{exec} calls {topic} "the defining question of the next decade"',
      s: 'In a {media} appearance, {exec} framed {topic} as the central strategic question for the industry.',
      w: 'Their own framing tells you the language they want to use — borrowing it keeps the conversation on their terms.',
      tone: 0,
    },
    {
      h: '{company} trends after {media} segment on {product}',
      s: 'A {media} segment about {product} drew significant attention and renewed discussion of {company}.',
      w: 'Public attention shifts the agenda — there may be a narrative they want to steer in your meeting.',
      tone: 0,
    },
    {
      h: '{exec} criticises competitors on {topic}',
      s: 'Speaking publicly, {exec} took a direct aim at rivals over {topic}.',
      w: 'How they describe competitors in public is how they want to position against your alternatives.',
      tone: -1,
    },
  ],
  analysis: [
    {
      h: 'Analysts split on whether {company} can sustain {pct}% growth',
      s: 'Sell-side commentary diverged sharply on whether {company} can hold its current growth trajectory.',
      w: 'When the street disagrees, ask which side of the debate the internal numbers support — it surfaces real information.',
      tone: 0,
    },
    {
      h: 'What {company}’s {product} launch means for {region} enterprise budgets',
      s: 'An analysis of {company}’s release argues it reshapes how {region} enterprises budget for {topic}.',
      w: 'Framing you can borrow for the meeting — especially the competitive comparison they assume.',
      tone: 0,
    },
    {
      h: 'The underrated question behind {company}’s {topic} strategy',
      s: 'A widely shared analysis argues the real debate about {company} is not the one being discussed publicly.',
      w: 'Naming the unstated debate gets you a deeper answer than the headline topic allows.',
      tone: 0,
    },
  ],
}

/**
 * Conversational openers, one set per category, each tagged with the tone of the
 * story it fits. The agent picks the opener whose tone matches the item, so a
 * positive result never gets an "I saw it disappointed the street" opener.
 */
export interface Opener {
  /** -1 negative story, 0 neutral, 1 positive */
  tone: -1 | 0 | 1
  text: string
}

export const OPENERS: Record<NewsCategory, Opener[]> = {
  funding: [
    { tone: 1, text: "I've been following the raise — can you walk me through where the money is actually going?" },
    { tone: 0, text: 'A raise like that usually comes with big expectations. What are you promising the board?' },
    { tone: -1, text: 'A passed round is a hard signal. How are you thinking about it from here?' },
  ],
  earnings: [
    { tone: 1, text: 'That result landed well. How are you thinking about the next quarter?' },
    { tone: 0, text: "There's a lot in that number. Which part of it would you point a new investor at?" },
    { tone: -1, text: "The result was not what the street expected, I think. What do you read from it?" },
  ],
  product: [
    { tone: 1, text: 'The release landed well. What were you trying to make possible with it?' },
    { tone: 0, text: 'I want to understand what problem {product} was built for — not what it does.' },
    { tone: -1, text: "I've seen some grumbling about {product}. What's going on there?" },
  ],
  partnerships: [
    { tone: 1, text: 'The {partner} arrangement is interesting. How did that conversation start?' },
    { tone: 0, text: 'Partnerships either compound or become noise. What is this one actually for?' },
    { tone: -1, text: 'I saw the arrangement came under scrutiny. How are you handling that?' },
  ],
  leadership: [
    { tone: 1, text: 'I noticed some movement on the leadership team. How has that changed the day-to-day?' },
    { tone: 0, text: 'New leadership usually means new priorities. What are yours now?' },
    { tone: -1, text: 'I saw the change in roles. How did you handle it with the team?' },
  ],
  regulation: [
    { tone: 1, text: 'The clearance went well. What changed for the team as a result?' },
    { tone: 0, text: 'How much of the roadmap depends on how that resolves?' },
    { tone: -1, text: 'There was a regulatory development. How are you thinking about it?' },
  ],
  litigation: [
    { tone: 1, text: 'The matter seems to have been settled. What changed in policy as a result?' },
    { tone: 0, text: 'I saw the legal coverage. How are you handling it?' },
    { tone: -1, text: 'I saw the legal coverage. How much does it distract the team, honestly?' },
  ],
  markets: [
    { tone: 1, text: 'The market liked it. What do you make of the reaction?' },
    { tone: 0, text: 'How do you read what the market is pricing in?' },
    { tone: -1, text: 'The market took that badly. How are you reading it?' },
  ],
  customers: [
    { tone: 1, text: 'I noticed the {partner} win. What made the difference in that evaluation?' },
    { tone: 0, text: 'What do your best customers do that the rest do not?' },
    { tone: -1, text: 'I saw the churn. What caused it?' },
  ],
  expansion: [
    { tone: 1, text: "I saw you're expanding. What's driving the timing?" },
    { tone: 0, text: 'Opening up a new market is a big commitment. How confident are you in the numbers?' },
    { tone: -1, text: 'I saw you scaled back. What changed in the numbers?' },
  ],
  acquisition: [
    { tone: 1, text: 'The {partner} acquisition is interesting. What does it change day to day?' },
    { tone: 0, text: 'What did you buy that you could not have built?' },
    { tone: -1, text: 'How are you thinking about integrating the teams?' },
  ],
  hiring: [
    { tone: 1, text: 'I saw the hiring plan. What is behind those numbers?' },
    { tone: 0, text: 'Where is the constraint you are actually hiring against?' },
    { tone: -1, text: 'I saw the restructuring. How did you land it with the team?' },
  ],
  social: [
    { tone: 1, text: 'I listened to the {media}. What were you trying to get across?' },
    { tone: 0, text: 'That framing is interesting. Do you believe it?' },
    { tone: -1, text: 'What was the subtext of saying that publicly?' },
  ],
  analysis: [
    { tone: 1, text: "I've read the analyst commentary. Do you agree with it?" },
    { tone: 0, text: 'The consensus seems to assume something. What are they getting wrong?' },
    { tone: -1, text: 'If the analysts are right, what do you do differently?' },
  ],
}

/** Pick the opener that best matches the tone of the story. */
export function pickOpener(rng: () => number, category: NewsCategory, tone: -1 | 0 | 1): string {
  const bank = OPENERS[category] ?? OPENERS.analysis
  const exact = bank.filter((o) => o.tone === tone)
  const pool = exact.length ? exact : bank
  return pool[Math.floor(rng() * pool.length) % pool.length].text
}

export const CATEGORY_LABEL: Record<NewsCategory, string> = {  funding: 'Funding',
  earnings: 'Earnings',
  product: 'Product',
  partnerships: 'Partnerships',
  leadership: 'Leadership',
  regulation: 'Regulation',
  litigation: 'Litigation',
  markets: 'Markets',
  customers: 'Customers',
  expansion: 'Expansion',
  acquisition: 'M&A',
  hiring: 'Hiring',
  social: 'Public voice',
  analysis: 'Analysis',
}

export const CATEGORY_ORDER: NewsCategory[] = [
  'funding', 'earnings', 'product', 'partnerships', 'leadership', 'regulation', 'litigation',
  'markets', 'customers', 'expansion', 'acquisition', 'hiring', 'social', 'analysis',
]
