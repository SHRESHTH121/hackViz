import { useState } from 'react'
import { Download, Pause, Play, Radio } from 'lucide-react'
import { api } from '../services/api'
import { usePolling } from '../hooks/usePolling'
import ActivityTable from '../components/ActivityTable'
import { Empty, ErrorNote, EVENT_LABEL, Spinner, fmtTime, num, useApp } from '../components/ui'

export default function LiveFeed() {
  const { version } = useApp()
  const [f, setF] = useState({ source: 'chrome_extension', employee_id: '', event_type: '' })
  const [paused, setPaused] = useState(false)
  const [limit, setLimit] = useState(50)
  const emps = usePolling(() => api.employees(), 15000, [version])
  const feed = usePolling(() => api.activity({ ...f, limit }), paused ? 0 : 3000, [f.source, f.employee_id, f.event_type, limit, paused, version])
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  return (
    <div className="stack">
      <div className="panel">
        <div className="panel-head">
          <Radio size={16} color="var(--live-text)" className={paused ? '' : 'pulse'} />
          <h2>Activity feed</h2>
          <span className="sub">{paused ? 'paused' : 'refreshing every 3 s'}{feed.data ? ` · last update ${fmtTime(new Date().toISOString())}` : ''}</span>
          <div className="right">
            <button className="btn sm" onClick={() => setPaused(!paused)}>{paused ? <Play size={13} /> : <Pause size={13} />}{paused ? 'Resume' : 'Pause'}</button>
            <a className="btn sm" href={api.exportUrl(f.employee_id || undefined)}><Download size={13} />Export CSV</a>
          </div>
        </div>
        <div className="filters">
          <select className="select" value={f.source} onChange={set('source')}>
            <option value="chrome_extension">Live Chrome Extension only</option>
            <option value="historical_cert">Historical CERT Data only</option>
            <option value="">All sources</option>
          </select>
          <select className="select" value={f.employee_id} onChange={set('employee_id')}>
            <option value="">All employees</option>
            {(emps.data || []).map((e) => <option key={e.employee_id} value={e.employee_id}>{e.employee_id} — {e.name}</option>)}
          </select>
          <select className="select" value={f.event_type} onChange={set('event_type')}>
            <option value="">All event types</option>{Object.entries(EVENT_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <span className="count">{feed.data ? `${num(feed.data.total)} matching records` : ''}</span>
        </div>
        <ErrorNote error={feed.error} />
        {!feed.data ? <div className="panel-body"><Spinner label="Loading…" /></div> :
          feed.data.items.length === 0 ? (
            <Empty icon={Radio} title="No live events yet">
              Pair the hackViz Chrome extension with an employee ID and browse normally — navigation and download events appear here within seconds.
            </Empty>
          ) : <ActivityTable items={feed.data.items} />}
        {feed.data && feed.data.total > feed.data.items.length && (
          <div className="panel-body" style={{ textAlign: 'center' }}><button className="btn sm" onClick={() => setLimit(limit + 50)}>Load more</button></div>
        )}
      </div>
    </div>
  )
}
