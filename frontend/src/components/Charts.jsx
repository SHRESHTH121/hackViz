import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EVENT_LABEL } from './ui'

// Series colours validated for the dark surface (see styles.css --series-*).
export const HIST = '#3987e5'
export const LIVE = '#d55181'
const SURFACE = '#111823'
const AXIS = { stroke: '#7d8aa0', fontSize: 11 }

function Tip({ active, payload, label, labelFmt }) {
  if (!active || !payload?.length) return null
  const total = payload.reduce((s, p) => s + (p.value || 0), 0)
  return (
    <div className="chart-tip">
      <div className="strong" style={{ marginBottom: 4 }}>{labelFmt ? labelFmt(label) : label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="row" style={{ gap: 6 }}>
          <i style={{ width: 8, height: 8, borderRadius: 2, background: p.color, display: 'inline-block' }} />
          <span style={{ color: 'var(--text-2)' }}>{p.name}</span>
          <span style={{ marginLeft: 'auto', paddingLeft: 12, color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>{p.value.toLocaleString()}</span>
        </div>
      ))}
      {payload.length > 1 && <div className="muted" style={{ marginTop: 4 }}>Total {total.toLocaleString()}</div>}
    </div>
  )
}

export function SourceLegend() {
  return (
    <div className="legend">
      <span><i style={{ background: HIST }} />Historical CERT data (synthetic)</span>
      <span><i style={{ background: LIVE }} />Live Chrome extension</span>
    </div>
  )
}

const dayFmt = (d) => new Date(d + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

// Daily activity, stacked by source. 2px surface gap between segments; rounded data-end on top.
export function DailyActivityChart({ data, height = 220 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} barCategoryGap="22%">
        <CartesianGrid vertical={false} stroke="#1e2836" />
        <XAxis dataKey="date" tickFormatter={dayFmt} tick={AXIS} axisLine={{ stroke: '#283447' }} tickLine={false} minTickGap={18} />
        <YAxis tick={AXIS} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip content={<Tip labelFmt={dayFmt} />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
        <Bar dataKey="historical" name="Historical" stackId="s" fill={HIST} stroke={SURFACE} strokeWidth={1} isAnimationActive={false} maxBarSize={28} />
        <Bar dataKey="live" name="Live" stackId="s" fill={LIVE} stroke={SURFACE} strokeWidth={1} radius={[4, 4, 0, 0]} isAnimationActive={false} maxBarSize={28} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// Event-type distribution, horizontal stacked bars.
export function EventTypeChart({ data, height = 240 }) {
  const rows = data.map((d) => ({ ...d, label: EVENT_LABEL[d.event_type] || d.event_type, historical: d.historical ?? 0, live: d.live ?? 0 }))
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }} barCategoryGap="28%">
        <CartesianGrid horizontal={false} stroke="#1e2836" />
        <XAxis type="number" tick={AXIS} axisLine={false} tickLine={false} allowDecimals={false} />
        <YAxis type="category" dataKey="label" width={112} tick={{ ...AXIS, fill: '#b3bfcf' }} axisLine={false} tickLine={false} />
        <Tooltip content={<Tip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
        <Bar dataKey="historical" name="Historical" stackId="s" fill={HIST} stroke={SURFACE} strokeWidth={1} isAnimationActive={false} maxBarSize={28} />
        <Bar dataKey="live" name="Live" stackId="s" fill={LIVE} stroke={SURFACE} strokeWidth={1} radius={[0, 4, 4, 0]} isAnimationActive={false} maxBarSize={22} />
      </BarChart>
    </ResponsiveContainer>
  )
}
