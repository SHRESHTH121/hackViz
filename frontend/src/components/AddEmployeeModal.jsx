import { useState } from 'react'
import { UserPlus, X } from 'lucide-react'
import { api } from '../services/api'

const EMPTY = { employee_id: '', name: '', role: '', department: '', email: '' }
const ID_RE = /^[A-Z0-9][A-Z0-9_-]{1,31}$/

export default function AddEmployeeModal({ onClose, onCreated, existingIds = [] }) {
  const [f, setF] = useState(EMPTY)
  const [errs, setErrs] = useState({})
  const [serverErr, setServerErr] = useState(null)
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: k === 'employee_id' ? e.target.value.toUpperCase() : e.target.value })

  const validate = () => {
    const e = {}
    const id = f.employee_id.trim()
    if (!id) e.employee_id = 'Employee ID is required'
    else if (!ID_RE.test(id)) e.employee_id = 'Use 2-32 letters, digits, - or _ (e.g. EMP011)'
    else if (existingIds.includes(id)) e.employee_id = `${id} already exists`
    if (f.name.trim().length < 2) e.name = 'Full name is required'
    if (f.role.trim().length < 2) e.role = 'Job role is required'
    if (f.department.trim().length < 2) e.department = 'Department is required'
    if (f.email.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(f.email.trim())) e.email = 'Invalid email address'
    setErrs(e)
    return Object.keys(e).length === 0
  }

  const submit = async (ev) => {
    ev.preventDefault()
    setServerErr(null)
    if (!validate()) return
    setSaving(true)
    try {
      const body = { ...f, employee_id: f.employee_id.trim(), email: f.email.trim() || null }
      const created = await api.createEmployee(body)
      onCreated(created)
    } catch (e) {
      setServerErr(e.message)
    } finally {
      setSaving(false)
    }
  }

  const field = (k, label, ph, hint) => (
    <div className="field">
      <label htmlFor={k}>{label}</label>
      <input id={k} className="input" value={f[k]} onChange={set(k)} placeholder={ph} autoComplete="off" />
      {errs[k] ? <span className="err">{errs[k]}</span> : hint && <span className="hint">{hint}</span>}
    </div>
  )

  return (
    <div className="overlay" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={submit} noValidate>
        <div className="modal-head">
          <UserPlus size={18} color="var(--accent)" />
          <h3>Add employee</h3>
          <button type="button" className="btn ghost icon-btn" style={{ marginLeft: 'auto' }} onClick={onClose}><X size={16} /></button>
        </div>
        <div className="modal-body">
          {field('employee_id', 'Employee ID *', 'EMP011', 'Used to pair the Chrome extension')}
          {field('name', 'Full name *', 'e.g. Sara Iyer')}
          <div className="grid cols-2" style={{ gap: 12 }}>
            {field('role', 'Job role *', 'e.g. Finance Analyst')}
            {field('department', 'Department *', 'e.g. Finance')}
          </div>
          {field('email', 'Email (optional)', 'name@company.example')}
          {serverErr && <div className="callout error">{serverErr}</div>}
          <div className="callout info small mt-8">New employees have no historical baseline. Their activity is assessed against their role until history builds up.</div>
        </div>
        <div className="modal-foot">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn primary" disabled={saving}>{saving ? 'Saving…' : 'Create employee'}</button>
        </div>
      </form>
    </div>
  )
}
