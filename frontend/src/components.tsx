import type { ReactNode } from 'react'

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'green' | 'amber' }) {
  return <span className={`badge badge--${tone}`}>{children}</span>
}
export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <header className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="lede">{description}</p></div>{action}</header>
}
export function StatePanel({ kind, title, description, action }: { kind: 'loading' | 'empty' | 'error'; title: string; description: string; action?: ReactNode }) {
  return <div className={`state-panel state-panel--${kind}`} role={kind === 'error' ? 'alert' : 'status'}><span className="state-icon" aria-hidden="true">{kind === 'loading' ? '···' : kind === 'empty' ? '○' : '!'}</span><div><strong>{title}</strong><p>{description}</p>{action}</div></div>
}
export function Metric({ label, value, note }: { label: string; value: string; note?: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</div>
}
export function ArrowIcon() { return <span aria-hidden="true">→</span> }
