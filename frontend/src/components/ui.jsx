import { createContext, useContext } from 'react'
import { Database, Globe, Inbox, Loader2 } from 'lucide-react'

export const AppContext = createContext({ openEvent: () => {}, toast: () => {}, refreshAll: () => {} })
export const useApp = () => useContext(AppContext)

export function RiskBadge({ level }) {
  const l = (level || 'unassessed').toLowerCase()
  const label = { low: 'Low', medium: 'Medium', high: 'High', unassessed: 'Not assessed' }[l] || l
  return <span className={`badge risk-${l}`}><span className="dot" />{label}</span>
}

export function SourceBadge({ source, short }) {
  if (source === 'chrome_extension')
    return <span className="badge src-live" title="Collected live by the hackViz Chrome extension"><Globe size={11} />{short ? 'Live' : 'Live Chrome Extension'}</span>
  return <span className="badge src-hist" title="Fictional, synthetic CERT-style historical record"><Database size={11} />{short ? 'Historical' : 'Historical CERT Data'}</span>
}

export function EvidenceChip({ id }) {
  const { openEvent } = useApp()
  return <button className="ev-chip" onClick={(e) => { e.stopPropagation(); openEvent(id) }} title="Open original activity record">#{id}</button>
}

export function Spinner({ size = 16, label }) {
  return <span className="row muted"><Loader2 size={size} className="spin" />{label}</span>
}

export function Empty({ icon: Icon = Inbox, title, children }) {
  return (
    <div className="empty">
      <Icon size={32} />
      <div className="t">{title}</div>
      <div className="small">{children}</div>
    </div>
  )
}

export function StatusDot({ state }) {
  return <span className={`dot ${state}`} style={{ width: 8, height: 8, borderRadius: '50%', display: 'inline-block' }} />
}

export function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100)
  return (
    <span className="row" title="Subjective model estimate - not a calibrated probability">
      <span className="conf-bar"><div style={{ width: `${pct}%` }} /></span>
      <span className="mono">{(value ?? 0).toFixed(2)}</span>
    </span>
  )
}

export function ErrorNote({ error }) {
  if (!error) return null
  return <div className="callout error">{error.message || String(error)}</div>
}

// ------------------------------------------------------------------ formatting
export const fmtTime = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
export const fmtShort = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
export const ago = (iso) => {
  if (!iso) return 'never'
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${Math.floor(s)}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}
export const num = (n) => (n ?? 0).toLocaleString()
export const initials = (name) => (name || '?').split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()

export const EVENT_LABEL = {
  navigation: 'Navigation', download: 'Download', tab_activated: 'Tab activated', logon: 'Logon', logoff: 'Logoff',
  file_access: 'File access', app_usage: 'App usage', removable_media: 'Removable media', email: 'Email (metadata)',
}

export function eventDetail(e) {
  const m = e.safe_metadata || {}
  if (e.event_type === 'app_usage') return `${m.application || 'app'} · ${m.duration_min ?? '?'} min`
  if (e.event_type === 'email') return `to @${e.domain} · ${m.recipients ?? '?'} recipient(s) · ${m.attachments ?? 0} attachment(s)`
  if (e.event_type === 'removable_media') return `${m.activity || ''} · ${m.device || 'device'}`
  if (e.event_type === 'logon' || e.event_type === 'logoff') return m.pc || ''
  if (e.event_type === 'file_access') return `${m.activity || 'open'} · ${e.filename || ''}`
  if (e.event_type === 'download') return e.filename || e.url
  return e.url
}
