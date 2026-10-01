import { useEffect, useState, type ChangeEvent } from 'react'
import './App.css'
import { ArrowIcon, Badge, Metric, PageHeader, StatePanel } from './components'
import { demoScenario, demoSteps } from './mockData'
import type { RouteKey } from './types'

const routeFromPath = (): RouteKey => demoSteps.find((step) => step.path === window.location.pathname)?.key ?? 'dashboard'

function App() {
  const [route, setRoute] = useState<RouteKey>(routeFromPath)
  useEffect(() => { const onPopState = () => setRoute(routeFromPath()); window.addEventListener('popstate', onPopState); return () => window.removeEventListener('popstate', onPopState) }, [])
  const navigate = (next: RouteKey) => { const step = demoSteps.find((item) => item.key === next); if (!step) return; window.history.pushState({}, '', step.path); setRoute(next); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  return <div className="app-shell"><aside className="sidebar">
    <button className="brand" onClick={() => navigate('dashboard')} aria-label="ClassLens dashboard"><span className="brand-mark">CL</span><span>ClassLens<small>Teacher workspace</small></span></button>
    <div className="demo-label"><Badge tone="amber">Demo skeleton</Badge><p>Photosynthesis scenario</p></div>
    <nav aria-label="Golden path"><p className="nav-heading">Demo sequence</p>{demoSteps.map((step, index) => <button key={step.key} className={route === step.key ? 'nav-item active' : 'nav-item'} onClick={() => navigate(step.key)} aria-current={route === step.key ? 'page' : undefined}><span>{String(index + 1).padStart(2, '0')}</span>{step.label}</button>)}</nav>
    <p className="sidebar-note">Interface-only milestone<br />No backend or AI connected</p>
  </aside><main className="main-content">
    {route === 'dashboard' && <Dashboard onNext={() => navigate('upload')} />}{route === 'upload' && <Upload onNext={() => navigate('analysis')} />}{route === 'analysis' && <Analysis onNext={() => navigate('misconception')} />}{route === 'misconception' && <Misconception onNext={() => navigate('intervention')} />}{route === 'intervention' && <Intervention onNext={() => navigate('results')} />}{route === 'results' && <Results onNext={() => navigate('dashboard')} />}
  </main></div>
}

function Dashboard({ onNext }: { onNext: () => void }) {
  return <><PageHeader eyebrow="Teacher dashboard" title="See the thinking behind the score." description="Move from a free-response assessment to evidence-backed learning gaps and a teacher-reviewed next step." action={<Badge tone="green">UI ready</Badge>} />
    <section className="hero-card"><div><Badge tone="amber">Synthetic scenario · not loaded</Badge><p className="kicker">{demoScenario.grade} · {demoScenario.subject}</p><h2>{demoScenario.topic}</h2><p>Follow the planned hackathon story from assessment intake through follow-up results.</p><button className="button primary" onClick={onNext}>Load photosynthesis demo <ArrowIcon /></button></div><div className="lens-graphic" aria-hidden="true"><span>Responses</span><strong>?</strong><span>Teacher review</span></div></section>
    <section className="section-block"><div className="section-title"><div><p className="eyebrow">At a glance</p><h2>Demo readiness</h2></div></div><div className="metric-grid"><Metric label="Assessment data" value="Not loaded" note="Awaiting a validated fixture" /><Metric label="Potential gaps" value="Not analyzed" note="No model output exists" /><Metric label="Interventions" value="0 approved" note="Teacher action required" /></div></section>
    <StatePanel kind="empty" title="No recent assessments" description="Load the documented photosynthesis scenario to begin the clickable demo path." action={<button className="text-button" onClick={onNext}>Go to assessment intake →</button>} /></>
}

function Upload({ onNext }: { onNext: () => void }) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const loadDemo = () => { setStatus('loading'); window.setTimeout(() => setStatus('ready'), 450) }
  const fileChanged = (event: ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0]; if (file && !file.name.toLowerCase().endsWith('.csv')) setStatus('error'); else if (file) setStatus('ready') }
  return <><PageHeader eyebrow="Step 2 of 6" title="Upload assessment" description="Add an assessment and response CSV, or stage the documented synthetic scenario for this interface walkthrough." />
    <div className="two-column"><section className="card"><p className="eyebrow">Option A</p><h2>Load demo scenario</h2><p>{demoScenario.assessmentTitle}</p><dl className="facts"><div><dt>Class</dt><dd>{demoScenario.grade} Science</dd></div><div><dt>Topic</dt><dd>{demoScenario.topic}</dd></div><div><dt>Data</dt><dd>Synthetic fixture pending</dd></div></dl><button className="button primary" onClick={loadDemo} disabled={status === 'loading'}>{status === 'loading' ? 'Preparing preview…' : 'Prepare demo preview'}</button></section>
    <section className="card"><p className="eyebrow">Option B</p><h2>Choose response file</h2><p>CSV validation will be connected in the backend milestone.</p><label className="file-input">Choose CSV<input type="file" accept=".csv,text/csv" onChange={fileChanged} /></label><small>Interface check only. Files are not read or uploaded.</small></section></div>
    {status === 'loading' && <StatePanel kind="loading" title="Preparing the preview" description="Checking the interface state for assessment and response data." />}{status === 'error' && <StatePanel kind="error" title="Use a CSV file" description="The selected file type is not supported. Choose a file ending in .csv." action={<button className="text-button" onClick={() => setStatus('idle')}>Try again</button>} />}{status === 'idle' && <StatePanel kind="empty" title="No assessment selected" description="Choose a CSV or prepare the synthetic demo preview. No data leaves this browser." />}
    {status === 'ready' && <section className="card preview-card"><div className="section-title"><div><p className="eyebrow">Preview</p><h2>Ready for the UI walkthrough</h2></div><Badge tone="amber">Unvalidated mock</Badge></div><p className="notice">Counts stay unavailable until a real, versioned dataset and validation contract exist.</p><div className="metric-grid compact"><Metric label="Students" value="—" note="Not available" /><Metric label="Questions" value="—" note="Not available" /><Metric label="Blank responses" value="—" note="Not available" /></div><div className="actions"><button className="button primary" onClick={onNext}>View staged analysis <ArrowIcon /></button></div></section>}</>
}

