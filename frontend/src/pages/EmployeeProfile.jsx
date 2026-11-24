import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Bot, Download, History, Loader2, Play, RefreshCw, Search, ShieldQuestion } from 'lucide-react'
import { api } from '../services/api'
import { usePolling } from '../hooks/usePolling'
import ActivityTable from '../components/ActivityTable'
import AssessmentCard from '../components/AssessmentCard'
import { DailyActivityChart, EventTypeChart, SourceLegend } from '../components/Charts'
import { Empty, ErrorNote, EVENT_LABEL, RiskBadge, Spinner, ago, fmtShort, initials, num, useApp } from '../components/ui'

const PAGE = 50

export default function EmployeeProfile({ id }) {
  const { toast, version } = useApp()
  const emp = usePolling(() => api.employee(id), 3000, [id, version])
  const timeline = usePolling(() => api.employeeTimeline(id), 10000, [id, version])
  const history = usePolling(() => api.employeeAnomalies(id), 4000, [id, version])
  const [filters, setFilters] = useState({ source: '', event_type: '', q: '' })
  const [limit, setLimit] = useState(PAGE)
  const activity = usePolling(() => api.employeeActivity(id, { ...filters, limit }), 4000, [id, filters.source, filters.event_type, filters.q, limit, version])
  const [requesting, setRequesting] = useState(false)
  const lastJobRef = useRef(null)

  const e = emp.data
  const job = e?.analysis_job
  const running = job && (job.state === 'queued' || job.state === 'running')

  // Notify when a job for this employee finishes.
  useEffect(() => {
    if (!job) return
    const key = `${job.queued_at}-${job.state}`
    if (lastJobRef.current && lastJobRef.current !== key && (job.state === 'done' || job.state === 'failed')) {
      if (job.state === 'done') {
        const r = job.result || {}
        toast(r.status === 'duplicate' ? 'No new activity since the last analysis — showing the existing assessment.' : `Ollama assessment saved: risk ${r.risk_level?.toUpperCase()}`, 'success')
      } else toast(`Analysis failed: ${job.error}`, 'error')
      history.reload()
    }
    lastJobRef.current = key
  }, [job, toast, history])

  const analyze = async (force = false) => {
    setRequesting(true)
    try {
      const r = await api.analyze(id, force)
      toast(r.already_in_progress ? 'Analysis already in progress for this employee' : 'Analysis queued — local Ollama inference on CPU can take 30-120 s')
      emp.reload()
    } catch (err) { toast(err.message, 'error') } finally { setRequesting(false) }
  }

  if (emp.error && !e) return (
    <div className="stack">
      <a href="#/" className="btn sm" style={{ width: 'fit-content' }}><ArrowLeft size={14} />Back</a>
      <ErrorNote error={emp.error} />
    </div>
  )
  if (!e) return <Spinner label="Loading employee…" />

  const latest = e.latest_assessment
  const setF = (k) => (ev) => { setFilters({ ...filters, [k]: ev.target.value }); setLimit(PAGE) }
  const st = e.analysis_state

  return (
    <div className="stack">
      <div className="row"><a href="#/" className="btn sm ghost"><ArrowLeft size={14} />Employee directory</a></div>

      <div className="panel">
        <div className="profile-head" style={{ flexWrap: 'wrap' }}>
          <div className="avatar">{initials(e.name)}</div>
          <div style={{ minWidth: 220 }}>
            <div className="row" style={{ gap: 10 }}><span className="profile-name">{e.name}</span><RiskBadge level={e.risk_status} /></div>
            <div className="muted"><span className="mono">{e.employee_id}</span> · {e.role} · {e.department}</div>
            <div className="small muted mt-8">
              {e.email || 'no email'}{e.profile?.location ? ` · ${e.profile.location}` : ''}{e.profile?.hire_date ? ` · joined ${e.profile.hire_date}` : ''}
              {e.is_synthetic ? ' · fictional profile' : ` · added ${fmtShort(e.created_at)}`}
            </div>
          </div>
          <div className="row" style={{ marginLeft: 'auto', gap: 0 }}>
            <div className="metric"><div className="v">{num(e.total_activity)}</div><div className="l">Total activity</div></div>
            <div className="metric"><div className="v" style={{ color: 'var(--hist-text)' }}>{num(e.historical_activity)}</div><div className="l">Historical</div></div>
            <div className="metric"><div className="v" style={{ color: 'var(--live-text)' }}>{num(e.live_activity)}</div><div className="l">Live</div></div>
            <div className="metric"><div className="v small" style={{ fontSize: 14, paddingTop: 4 }}>{ago(e.last_activity)}</div><div className="l">Last activity</div></div>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn primary" onClick={() => analyze(false)} disabled={running || requesting || !e.total_activity}>
              {running ? <Loader2 size={15} className="spin" /> : <Play size={15} />}{running ? (job.state === 'queued' ? 'Queued…' : 'Analyzing…') : 'Analyze Now'}
            </button>
            <a className="btn" href={api.exportUrl(e.employee_id)}><Download size={15} />Export activity</a>
          </div>
        </div>
        {(running || e.unanalyzed_live_events > 0 || st?.last_error) && (
          <div style={{ padding: '0 18px 16px' }} className="stack">
            {running && (
              <div className="callout info row"><Bot size={16} className="pulse" />
                <span>Ollama ({e.latest_assessment?.model_name || 'qwen2.5:3b'}) is assessing this employee's activity
                  {job.started_at ? ` — started ${ago(job.started_at)}` : ' — waiting in queue'}. CPU inference typically takes 30–120 seconds.</span>
              </div>
            )}
            {!running && e.unanalyzed_live_events > 0 && (
              <div className="callout small">{e.unanalyzed_live_events} new live event(s) not yet analyzed. Automatic analysis runs after a batch threshold or a short idle period — or click <b>Analyze Now</b>.</div>
            )}
            {st?.last_error && !running && (
              <div className="callout error small">Last analysis attempt failed ({st.consecutive_failures} attempt(s)): {st.last_error}. Events were not skipped and will be retried{st.next_retry_at ? ` after ${fmtShort(st.next_retry_at)}` : ''}.</div>
            )}
          </div>
        )}
      </div>

      <div className="grid cols-3-2">
        <div className="stack">
          <div className="panel">
            <div className="panel-head"><ShieldQuestion size={16} color="var(--accent)" /><h2>Current risk assessment</h2>
              {latest && <div className="right"><button className="btn sm ghost" onClick={() => analyze(true)} disabled={running} title="Re-run the analysis on the same window"><RefreshCw size={13} />Re-run</button></div>}
            </div>
            <div className="panel-body">
              {latest ? <AssessmentCard a={latest} showEmployee={false} /> : (
                <Empty icon={ShieldQuestion} title="Not assessed yet">
                  No LLM assessment exists for this employee. Collect live activity with the Chrome extension or click <b>Analyze Now</b> to assess the most recent activity.
                </Empty>
              )}
            </div>
          </div>
        </div>
        <div className="stack">
          <div className="panel">
            <div className="panel-head"><h2>Activity timeline</h2><div className="right"><SourceLegend /></div></div>
            <div className="panel-body">{timeline.data ? (timeline.data.daily.length ? <DailyActivityChart data={timeline.data.daily} height={190} /> : <Empty title="No activity yet" />) : <Spinner />}</div>
          </div>
          <div className="panel">
            <div className="panel-head"><h2>Event types</h2></div>
            <div className="panel-body">{timeline.data ? (timeline.data.event_types.length ? <EventTypeChart data={timeline.data.event_types} height={Math.max(120, timeline.data.event_types.length * 30)} /> : <Empty title="No activity yet" />) : <Spinner />}</div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-head"><h2>Activity log</h2><span className="sub">recent browser events and historical records</span></div>
        <div className="filters">
          <div className="search"><Search size={15} /><input className="input" placeholder="Filter domain, URL, file" value={filters.q} onChange={setF('q')} /></div>
          <select className="select" value={filters.source} onChange={setF('source')}>
            <option value="">All sources</option><option value="chrome_extension">Live Chrome Extension</option><option value="historical_cert">Historical CERT Data</option>
          </select>
          <select className="select" value={filters.event_type} onChange={setF('event_type')}>
            <option value="">All event types</option>{Object.entries(EVENT_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <span className="count">{activity.data ? `${Math.min(activity.data.items.length, activity.data.total)} of ${num(activity.data.total)} records` : ''}</span>
        </div>
        {activity.data ? (activity.data.items.length ? <ActivityTable items={activity.data.items} showEmployee={false} /> : <Empty title="No activity matches these filters" />) : <div className="panel-body"><Spinner /></div>}
        {activity.data && activity.data.total > activity.data.items.length && (
          <div className="panel-body" style={{ textAlign: 'center' }}><button className="btn sm" onClick={() => setLimit(limit + PAGE)}>Load more</button></div>
        )}
      </div>

      <div className="panel">
        <div className="panel-head"><History size={16} /><h2>Previous assessments</h2><span className="sub">{history.data ? `${history.data.length} saved in total` : ''}</span></div>
        <div className="panel-body stack">
          {history.data?.length > 1 ? history.data.slice(1).map((a) => <AssessmentCard key={a.id} a={a} showEmployee={false} />) : <Empty title="No earlier assessments" />}
        </div>
      </div>
    </div>
  )
}
