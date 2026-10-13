import { useEffect, useState, type ReactNode } from 'react'

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'green' | 'amber' }) {
  return <span className={`badge badge--${tone}`}>{children}</span>
}
export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <header className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="lede">{description}</p></div>{action}</header>
}
export function StatePanel({ kind, title, description, action }: { kind: 'loading' | 'empty' | 'error'; title: string; description: string; action?: ReactNode }) {
  return <div className={`state-panel state-panel--${kind}`} role={kind === 'error' ? 'alert' : 'status'}><span className="state-icon" aria-hidden="true">{kind === 'loading' ? '···' : kind === 'empty' ? '○' : '!'}</span><div><strong>{title}</strong><p>{description}</p>{action}</div></div>
}
export function LongTaskProgress({ task }: { task: 'analysis' | 'generation' }) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  useEffect(() => {
    const startedAt = Date.now()
    const timer = window.setInterval(() => setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1_000)), 1_000)
    return () => window.clearInterval(timer)
  }, [])

  const content = task === 'analysis'
    ? elapsedSeconds < 5
      ? ['Analysis request sent', 'Preparing the validated responses. Analysis often takes 15–45 seconds on a warm model.']
      : elapsedSeconds < 20
        ? ['Analysis in progress', 'The request is still running. Embedding and grouping times vary with the model and dataset.']
        : ['Still analyzing', 'A cold model can take longer to start. Keep this page open while the request completes.']
    : elapsedSeconds < 8
      ? ['Generation request sent', 'Gemini is preparing a grounded draft from the student evidence and teacher passages shown above.']
      : elapsedSeconds < 30
        ? ['Generation in progress', 'The provider is still responding. ClassLens will keep this request within its browser time limit.']
        : ['Still waiting for Gemini', 'The request will stop near the 70-second browser limit. Your evidence remains available for retry.']

  return <div className="state-panel long-task-progress" role="status" aria-live="polite" aria-atomic="true"><span className="long-task-progress__pulse" aria-hidden="true" /><div><strong>{content[0]}</strong><p>{content[1]}</p><span className="long-task-progress__elapsed">{elapsedSeconds}s elapsed</span></div></div>
}
export function Metric({ label, value, note }: { label: string; value: string; note?: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</div>
}
export function ArrowIcon() { return <span aria-hidden="true">→</span> }
