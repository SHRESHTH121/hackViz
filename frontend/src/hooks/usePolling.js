import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Poll an async loader every `interval` ms. Returns { data, error, loading, reload }.
 * Pauses while the tab is hidden; never overlaps requests.
 */
export function usePolling(loader, interval = 4000, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const busy = useRef(false)
  const alive = useRef(true)
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  const reload = useCallback(async () => {
    if (busy.current) return
    busy.current = true
    try {
      const d = await loaderRef.current()
      if (alive.current) { setData(d); setError(null) }
    } catch (e) {
      if (alive.current && e.name !== 'AbortError') setError(e)
    } finally {
      busy.current = false
      if (alive.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    alive.current = true
    setLoading(true)
    reload()
    if (!interval) return () => { alive.current = false }
    const t = setInterval(() => { if (!document.hidden) reload() }, interval)
    return () => { alive.current = false; clearInterval(t) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, error, loading, reload, setData }
}
