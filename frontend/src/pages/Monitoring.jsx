import { Bot, Cpu, Database, Plug, Puzzle, Server } from 'lucide-react'
import { api } from '../services/api'
import { usePolling } from '../hooks/usePolling'
import { Empty, ErrorNote, Spinner, ago, fmtTime, num } from '../components/ui'

function Card({ icon: Icon, title, state, value, children }) {
  const label = { ok: 'Connected', warn: 'Attention', bad: 'Unavailable', idle: 'Unknown' }[state]
  return (
    <div className="panel">
      <div className="panel-body stack" style={{ gap: 10 }}>
        <div className="row"><Icon size={16} color="var(--text-2)" /><span className="strong">{title}</span>
          <span className="status-pill" style={{ marginLeft: 'auto' }}><span className={`dot ${state}`} />{value || label}</span>
        </div>
        <div className="small muted">{children}</div>
      </div>
    </div>
  )
}

export default function Monitoring({ status }) {
  const s = status.data
  const backendOk = !status.error
  const employees = usePolling(() => api.employees(), 5000)
  const pending = (employees.data || []).filter((e) => e.unanalyzed_live_events > 0)
  const a = s?.analysis
  const mon = s?.monitoring

  return (
    <div className="stack">
      <ErrorNote error={status.error} />
      <div className="grid cols-4">
        <Card icon={Server} title="Backend (FastAPI)" state={backendOk ? 'ok' : 'bad'}>
          {backendOk ? `Responding · server time ${fmtTime(s?.backend?.time)}` : status.error?.message}
        </Card>
        <Card icon={Database} title="PostgreSQL" state={!backendOk ? 'idle' : s?.database?.ok ? 'ok' : 'bad'}>
          {s?.database?.info || '—'}
        </Card>
        <Card icon={Bot} title="Ollama" state={!backendOk ? 'idle' : s?.ollama?.ok ? 'ok' : 'bad'}>
          {s?.ollama?.ok ? `Reachable at ${s.ollama.url}` : (s?.ollama?.error || 'Not reachable — run `ollama serve`')}
        </Card>
        <Card icon={Cpu} title={`Model ${s?.ollama?.model || ''}`} state={!backendOk || !s?.ollama?.ok ? 'idle' : s.ollama.model_available ? 'ok' : 'warn'}
          value={s?.ollama?.model_available ? 'Available' : 'Missing'}>
          {s?.ollama?.model_available ? `Installed models: ${s.ollama.installed_models.join(', ')}` : `Run: ollama pull ${s?.ollama?.model || 'qwen2.5:3b'}`}
        </Card>
      </div>

      <div className="grid cols-2-1">
        <div className="panel">
          <div className="panel-head"><Puzzle size={16} /><h2>Chrome extension</h2>
            <span className="sub">pairing (employee verified) is shown separately from transmission (events actually received)</span>
          </div>
          {!mon ? <div className="panel-body"><Spinner /></div> : (
            <>
              <div className="panel-body grid cols-4" style={{ gap: 12 }}>
                <div><div className="small muted">Monitoring status</div><div className="strong">{{ transmitting: 'Receiving live events', paired_idle: 'Paired — no recent events', no_active_pairing: 'No active pairing' }[mon.status]}</div></div>
                <div><div className="small muted">Last live event received</div><div className="strong">{mon.last_live_event_at ? `${ago(mon.last_live_event_at)} (${mon.last_live_event_employee})` : 'none yet'}</div></div>
                <div><div className="small muted">Live events, last 60 min</div><div className="strong">{num(mon.live_events_last_hour)}</div></div>
                <div><div className="small muted">Active pairings</div><div className="strong">{mon.paired_extensions.length}</div></div>
              </div>
              {mon.paired_extensions.length === 0 ? <Empty icon={Plug} title="No extension paired">Open the hackViz extension popup in Chrome and enter an employee ID.</Empty> : (
                <div className="table-wrap">
                  <table>
                    <thead><tr><th>Employee</th><th>Paired</th><th>Connection (heartbeat)</th><th>Transmission</th><th>Events sent</th></tr></thead>
                    <tbody>
                      {mon.paired_extensions.map((p, i) => (
                        <tr key={i}>
                          <td><a href={`#/employees/${p.employee_id}`} className="strong">{p.employee_name}</a><div className="mono small muted">{p.employee_id} · {p.role}</div></td>
                          <td className="small">{fmtTime(p.paired_at)}</td>
                          <td><span className="status-pill"><span className={`dot ${p.connection === 'online' ? 'ok' : 'warn'}`} />{p.connection === 'online' ? 'Online' : 'Stale'} · {ago(p.last_heartbeat_at)}</span></td>
                          <td><span className="status-pill"><span className={`dot ${p.transmitting ? 'ok' : 'idle'}`} />{p.last_event_at ? `Last event ${ago(p.last_event_at)}` : 'No events received yet'}</span></td>
                          <td className="mono">{num(p.events_received)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>

        <div className="panel">
          <div className="panel-head"><Bot size={16} /><h2>Analysis worker</h2></div>
          {!a ? <div className="panel-body"><Spinner /></div> : (
            <div className="panel-body stack" style={{ gap: 10 }}>
              <dl className="kv small" style={{ gridTemplateColumns: '150px 1fr' }}>
                <dt>Worker thread</dt><dd>{a.worker_alive ? 'Running' : 'Stopped'}</dd>
                <dt>Automatic analysis</dt><dd>{a.auto_enabled ? `On — after ${a.batch_size} new live events or ${a.idle_seconds}s idle` : 'Off (manual only)'}</dd>
                <dt>Retry after failure</dt><dd>{a.retry_seconds}s (events are never skipped)</dd>
                <dt>Currently running</dt><dd>{a.current ? `${a.current.employee_id} (${a.current.mode}) since ${ago(a.current.started_at)}` : 'Idle'}</dd>
                <dt>Queued</dt><dd>{a.active.filter((j) => j.state === 'queued').map((j) => j.employee_id).join(', ') || 'none'}</dd>
              </dl>
              <div className="small muted">Employees with unanalyzed live events</div>
              {pending.length === 0 ? <div className="small">None</div> : pending.map((e) => (
                <div key={e.employee_id} className="row small"><a href={`#/employees/${e.employee_id}`}>{e.employee_id}</a><span className="muted">{e.name}</span><span style={{ marginLeft: 'auto' }} className="mono">{e.unanalyzed_live_events}</span></div>
              ))}
              <div className="small muted mt-8">Recent jobs</div>
              {Object.values(a.last_finished || {}).sort((x, y) => new Date(y.finished_at) - new Date(x.finished_at)).slice(0, 6).map((j, i) => (
                <div key={i} className="small row" style={{ alignItems: 'flex-start' }}>
                  <span className={`dot ${j.state === 'done' ? 'ok' : 'bad'}`} style={{ width: 7, height: 7, borderRadius: '50%', marginTop: 6, flexShrink: 0 }} />
                  <span><span className="mono">{j.employee_id}</span> · {j.mode} · {ago(j.finished_at)} — {j.state === 'done' ? (j.result?.status === 'saved' ? `saved #${j.result.anomaly_id} (${j.result.risk_level})` : j.result?.status) : j.error}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