function Analysis({ onNext }: { onNext: () => void }) {
  return <><PageHeader eyebrow="Step 3 of 6" title="Learning gaps" description="Review potential misconception groups as proposals, then inspect the response evidence before deciding what they mean." action={<Badge tone="amber">Documented demo example</Badge>} />
    <section className="question-strip"><div><span>Question focus</span><strong>{demoScenario.question}</strong></div><div><span>Analysis status</span><strong>UI example only</strong></div></section><div className="section-title"><div><p className="eyebrow">Potential misconceptions</p><h2>One documented pattern to inspect</h2></div></div>
    <button className="gap-card" onClick={onNext}><div><Badge tone="amber">Potential · teacher review needed</Badge><h2>{demoScenario.proposedMisconception}</h2><p>Three example phrases are documented in the demo plan. Group support and confidence remain unavailable until analysis is implemented.</p></div><div className="gap-meta"><span>Evidence examples</span><strong>3 documented</strong><span>Open evidence →</span></div></button><StatePanel kind="empty" title="No other groups available" description="The UI does not invent additional groups or outliers before a verified analysis exists." /></>
}

function Misconception({ onNext }: { onNext: () => void }) {
  return <><PageHeader eyebrow="Step 4 of 6" title={demoScenario.proposedMisconception} description="Inspect the exact documented response examples before treating this potential pattern as educationally meaningful." action={<Badge tone="amber">Not a diagnosis</Badge>} />
    <section className="card"><p className="eyebrow">Question context</p><h2>{demoScenario.question}</h2><div className="concept-box"><span>Expected concept</span><p>{demoScenario.expectedConcept}</p></div></section><section className="section-block"><div className="section-title"><div><p className="eyebrow">Evidence</p><h2>Representative responses</h2></div><Badge>From docs/DEMO.md</Badge></div><div className="evidence-list">{demoScenario.evidence.map((item) => <blockquote key={item.id}><p>“{item.text}”</p><cite>{item.id} · documented example, not a dataset record</cite></blockquote>)}</div></section><div className="callout"><div><strong>Teacher checkpoint</strong><p>Does this proposed interpretation match what the responses show? The teacher remains the final authority.</p></div><button className="button primary" onClick={onNext}>Continue to intervention <ArrowIcon /></button></div></>
}

function Intervention({ onNext }: { onNext: () => void }) {
  const [reviewed, setReviewed] = useState(false)
  return <><PageHeader eyebrow="Step 5 of 6" title="Review intervention" description="Ground a draft in teacher-provided material, edit it, and approve it explicitly before use." /><section className="card material-card"><div><p className="eyebrow">Grounding material</p><h2>No teacher material connected</h2><p>A real passage and source locator will appear here only after retrieval is implemented.</p></div><Badge tone="amber">Grounding unavailable</Badge></section><StatePanel kind="error" title="Generation is intentionally unavailable" description="ClassLens will not claim a grounded intervention without a retrieved teacher passage. This skeleton shows the safe blocked state." />
    <section className="card form-card"><label htmlFor="intervention">Intervention draft</label><textarea id="intervention" rows={5} disabled placeholder="A grounded draft will appear here after teacher material retrieval succeeds." /><label htmlFor="questions">Follow-up questions</label><textarea id="questions" rows={4} disabled placeholder="Follow-up questions will appear here with source references." /><label className="check-row"><input type="checkbox" checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} />I reviewed the blocked state for this UI walkthrough.</label><div className="actions"><button className="button secondary" disabled>Reject draft</button><button className="button primary" disabled={!reviewed} onClick={onNext}>Continue to results skeleton <ArrowIcon /></button></div></section></>
}

function Results({ onNext }: { onNext: () => void }) {
  return <><PageHeader eyebrow="Step 6 of 6" title="Results" description="Compare baseline and follow-up transparently. Missing data remains unavailable rather than being treated as zero." action={<Badge tone="amber">No results loaded</Badge>} /><section className="results-card"><div><p className="eyebrow">Target concept</p><h2>{demoScenario.proposedMisconception}</h2><p>Observed comparison only. This view will not imply that an intervention caused a change.</p></div><div className="comparison"><div><span>Baseline</span><strong>Not available</strong><small>No verified fixture</small></div><span className="comparison-arrow">→</span><div><span>Follow-up</span><strong>Not available</strong><small>No results loaded</small></div></div></section><div className="metric-grid"><Metric label="Matched responses" value="—" note="Stable identifiers required" /><Metric label="Missing follow-up" value="—" note="Never counted as zero" /><Metric label="Observed change" value="—" note="Not calculated" /></div><StatePanel kind="empty" title="Follow-up results are not available" description="Load a clearly labeled synthetic follow-up fixture once the results contract is implemented." /><div className="callout complete"><div><strong>Clickable skeleton complete</strong><p>You reached every screen in the planned hackathon path without implying backend or AI work exists.</p></div><button className="button primary" onClick={onNext}>Return to dashboard</button></div></>
}

export default App
