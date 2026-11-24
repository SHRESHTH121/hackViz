import { useState } from 'react'
import { Bot, ChevronDown, ChevronUp, ShieldAlert, ShieldCheck } from 'lucide-react'
import { api } from '../services/api'
import { ConfidenceBar, EvidenceChip, ErrorNote, EVENT_LABEL, RiskBadge, SourceBadge, Spinner, fmtShort, fmtTime } from './ui'

// One saved LLM assessment. All text shown here is the model's actual stored output.
export default function AssessmentCard({ a, showEmployee = true, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const [detail, setDetail] = useState(null)
  const [err, setErr] = useState(null)

  const toggle = async () => {
    const next = !open
    setOpen(next)
    if (next && !detail) {
      try { setDetail(await api.anomaly(a.id)) } catch (e) { setErr(e) }
    }
  }
  const level = a.is_anomaly ? a.risk_level : 'low'
  const Icon = a.is_anomaly ? ShieldAlert : ShieldCheck

  return (
    <div className={`panel assessment ${level}`}>
      <div className="panel-body stack" style={{ gap: 12 }}>
        <div className="row wrap" style={{ gap: 10 }}>
          <Icon size={18} color={a.is_anomaly ? (a.risk_level === 'high' ? 'var(--red)' : 'var(--amber)') : 'var(--green)'} />
          <span className="strong">{a.is_anomaly ? 'Potential anomaly' : 'No anomaly identified'}</span>
          <RiskBadge level={a.risk_level} />
          <span className="mono muted small">Alert #{a.id}</span>
          {showEmployee && (
            <span className="small">
              <a href={`#/employees/${a.employee_id}`}>{a.employee_name}</a>
              <span className="muted"> · {a.employee_id} · {a.role} · {a.department}</span>
            </span>
          )}
          <span className="muted small" style={{ marginLeft: 'auto' }} title={fmtTime(a.created_at)}>{fmtShort(a.created_at)}</span>
        </div>

        <div className="reason">{a.reason}</div>

        <div className="grid cols-2" style={{ gap: 12 }}>
          <div className="callout">
            <div className="small muted" style={{ marginBottom: 4 }}>Recommended action</div>
            <div style={{ color: 'var(--text)' }}>{a.recommended_action}</div>
          </div>
          <dl className="kv small" style={{ gridTemplateColumns: '120px 1fr', alignContent: 'start' }}>
            <dt>Confidence</dt><dd><ConfidenceBar value={a.confidence} /></dd>
            <dt>Model</dt><dd className="row"><Bot size={13} /> <span className="mono">{a.model_name}</span></dd>
            <dt>Analysis</dt><dd>{a.analysis_source === 'auto_batch' ? 'Automatic batch' : 'Manual (Analyze Now)'} · {a.analyzed_event_ids.length} events ({a.live_events_in_batch} new live) · {a.duration_ms ? `${(a.duration_ms / 1000).toFixed(1)}s` : '—'}</dd>
          </dl>
        </div>

        <div className="row wrap">
          <span className="small muted">Supporting event IDs:</span>
          {a.evidence_event_ids.length ? a.evidence_event_ids.map((id) => <EvidenceChip key={id} id={id} />) : <span className="small muted">none cited</span>}
        </div>

        {a.validation_notes?.length > 0 && (
          <div className="callout warn small">Validation: {a.validation_notes.join('; ')}</div>
        )}

        <div>
          <button className="btn sm ghost" onClick={toggle}>
            {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />} Activity sequence, indicators & raw model output
          </button>
        </div>

        {open && (
          <div className="stack" style={{ gap: 12 }}>
            <ErrorNote error={err} />
            {!detail && !err && <Spinner label="Loading…" />}
            {detail && (
              <>
                <div>
                  <div className="small muted" style={{ marginBottom: 6 }}>Rule-based supporting indicators (hints supplied to the model, not verdicts)</div>
                  {detail.indicators.length === 0 ? <div className="small muted">None triggered</div> :
                    detail.indicators.map((i, k) => (
                      <div className="indicator" key={k}>
                        <span className={`strength ${i.strength}`}>{i.strength}</span>
                        <span style={{ flex: 1 }}><span className="mono">{i.code}</span> — {i.detail}</span>
                        <span className="row wrap" style={{ gap: 4 }}>{i.event_ids.slice(0, 8).map((id) => <EvidenceChip key={id} id={id} />)}</span>
                      </div>
                    ))}
                </div>
                <div className="panel" style={{ boxShadow: 'none' }}>
                  <div className="table-wrap" style={{ maxHeight: 340, overflowY: 'auto' }}>
                    <table>
                      <thead><tr><th>ID</th><th>Time</th><th>Source</th><th>Type</th><th>Domain / detail</th></tr></thead>
                      <tbody>
                        {detail.analyzed_events.map((e) => (
                          <tr key={e.id} style={a.evidence_event_ids.includes(e.id) ? { background: 'rgba(240,82,79,0.06)' } : undefined}>
                            <td><EvidenceChip id={e.id} /></td>
                            <td className="nowrap small">{fmtShort(e.timestamp)}</td>
                            <td><SourceBadge source={e.source} short /></td>
                            <td className="small">{EVENT_LABEL[e.event_type] || e.event_type}</td>
                            <td className="url-cell" title={e.url || e.filename}>{e.domain || ''} {e.filename ? `· ${e.filename}` : (e.url ? e.url.replace(/^https?:\/\/[^/]+/, '') : '')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div>
                  <div className="small muted" style={{ marginBottom: 6 }}>Raw model response (stored verbatim) · batch {detail.batch_id}</div>
                  <pre className="json">{detail.raw_response}</pre>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
