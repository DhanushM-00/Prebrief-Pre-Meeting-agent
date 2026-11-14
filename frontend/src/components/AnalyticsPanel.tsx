import { useMemo } from 'react'
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, SectionTitle } from './ui'
import { CATEGORY_LABEL } from '../lib/templates'
import { fmtShortDate } from '../lib/format'
import type { BriefingResult } from '../types'

export function AnalyticsPanel({ briefing }: { briefing: BriefingResult }) {
  const trend = useMemo(
    () =>
      briefing.sentimentTrend.map((p) => ({
        ...p,
        label: fmtShortDate(`${p.date}T00:00:00`),
      })),
    [briefing.sentimentTrend],
  )

  const coverage = useMemo(
    () =>
      briefing.coverage.map((c) => ({
        ...c,
        label: CATEGORY_LABEL[c.category],
      })),
    [briefing.coverage],
  )

  const avg = briefing.stats.avgSentiment
  const tone = avg > 0.15 ? 'positive' : avg < -0.15 ? 'negative' : 'neutral'
  const toneColor =
    tone === 'positive'
      ? 'var(--positive)'
      : tone === 'negative'
        ? 'var(--negative)'
        : 'var(--text-faint)'

  const totalVolume = briefing.sentimentTrend.reduce((a, b) => a + b.volume, 0)
  const peak = useMemo(
    () =>
      briefing.sentimentTrend.reduce(
        (m, p) => (p.volume > m.volume ? p : m),
        briefing.sentimentTrend[0],
      ),
    [briefing.sentimentTrend],
  )

  const maxVolume = Math.max(1, ...briefing.sentimentTrend.map((p) => p.volume))

  return (
    <div className="grid gap-4 lg:grid-cols-5">
      <Card className="lg:col-span-3">
        <SectionTitle
          eyebrow="Signal"
          title={`Sentiment across the ${briefing.windowDays}-day window`}
          count={`${totalVolume} items`}
          action={
            <div className="flex items-center gap-2 text-[11.5px]">
              <span className="text-faint">Avg tone</span>
              <span className="tabular font-semibold" style={{ color: toneColor }}>
                {avg > 0 ? '+' : ''}
                {avg.toFixed(2)}
              </span>
            </div>
          }
        />
        <div className="h-[210px] px-2 pb-3">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={trend} margin={{ top: 8, right: 12, left: -22, bottom: 0 }}>
              <CartesianGrid stroke="var(--grid-line)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: 'var(--text-faint)' }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
                interval="preserveStartEnd"
                minTickGap={24}
              />
              <YAxis
                yAxisId="tone"
                domain={[-1, 1]}
                ticks={[-1, 0, 1]}
                tick={{ fontSize: 10, fill: 'var(--text-faint)' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis yAxisId="vol" hide domain={[0, maxVolume + 1]} />
              <Tooltip
                content={<TrendTooltip />}
                cursor={{ fill: 'var(--surface-2)' }}
              />
              {/* raw daily coverage — the honest base rate */}
              <Bar
                yAxisId="vol"
                dataKey="volume"
                fill="var(--border-strong)"
                radius={[2, 2, 0, 0]}
                barSize={7}
                opacity={0.65}
              />
              {/* trailing 7-day mean tone — the trend, not a per-day reading */}
              <Line
                yAxisId="tone"
                type="monotone"
                dataKey="score"
                stroke="var(--accent)"
                strokeWidth={2}
                dot={false}
                connectNulls
                activeDot={{ r: 3.5, fill: 'var(--accent)', stroke: 'var(--surface)', strokeWidth: 2 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-5 py-2.5 text-[11px] text-faint">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-sm bg-line-strong" />
            items per day
            <span className="ml-2 inline-block h-2 w-4 rounded-sm bg-accent" />
            7-day mean tone
          </span>
          {peak && peak.volume > 0 && (
            <span>
              Peak coverage {fmtShortDate(`${peak.date}T00:00:00`)} · {peak.volume} items
            </span>
          )}
        </div>
      </Card>

      <Card className="lg:col-span-2">
        <SectionTitle eyebrow="Coverage" title="Where the attention is" count={coverage.length} />
        <div className="h-[210px] px-2 pb-3">
          <ResponsiveContainer width="100%" height="100%">
            <div className="h-full w-full">
              <CoverageBars data={coverage} />
            </div>
          </ResponsiveContainer>
        </div>
        <div className="border-t border-line px-5 py-2.5 text-[11px] text-faint">
          Categories with the most coverage drive the frame their team works inside.
        </div>
      </Card>
    </div>
  )
}

/** Horizontal bars with every category label visible. */
function CoverageBars({ data }: { data: { label: string; count: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.count))
  return (
    <div className="flex h-full flex-col justify-center gap-1.5 overflow-y-auto px-2">
      {data.map((d, i) => (
        <div key={d.label} className="group flex items-center gap-2">
          <span className="w-[104px] shrink-0 truncate text-right text-[10.5px] text-muted">
            {d.label}
          </span>
          <span className="relative h-[13px] flex-1 overflow-hidden rounded-sm bg-surface-3">
            <span
              className="absolute inset-y-0 left-0 rounded-sm transition-all"
              style={{
                width: `${(d.count / max) * 100}%`,
                background: i === 0 ? 'var(--accent)' : 'var(--border-strong)',
              }}
            />
          </span>
          <span className="tabular w-5 shrink-0 text-[10.5px] text-faint">{d.count}</span>
        </div>
      ))}
    </div>
  )
}

function TrendTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  const has = p.score !== null && p.score !== undefined
  const tone = p.score > 0.15 ? 'positive' : p.score < -0.15 ? 'negative' : 'neutral'
  const color =
    tone === 'positive'
      ? 'var(--positive)'
      : tone === 'negative'
        ? 'var(--negative)'
        : 'var(--text-muted)'
  return (
    <div className="rounded-lg border border-line bg-surface px-2.5 py-2 shadow-pop">
      <div className="text-[11px] font-semibold text-ink">{p.label}</div>
      <div className="tabular mt-1 text-[11px]" style={{ color }}>
        {has ? `7-day tone ${p.score > 0 ? '+' : ''}${p.score}` : 'no coverage'}
      </div>
      <div className="tabular text-[11px] text-faint">
        {p.volume} item{p.volume === 1 ? '' : 's'} that day
      </div>
    </div>
  )
}
