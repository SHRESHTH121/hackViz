import { useEffect, useState } from 'react'
import { FileSearch, X } from 'lucide-react'
import { api } from '../services/api'
import { ErrorNote, EVENT_LABEL, SourceBadge, Spinner, fmtTime } from './ui'

// Shows the original PostgreSQL activity record behind an evidence ID.
export default function EventModal({ id, onClose }) {
  const [ev, setEv] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    setEv(null); setErr(null)
    api.event(id).then(setEv).catch(setErr)
  }, [id])

  useEffect(() => {
    const k = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [onClose])

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <FileSearch size={18} color="var(--accent)" />
          <h3>Activity record <span className="mono">#{id}</span></h3>
          <button className="btn ghost icon-btn" style={{ marginLeft: 'auto' }} onClick={onClose}><X size={16} /></button>
        </div>
        <div className="modal-body">
          <ErrorNote error={err} />
          {!ev && !err && <Spinner label="Loading record from PostgreSQL…" />}
          {ev && (
            <div className="stack">
              <dl className="kv">
                <dt>Event ID</dt><dd className="mono">{ev.id}{ev.dataset_record_id && <span className="muted"> · dataset record {ev.dataset_record_id}</span>}</dd>
                <dt>Employee</dt><dd><a href={`#/employees/${ev.employee_id}`} onClick={onClose}>{ev.employee_name}</a> <span className="mono muted">({ev.employee_id})</span></dd>
                <dt>Role</dt><dd>{ev.role} · {ev.department}</dd>
                <dt>Timestamp</dt><dd>{fmtTime(ev.timestamp)} <span className="muted mono small">({ev.timestamp})</span></dd>
                <dt>Event type</dt><dd>{EVENT_LABEL[ev.event_type] || ev.event_type}</dd>
                <dt>Source</dt><dd><SourceBadge source={ev.source} /></dd>
                <dt>Domain</dt><dd className="mono">{ev.domain || '—'}</dd>
                <dt>URL</dt><dd className="mono" style={{ wordBreak: 'break-all' }}>{ev.url || '—'}</dd>
                <dt>Filename</dt><dd className="mono" style={{ wordBreak: 'break-all' }}>{ev.filename || '—'}</dd>
                {ev.received_at && ev.source === 'chrome_extension' && (<><dt>Received</dt><dd>{fmtTime(ev.received_at)}</dd></>)}
              </dl>
              <div>
                <div className="small muted" style={{ marginBottom: 6 }}>Safe metadata (no page content, form data or credentials are ever collected)</div>
                <pre className="json">{JSON.stringify(ev.safe_metadata || {}, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
