import { useEffect, useState } from 'react'
import { getHealth, NETWORK_FAILURE_HINT } from './api/client'

type ApiState = 'checking' | 'connected' | 'unavailable'

export function ApiStatus() {
  const [state, setState] = useState<ApiState>('checking')

  useEffect(() => {
    const controller = new AbortController()
    getHealth(controller.signal)
      .then(() => setState('connected'))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState('unavailable')
      })
    return () => controller.abort()
  }, [])

  return <div className={`api-status api-status--${state}`} role="status"><span aria-hidden="true" /><div><strong>{state === 'checking' ? 'Checking API' : state === 'connected' ? 'API connected' : 'API unavailable'}</strong><small>{state === 'connected' ? 'FastAPI health check passed' : state === 'unavailable' ? NETWORK_FAILURE_HINT : 'Contacting the local backend'}</small></div></div>
}
