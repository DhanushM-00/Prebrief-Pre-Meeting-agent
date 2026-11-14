import { generateBriefing } from '../src/lib/mock.ts'
import { briefingToMarkdown } from '../src/lib/export.ts'

const b = generateBriefing({ subject: 'Helio Grid', type: 'auto', days: 30 })
const md = briefingToMarkdown(b, {
  title: 'Series B partner introduction',
  date: '2026-11-04',
  attendees: ['Dana (VP Partnerships)'],
  note: 'They are raising; we partner in EMEA.',
})

console.log(md.slice(0, 3200))
console.log('\n... [truncated] ...\n')
console.log(md.slice(-1400))
console.log('\n--- STATS ---')
console.log(JSON.stringify(b.stats, null, 2))
console.log('in-window:', b.news.filter((n) => n.inWindow).length, '/ total:', b.news.length)
console.log('talking points:', b.talkingPoints.length, 'questions:', b.questions.length, 'signals:', b.signals.length)
console.log('trend points:', b.sentimentTrend.length, 'nulls:', b.sentimentTrend.filter((p) => p.score === null).length)
console.log('\n--- OPENERS ---')
b.talkingPoints.forEach((t) => console.log('•', t.opener))
console.log('\n--- HEADLINES ---')
b.news.filter((n) => n.inWindow).slice(0, 14).forEach((n) => console.log('•', n.headline, `(${n.category}/${n.sentiment})`))
