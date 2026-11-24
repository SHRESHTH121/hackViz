import { useState } from 'react'
import { BellRing, Info } from 'lucide-react'
import { api } from '../services/api'
import { usePolling } from '../hooks/usePolling'
import AssessmentCard from '../components/AssessmentCard'
import { Empty, ErrorNote, Spinner, useApp } from '../components/ui'

export default function Alerts() {
  const { version } = useApp()
  const [f, setF] = useState({ only: 'true', risk_level: '', employee_id: '' })
  const emps = usePolling(() => api.employees(), 15000, [version])
  const list = usePolling(() => api.anomalies({ only_anomalies: f.only === 'true' ? true : undefined, risk_level: f.risk_level, employee_id: f.employee_id, limit: 200 }),
    4000, [f.only, f.risk_level, f.employee_id, version])
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const rows = list.data || []

  return (
    <div className="stack">
      <div className="callout info row small"><Info size={15} />
        Every alert below is a stored response from the local Ollama model (qwen2.5:3b), validated against the activity records it was given. Confidence is the model's subjective estimate, not a calibrated probability. Alerts are investigative leads that need human review — not proof of misconduct.
      </div>
      <div className="panel">
        <div className="panel-head"><BellRing size={16} color="var(--amber)" /><h2>Anomaly alerts</h2><span className="sub">auto-refreshing every 4 s</span></div>
        <div className="filters">
          <select className="select" value={f.only} onChange={set('only')}>
            <option value="true">Anomalies only</option><option value="false">All assessments (incl. no anomaly)</option>
          </select>
          <select className="select" value={f.risk_level} onChange={set('risk_level')}>
            <option value="">All risk levels</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
          </select>
          <select className="select" value={f.employee_id} onChange={set('employee_id')}>
            <option value="">All employees</option>
            {(emps.data || []).map((e) => <option key={e.employee_id} value={e.employee_id}>{e.employee_id} — {e.name}</option>)}
          </select>
          <span className="count">{rows.length} shown</span>
        </div>
        <div className="panel-body stack">
          <ErrorNote error={list.error} />
          {!list.data ? <Spinner label="Loading…" /> : rows.length === 0 ? (
            <Empty icon={BellRing} title={f.only === 'true' ? 'No anomalies detected' : 'No assessments yet'}>
              Alerts appear here only after the local LLM has actually analyzed an employee's activity. Use <b>Analyze Now</b> on an employee profile or collect live activity with the extension.
            </Empty>
          ) : rows.map((a) => <AssessmentCard key={a.id} a={a} />)}
        </div>
      </div>
    </div>
  )
}
