import { useEffect, useRef } from 'react'
import { EvidenceChip, EVENT_LABEL, SourceBadge, eventDetail, fmtTime } from './ui'

export default function ActivityTable({ items, showEmployee = true, flashNew = true }) {
  const seen = useRef(null)
  const fresh = new Set()
  if (flashNew && seen.current) items.forEach((e) => { if (!seen.current.has(e.id)) fresh.add(e.id) })
  useEffect(() => { seen.current = new Set(items.map((e) => e.id)) }, [items])

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Event ID</th>
            {showEmployee && <th>Employee</th>}
            <th>Timestamp</th>
            <th>Event type</th>
            <th>Domain</th>
            <th>URL / details</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {items.map((e) => (
            <tr key={e.id} className={fresh.has(e.id) ? 'flash' : ''}>
              <td><EvidenceChip id={e.id} /></td>
              {showEmployee && (
                <td className="nowrap">
                  <a href={`#/employees/${e.employee_id}`} className="strong">{e.employee_name}</a>
                  <div className="mono muted" style={{ fontSize: 11 }}>{e.employee_id}</div>
                </td>
              )}
              <td className="nowrap small">{fmtTime(e.timestamp)}</td>
              <td className="nowrap"><span className="tag">{EVENT_LABEL[e.event_type] || e.event_type}</span></td>
              <td className="mono small">{e.domain || '—'}</td>
              <td className="url-cell" title={e.url || eventDetail(e)}>{eventDetail(e) || '—'}</td>
              <td><SourceBadge source={e.source} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
