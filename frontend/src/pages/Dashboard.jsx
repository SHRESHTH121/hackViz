import { useMemo, useState } from 'react'
import { Activity, AlertTriangle, Database, Download, Eye, Globe, Play, Search, ShieldAlert, UserPlus, Users } from 'lucide-react'
import { api } from '../services/api'
import { usePolling } from '../hooks/usePolling'
import { navigate } from '../hooks/useHashRoute'
import { DailyActivityChart, EventTypeChart, SourceLegend } from '../components/Charts'
import { Empty, ErrorNote, RiskBadge, Spinner, ago, fmtShort, initials, num, useApp } from '../components/ui'

function Stat({ icon: Icon, label, value, foot, tone = 'var(--accent)', soft = 'var(--accent-soft)' }) {
  return (
    <div className="panel stat">
      <div className="stat-top">{label}<span className="stat-icon" style={{ background: soft, color: tone }}><Icon size={16} /></span></div>
      <div className="stat-value">{value ?? '—'}</div>
      <div className="stat-foot">{foot}</div>
    </div>
  )
}

const RISK_ORDER = { high: 0, medium: 1, low: 2, unassessed: 3 }

export default function Dashboard() {
  const { version, toast, openAddEmployee } = useApp()
  const stats = usePolling(() => api.stats(), 5000, [version])
  const emps = usePolling(() => api.employees(), 4000, [version])
  const [f, setF] = useState({ q: '', role: '', dept: '', risk: '', source: '' })
  const [sort, setSort] = useState('id')
  const [queued, setQueued] = useState({})

  const list = emps.data || []
  const roles = useMemo(() => [...new Set(list.map((e) => e.role))].sort(), [list])
  const depts = useMemo(() => [...new Set(list.map((e) => e.department))].sort(), [list])
  const rows = useMemo(() => {
    const q = f.q.trim().toLowerCase()
    let r = list.filter((e) =>
      (!q || `${e.employee_id} ${e.name} ${e.email || ''}`.toLowerCase().includes(q)) &&
      (!f.role || e.role === f.role) && (!f.dept || e.department === f.dept) &&
      (!f.risk || e.risk_status === f.risk) &&
      (!f.source || (f.source === 'live' ? e.live_activity > 0 : f.source === 'historical' ? e.historical_activity > 0 && e.live_activity === 0 : e.total_activity === 0)))
    if (sort === 'risk') r = [...r].sort((a, b) => RISK_ORDER[a.risk_status] - RISK_ORDER[b.risk_status])
    if (sort === 'activity') r = [...r].sort((a, b) => b.total_activity - a.total_activity)
    if (sort === 'last') r = [...r].sort((a, b) => new Date(b.last_activity || 0) - new Date(a.last_activity || 0))
    return r
  }, [list, f, sort])

  const analyze = async (e, ev) => {
    ev.stopPropagation()
    try {
      const r = await api.analyze(e.employee_id)
      setQueued((q) => ({ ...q, [e.employee_id]: true }))
      setTimeout(() => setQueued((q) => ({ ...q, [e.employee_id]: false })), 8000)
      toast(r.already_in_progress ? `Analysis for ${e.employee_id} is already in progress` : `Analysis queued for ${e.employee_id} — running on local Ollama`)
    } catch (err) { toast(err.message, 'error') }
  }

  const s = stats.data
  const set = (k) => (ev) => setF({ ...f, [k]: ev.target.value })

  return (
    <div className="stack">
      <ErrorNote error={stats.error} />
      <div className="grid cols-6">
        <Stat icon={Users} label="Total Employees" value={s && num(s.total_employees)} foot="Directory in PostgreSQL" />
        <Stat icon={Activity} label="Active Employees" value={s && num(s.active_employees)} foot="Live activity in last 24h" tone="var(--green)" soft="var(--green-soft)" />
        <Stat icon={Database} label="Historical Activity" value={s && num(s.historical_activity)} foot="Synthetic CERT-style records" tone="var(--hist-text)" soft="var(--hist-soft)" />
        <Stat icon={Globe} label="Live Activity" value={s && num(s.live_activity)} foot="From Chrome extension" tone="var(--live-text)" soft="var(--live-soft)" />
        <Stat icon={ShieldAlert} label="Anomalies Detected" value={s && num(s.anomalies_detected)} foot={s ? `${num(s.assessments)} LLM assessments total` : ''} tone="var(--amber)" soft="var(--amber-soft)" />
        <Stat icon={AlertTriangle} label="High-Risk Alerts" value={s && num(s.high_risk_alerts)} foot="Require human review" tone="var(--red)" soft="var(--red-soft)" />
      </div>

      <div className="grid cols-3-2">
        <div className="panel">
          <div className="panel-head"><h2>Activity per day</h2><span className="sub">all employees, organisation local time</span><div className="right"><SourceLegend /></div></div>
          <div className="panel-body">{s ? (s.daily.length ? <DailyActivityChart data={s.daily} /> : <Empty title="No activity yet" />) : <Spinner />}</div>
        </div>
        <div className="panel">
          <div className="panel-head"><h2>Activity by event type</h2></div>
          <div className="panel-body">{s ? <EventTypeChart data={s.event_types} /> : <Spinner />}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h2>Employee directory</h2>
          <span className="sub">click a row to open the profile</span>
          <div className="right">
            <a className="btn sm" href={api.exportUrl()}><Download size={14} />Export all activity CSV</a>
            <button className="btn sm primary" onClick={openAddEmployee}><UserPlus size={14} />Add employee</button>
          </div>
        </div>
        <div className="filters">
          <div className="search"><Search size={15} /><input className="input" placeholder="Search employee, ID or email" value={f.q} onChange={set('q')} /></div>
          <select className="select" value={f.role} onChange={set('role')}><option value="">All roles</option>{roles.map((r) => <option key={r}>{r}</option>)}</select>
          <select className="select" value={f.dept} onChange={set('dept')}><option value="">All departments</option>{depts.map((r) => <option key={r}>{r}</option>)}</select>
          <select className="select" value={f.risk} onChange={set('risk')}>
            <option value="">All risk levels</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option><option value="unassessed">Not assessed</option>
          </select>
          <select className="select" value={f.source} onChange={set('source')}>
            <option value="">All activity sources</option><option value="live">Has live extension activity</option><option value="historical">Historical data only</option><option value="none">No activity</option>
          </select>
          <select className="select" value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="id">Sort: Employee ID</option><option value="risk">Sort: Risk</option><option value="activity">Sort: Activity count</option><option value="last">Sort: Last activity</option>
          </select>
          <span className="count">{rows.length} of {list.length} employees</span>
        </div>
        {emps.loading && !emps.data ? <div className="panel-body"><Spinner label="Loading employees…" /></div> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Employee ID</th><th>Employee</th><th>Job role</th><th>Department</th><th>Total activity</th><th>Last activity</th><th>Risk status</th><th style={{ textAlign: 'right' }}>Actions</th></tr></thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.employee_id} className="clickable" onClick={() => navigate(`#/employees/${e.employee_id}`)}>
                    <td className="mono strong">{e.employee_id}</td>
                    <td>
                      <div className="row" style={{ gap: 10 }}>
                        <span className="avatar" style={{ width: 30, height: 30, fontSize: 11.5, borderRadius: 8 }}>{initials(e.name)}</span>
                        <div><div className="strong">{e.name}</div><div className="small muted">{e.email || 'no email'}</div></div>
                      </div>
                    </td>
                    <td>{e.role}</td>
                    <td>{e.department}</td>
                    <td>
                      <span className="strong" style={{ fontVariantNumeric: 'tabular-nums' }}>{num(e.total_activity)}</span>
                      <div className="small muted">{num(e.historical_activity)} hist · <span style={{ color: e.live_activity ? 'var(--live-text)' : undefined }}>{num(e.live_activity)} live</span></div>
                    </td>
                    <td className="small nowrap">{fmtShort(e.last_activity)}<div className="muted">{ago(e.last_activity)}</div></td>
                    <td>
                      <RiskBadge level={e.risk_status} />
                      {e.unanalyzed_live_events > 0 && <div className="small muted mt-8">{e.unanalyzed_live_events} new live event(s) pending</div>}
                    </td>
                    <td style={{ textAlign: 'right' }} onClick={(ev) => ev.stopPropagation()}>
                      <div className="row" style={{ justifyContent: 'flex-end', gap: 6 }}>
                        <button className="btn sm" title="Open profile" onClick={() => navigate(`#/employees/${e.employee_id}`)}><Eye size={13} />View</button>
                        <button className="btn sm" title="Run Ollama analysis now" disabled={!e.total_activity || queued[e.employee_id]} onClick={(ev) => analyze(e, ev)}><Play size={13} />{queued[e.employee_id] ? 'Queued' : 'Analyze'}</button>
                        <a className="btn sm icon-btn" title="Export this employee's activity (CSV)" href={api.exportUrl(e.employee_id)}><Download size={13} /></a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length === 0 && <Empty title="No employees match these filters" />}
          </div>
        )}
      </div>
    </div>
  )
}
