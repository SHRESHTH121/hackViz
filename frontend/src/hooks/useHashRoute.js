import { useEffect, useState } from 'react'

// Minimal hash router: #/ , #/employees/EMP002 , #/activity , #/alerts , #/alerts/12 , #/monitoring
function parse() {
  const h = window.location.hash.replace(/^#/, '') || '/'
  const parts = h.split('?')[0].split('/').filter(Boolean)
  return { path: h, page: parts[0] || 'dashboard', param: parts[1] ? decodeURIComponent(parts[1]) : null }
}

export function useHashRoute() {
  const [route, setRoute] = useState(parse)
  useEffect(() => {
    const on = () => { setRoute(parse()); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return route
}

export const navigate = (to) => { window.location.hash = to }
