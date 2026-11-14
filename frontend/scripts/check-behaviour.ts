import { generateBriefing, detectSubjectType } from '../src/lib/mock.ts'

console.log('--- type detection ---')
for (const s of ['Helio Grid', 'Ada Chen', 'Northwind Robotics', 'Marcus Reyes', 'Ada', 'Quantipay', 'OpenAI Inc.', 'Priya Kapoor']) {
  console.log(`  ${s.padEnd(20)} -> ${detectSubjectType(s)}`)
}

console.log('\n--- person subject ---')
const p = generateBriefing({ subject: 'Ada Chen', type: 'auto', days: 30 })
console.log('type:', p.type, '| name:', p.snapshot.name, '| tagline:', p.snapshot.tagline)
console.log('key people:', p.snapshot.keyPeople.map((k) => `${k.name} (${k.role})`).join('; '))
console.log('items:', p.stats.articles, 'tone:', p.stats.avgSentiment, 'signals:', p.signals.length)
console.log('sample headlines:')
p.news.filter((n) => n.inWindow).slice(0, 6).forEach((n) => console.log('   -', n.headline, `(${n.category}/${n.sentiment})`))
console.log('questions:', p.questions.slice(0, 3).map((q) => q.question))
console.log('opener sample:', p.talkingPoints[1]?.opener)

console.log('\n--- focus steering (fundraising) ---')
const plain = generateBriefing({ subject: 'Quantipay', type: 'company', days: 30 })
const focused = generateBriefing({ subject: 'Quantipay', type: 'company', days: 30, focus: 'fundraising litigation' })
const cats = (b: typeof plain) => {
  const m = new Map<string, number>()
  b.news.filter((n) => n.inWindow).forEach((n) => m.set(n.category, (m.get(n.category) ?? 0) + 1))
  return Object.fromEntries(m)
}
console.log('  plain  :', cats(plain))
console.log('  focused:', cats(focused))

console.log('\n--- window enforcement ---')
for (const days of [7, 30, 90]) {
  const b = generateBriefing({ subject: 'Lumen Bio', type: 'company', days })
  const out = b.news.filter((n) => !n.inWindow)
  const oldest = Math.max(...b.news.filter((n) => n.inWindow).map((n) => (Date.now() - +new Date(n.publishedAt)) / 86400000))
  console.log(`  days=${days}: in-window=${b.news.length - out.length} outside=${out.length} oldest-in-window=${oldest.toFixed(1)}d`)
}

console.log('\n--- determinism ---')
const a = generateBriefing({ subject: 'Helio Grid', type: 'company', days: 30 })
const b = generateBriefing({ subject: 'Helio Grid', type: 'company', days: 30 })
console.log('  same headlines:', JSON.stringify(a.news.map((n) => n.headline)) === JSON.stringify(b.news.map((n) => n.headline)))
