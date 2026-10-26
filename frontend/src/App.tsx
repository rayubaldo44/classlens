import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import './App.css'
import './WorkspacePolish.css'
import { LandingPage } from './LandingPage'
import { ApiStatus } from './ApiStatus'
import { clearPendingRequestId, getOrCreatePendingRequestId } from './api/requestReliability'
import {
  analysisMatchesWorkflow,
  groupReviewMatchesWorkflow,
  comparisonMatchesWorkflow,
  parseWorkflowPointer,
  remediationMatchesWorkflow,
  retrievalMatchesWorkflow,
  type WorkflowPointer,
} from './workflowStorage'
import {
  analyzeAssessment,
  analyzePhotosynthesisDemo,
  ApiError,
  getAnalysis,
  getGroupReviews,
  getFollowUpComparison,
  getRemediation,
  getPhotosynthesisDemo,
  generateRemediation,
  ingestLearningMaterial,
  ingestPhotosynthesisDemoMaterial,
  NETWORK_FAILURE_HINT,
  retrieveMaterialForGroup,
  reviewRemediation,
  submitFollowUpComparison,
  submitPhotosynthesisDemoComparison,
  uploadAssessment,
  type AnalysisResponse,
  type AssessmentPreview,
  type LearningMaterial,
  type MaterialIngestionResponse,
  type MaterialRetrievalContext,
  type MaterialRetrievalResponse,
  type ReviewedMisconceptionGroup,
  type GroupReviewResponse,
  type EditableRemediationContent,
  type FollowUpComparisonLink,
  type FollowUpComparisonRecord,
  type RemediationRecord,
} from './api/client'
import { ArrowIcon, Badge, LongTaskProgress, Metric, PageHeader, StatePanel } from './components'
import { GroupReviewPanel } from './GroupReviewPanel'
import { buildApprovedInterventionExport } from './interventionExport'
import { demoScenario, demoSteps } from './mockData'
import type { RouteKey } from './types'

const routeFromPath = (): RouteKey => demoSteps.find((step) => step.path === window.location.pathname)?.key ?? 'landing'
type AnalysisSource = { kind: 'demo' } | { kind: 'upload'; file: File }
const WORKFLOW_KEY = 'classlens.workflow.v1'
const readWorkflow = () => {
  try { return parseWorkflowPointer(localStorage.getItem(WORKFLOW_KEY)) }
  catch { return parseWorkflowPointer('{unavailable') }
}
const replaceWorkflow = (next: WorkflowPointer) => {
  try { localStorage.setItem(WORKFLOW_KEY, JSON.stringify(next)) } catch { /* Workflow remains usable without reload recovery. */ }
}
const restoreErrorMessage = (fallback: string, error: unknown) => error instanceof ApiError
  ? `${fallback} ${error.message}`
  : `${fallback} ${NETWORK_FAILURE_HINT}`

function App() {
  const [route, setRoute] = useState<RouteKey>(routeFromPath)
  const didRestore = useRef(false)
  const mainRef = useRef<HTMLElement>(null)
  const previousRoute = useRef(route)
  const [analysisSource, setAnalysisSource] = useState<AnalysisSource | null>(null)
  const [selectedGroup, setSelectedGroup] = useState<ReviewedMisconceptionGroup | null>(null)
  const [selectedAssessment, setSelectedAssessment] = useState<AssessmentPreview['assessment'] | null>(null)
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisResponse | null>(null)
  const [retrievedSources, setRetrievedSources] = useState<MaterialRetrievalResponse | null>(null)
  const [approvedRemediation, setApprovedRemediation] = useState<RemediationRecord | null>(null)
  const [savedComparison, setSavedComparison] = useState<FollowUpComparisonRecord | null>(null)
  const [restoreMessage, setRestoreMessage] = useState('')
  useEffect(() => {
    if (route === 'landing' || didRestore.current) return
    didRestore.current = true
    void (async () => {
      const saved = readWorkflow()
      if (!saved.pointer) {
        setRestoreMessage(saved.issue?.message ?? 'The saved workflow reference was not valid. Start a new workflow to replace it.')
        return
      }
      const pointer = saved.pointer
      const analysisId = pointer.analysis_id
      if (!analysisId) return
      try {
        const analysis = await getAnalysis(analysisId)
        const reviews = await getGroupReviews(analysisId)
        const group = reviews.active_groups.find((item) => item.reviewed_group_id === pointer.group_id) ?? null
        if (!analysisMatchesWorkflow(pointer, analysis) || !groupReviewMatchesWorkflow(pointer, reviews)) {
          if (analysis.analysis_id === pointer.analysis_id) {
            setSelectedAnalysis(analysis); setSelectedAssessment(analysis.assessment)
            replaceWorkflow({ analysis_id: analysis.analysis_id })
          }
          setRestoreMessage('The saved misconception no longer belongs to this analysis. Return to Learning Gaps and select the evidence again.')
          return
        }
        setSelectedAnalysis(analysis); setSelectedAssessment(analysis.assessment); setSelectedGroup(group)
        if (group && pointer.material_id) {
          try {
            const retrieval = await retrieveMaterialForGroup(pointer.material_id, {
              analysis_id: analysis.analysis_id, group_id: group.reviewed_group_id, question_id: group.question_id, question: group.question,
              correct_answer: group.correct_answer,
              representative_answers: group.representative_responses.map((item) => item.answer),
            })
            if (!retrievalMatchesWorkflow(pointer, retrieval)) {
              replaceWorkflow({ analysis_id: analysis.analysis_id, group_id: group.reviewed_group_id })
              setRestoreMessage('The saved teaching material no longer belongs to this misconception. Retrieve supporting passages again.')
              return
            }
            setRetrievedSources(retrieval)
          } catch (error: unknown) {
            replaceWorkflow({ analysis_id: analysis.analysis_id, group_id: group.reviewed_group_id })
            setRestoreMessage(restoreErrorMessage('The saved teaching-material retrieval could not be restored.', error))
            return
          }
        }
        if (pointer.remediation_id) {
          try {
            const remediation = await getRemediation(pointer.remediation_id)
            if (!remediationMatchesWorkflow(pointer, remediation)) {
              replaceWorkflow({ analysis_id: analysis.analysis_id, group_id: group?.reviewed_group_id, material_id: pointer.material_id })
              setRestoreMessage('The saved intervention no longer belongs to this analysis and misconception. Generate or select the intervention again.')
              return
            }
            setApprovedRemediation(remediation)
          } catch (error: unknown) {
            replaceWorkflow({ analysis_id: analysis.analysis_id, group_id: group?.reviewed_group_id, material_id: pointer.material_id })
            setRestoreMessage(restoreErrorMessage('The saved intervention could not be restored.', error))
            return
          }
        }
        if (pointer.comparison_id) {
          try {
            const comparison = await getFollowUpComparison(pointer.comparison_id)
            if (!comparisonMatchesWorkflow(pointer, comparison)) {
              replaceWorkflow({ analysis_id: analysis.analysis_id, group_id: group?.reviewed_group_id, material_id: pointer.material_id, remediation_id: pointer.remediation_id })
              setRestoreMessage('The saved comparison no longer belongs to this approved intervention. Rerun the follow-up comparison.')
              return
            }
            setSavedComparison(comparison)
          } catch (error: unknown) {
            replaceWorkflow({ analysis_id: analysis.analysis_id, group_id: group?.reviewed_group_id, material_id: pointer.material_id, remediation_id: pointer.remediation_id })
            setRestoreMessage(restoreErrorMessage('The saved comparison could not be restored.', error))
          }
        }
      } catch (error: unknown) {
        setRestoreMessage(restoreErrorMessage('The saved workflow could not be restored.', error))
      }
    })()
  }, [route])
  useEffect(() => { const onPopState = () => setRoute(routeFromPath()); window.addEventListener('popstate', onPopState); return () => window.removeEventListener('popstate', onPopState) }, [])
  useEffect(() => {
    if (previousRoute.current === route) return
    previousRoute.current = route
    window.requestAnimationFrame(() => mainRef.current?.focus({ preventScroll: true }))
  }, [route])
  const navigate = (next: RouteKey) => { const path = next === 'landing' ? '/' : demoSteps.find((item) => item.key === next)?.path; if (!path) return; window.history.pushState({}, '', path); setRoute(next); window.scrollTo({ top: 0, behavior: 'auto' }) }
  if (route === 'landing') return <LandingPage onWorkspace={() => navigate('dashboard')} onDemo={() => navigate('upload')} />
  return <><a className="skip-link" href="#main-content">Skip to main content</a><div className="app-shell"><aside className="sidebar">
    <button className="brand" onClick={() => navigate('landing')} aria-label="ClassLens home"><img className="brand-image" src="/classlens-mascot.png" alt="" width="56" height="56" /><span>ClassLens<small>Teacher workspace</small></span></button>
    <div className="demo-label"><Badge tone="amber">Synthetic demo</Badge><p>Photosynthesis scenario</p></div>
    <nav aria-label="Golden path"><p className="nav-heading">Demo sequence</p>{demoSteps.map((step, index) => <button key={step.key} className={route === step.key ? 'nav-item active' : 'nav-item'} onClick={() => navigate(step.key)} aria-current={route === step.key ? 'page' : undefined}><span>{String(index + 1).padStart(2, '0')}</span>{step.label}</button>)}</nav>
    <label className="mobile-step-picker"><span>Workflow step</span><select value={route} onChange={(event) => { const next = demoSteps.find((step) => step.key === event.target.value); if (next) navigate(next.key) }}>{demoSteps.map((step, index) => <option key={step.key} value={step.key}>{String(index + 1).padStart(2, '0')} · {step.label}</option>)}</select></label>
    <ApiStatus />
  </aside><main className="main-content" id="main-content" ref={mainRef} tabIndex={-1}>
    {restoreMessage && <StatePanel kind="error" title="Saved workflow not fully restored" description={restoreMessage} action={<button className="text-button" onClick={() => { localStorage.removeItem(WORKFLOW_KEY); setRestoreMessage(''); navigate('upload') }}>Start a new workflow →</button>} />}
    {route === 'dashboard' && <Dashboard onNext={() => navigate('upload')} />}{route === 'upload' && <Upload onNext={(source) => { localStorage.removeItem(WORKFLOW_KEY); setAnalysisSource(source); setSelectedGroup(null); setSelectedAssessment(null); setSelectedAnalysis(null); setRetrievedSources(null); setApprovedRemediation(null); setSavedComparison(null); navigate('analysis') }} />}{route === 'analysis' && <Analysis key={analysisSource?.kind === 'upload' ? `${analysisSource.file.name}-${analysisSource.file.size}-${analysisSource.file.lastModified}` : analysisSource?.kind ?? selectedAnalysis?.analysis_id ?? 'none'} source={analysisSource} initialAnalysis={selectedAnalysis} onLoadDemo={() => setAnalysisSource({ kind: 'demo' })} onNext={(group, analysis) => { replaceWorkflow({ analysis_id: analysis.analysis_id, group_id: group.reviewed_group_id }); setSelectedGroup(group); setSelectedAssessment(analysis.assessment); setSelectedAnalysis(analysis); setRetrievedSources(null); setApprovedRemediation(null); setSavedComparison(null); navigate('misconception') }} />}{route === 'misconception' && <Misconception key={`${selectedGroup?.reviewed_group_id ?? 'none'}-${retrievedSources?.material.material_id ?? 'none'}`} group={selectedGroup} analysisId={selectedAnalysis?.analysis_id ?? null} initialRetrieval={retrievedSources} onBack={() => navigate('analysis')} onRetrieved={(sources) => { replaceWorkflow({ analysis_id: selectedAnalysis?.analysis_id, group_id: selectedGroup?.reviewed_group_id, material_id: sources?.material.material_id }); setRetrievedSources(sources) }} onNext={() => navigate('intervention')} />}{route === 'intervention' && <Intervention key={`${selectedGroup?.reviewed_group_id ?? 'none'}-${retrievedSources?.material.material_id ?? 'none'}-${approvedRemediation?.remediation_id ?? 'none'}`} group={selectedGroup} analysisId={selectedAnalysis?.analysis_id ?? null} dataLabel={selectedAnalysis?.data_label ?? null} assessment={selectedAssessment} sources={retrievedSources} initialRemediation={approvedRemediation} onBack={() => navigate('misconception')} onNext={(record) => { replaceWorkflow({ analysis_id: selectedAnalysis?.analysis_id, group_id: selectedGroup?.reviewed_group_id, material_id: retrievedSources?.material.material_id, remediation_id: record.remediation_id }); setApprovedRemediation(record); navigate('results') }} />}{route === 'results' && <Results key={savedComparison?.comparison_id ?? 'new'} baseline={selectedAnalysis} group={selectedGroup} remediation={approvedRemediation} initialResult={savedComparison} onResult={(record) => { replaceWorkflow({ analysis_id: selectedAnalysis?.analysis_id, group_id: selectedGroup?.reviewed_group_id, material_id: retrievedSources?.material.material_id, remediation_id: approvedRemediation?.remediation_id, comparison_id: record.comparison_id }); setSavedComparison(record) }} onNext={() => navigate('dashboard')} />}
  </main></div></>
}

function Dashboard({ onNext }: { onNext: () => void }) {
  return <><PageHeader eyebrow="Teacher dashboard" title="See the thinking behind the score." description="Move from a free-response assessment to evidence-backed learning gaps and a teacher-reviewed next step." action={<Badge tone="green">Workflow connected</Badge>} />
    <section className="hero-card"><div><Badge tone="amber">Synthetic scenario · not loaded</Badge><p className="kicker">{demoScenario.grade} · {demoScenario.subject}</p><h2>{demoScenario.topic}</h2><p>Follow the live workflow from assessment intake through follow-up results.</p><button className="button primary" onClick={onNext}>Load photosynthesis demo <ArrowIcon /></button></div><div className="lens-graphic" aria-hidden="true"><span>Responses</span><strong>?</strong><span>Teacher review</span></div></section>
    <section className="section-block"><div className="section-title"><div><p className="eyebrow">At a glance</p><h2>Demo readiness</h2></div></div><div className="metric-grid"><Metric label="Assessment data" value="Not loaded" note="Awaiting a validated fixture" /><Metric label="Potential gaps" value="Not analyzed" note="No model output exists" /><Metric label="Interventions" value="0 approved" note="Teacher action required" /></div></section>
    <StatePanel kind="empty" title="No recent assessments" description="Load the documented photosynthesis scenario to begin the clickable demo path." action={<button className="text-button" onClick={onNext}>Go to assessment intake →</button>} /></>
}

function Upload({ onNext }: { onNext: (source: AnalysisSource) => void }) {
  const [status, setStatus] = useState<'idle' | 'selected' | 'loading' | 'ready' | 'error'>('idle')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<AssessmentPreview | null>(null)
  const [validatedSource, setValidatedSource] = useState<AnalysisSource | null>(null)
  const [errorMessage, setErrorMessage] = useState('')
  const runPreview = async (source: AnalysisSource, request: () => Promise<AssessmentPreview>) => {
    setStatus('loading'); setErrorMessage('')
    try { setPreview(await request()); setValidatedSource(source); setStatus('ready') }
    catch (error: unknown) { setPreview(null); setValidatedSource(null); setErrorMessage(error instanceof ApiError ? error.message : `The assessment service did not respond. ${NETWORK_FAILURE_HINT}`); setStatus('error') }
  }
  const loadDemo = () => void runPreview({ kind: 'demo' }, getPhotosynthesisDemo)
  const fileChanged = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    setPreview(null); setValidatedSource(null); setSelectedFile(file)
    if (!file) { setStatus('idle'); return }
    if (!file.name.toLowerCase().endsWith('.csv')) { setErrorMessage('Choose a file with a .csv extension.'); setStatus('error'); return }
    setStatus('selected')
  }
  const uploadSelected = () => { if (selectedFile) void runPreview({ kind: 'upload', file: selectedFile }, () => uploadAssessment(selectedFile)) }
  return <><PageHeader eyebrow="Step 2 of 6" title="Upload assessment" description="Add an assessment response CSV, or load the verified synthetic photosynthesis scenario." />
    <div className="two-column"><section className="card"><p className="eyebrow">Option A</p><h2>Load demo scenario</h2><p>{demoScenario.assessmentTitle}</p><dl className="facts"><div><dt>Class</dt><dd>{demoScenario.grade} Science</dd></div><div><dt>Topic</dt><dd>{demoScenario.topic}</dd></div><div><dt>Data</dt><dd>45 synthetic students</dd></div></dl><button className="button primary" onClick={loadDemo} disabled={status === 'loading'}>{status === 'loading' ? 'Validating…' : 'Validate demo dataset'}</button></section>
    <section className="card"><p className="eyebrow">Option B</p><h2>Choose response file</h2><p>Upload a UTF-8 CSV that follows the documented assessment contract.</p><label className="file-input">{selectedFile?.name ?? 'Choose CSV'}<input type="file" accept=".csv,text/csv" onChange={fileChanged} /></label><small>The backend validates the file before showing a preview.</small><button className="button secondary upload-button" onClick={uploadSelected} disabled={!selectedFile || status === 'loading'}>Validate selected CSV</button></section></div>
    {status === 'loading' && <StatePanel kind="loading" title="Validating assessment" description="The backend is parsing and normalizing the response file." />}
    {status === 'error' && <StatePanel kind="error" title="Assessment could not be validated" description={errorMessage} action={<button className="text-button" onClick={() => { setStatus(selectedFile ? 'selected' : 'idle'); setErrorMessage('') }}>Try again</button>} />}
    {status === 'idle' && <StatePanel kind="empty" title="No assessment selected" description="Choose a CSV or load the clearly labeled synthetic photosynthesis dataset." />}
    {status === 'selected' && <StatePanel kind="empty" title="File ready to validate" description={`${selectedFile?.name ?? 'CSV'} has not been uploaded yet.`} action={<button className="text-button" onClick={uploadSelected}>Validate now →</button>} />}
    {status === 'ready' && preview && <section className="card preview-card"><div className="section-title"><div><p className="eyebrow">Validated preview</p><h2>{preview.assessment.title}</h2></div><Badge tone={preview.data_label === 'synthetic_demo' ? 'amber' : 'green'}>{preview.data_label === 'synthetic_demo' ? 'Synthetic demo data' : 'Teacher upload'}</Badge></div><p className="notice">{preview.assessment.grade_level} · {preview.assessment.subject} · {preview.assessment.topic}. Blank and correct answers are retained for review but excluded from misconception grouping.</p><div className="metric-grid compact"><Metric label="Students" value={String(preview.summary.student_count)} note={`${preview.summary.response_count} accepted responses`} /><Metric label="Incorrect answers" value={String(preview.summary.incorrect_count)} note={`${preview.summary.correct_count} marked correct`} /><Metric label="Blank responses" value={String(preview.summary.blank_count)} note="Preserved explicitly" /></div><div className="response-preview"><div className="response-preview__heading"><strong>Normalized sample</strong><span>First {preview.sample_responses.length} accepted rows</span></div>{preview.sample_responses.map((response) => <div className="response-row" key={`${response.student_id}-${response.question_id}`}><span>{response.student_id}</span><p>{response.answer_status === 'blank' ? <em>Blank response</em> : response.answer}</p><Badge tone={response.is_correct ? 'green' : response.answer_status === 'blank' ? 'amber' : 'neutral'}>{response.answer_status === 'blank' ? 'blank' : response.is_correct ? 'correct' : 'incorrect'}</Badge></div>)}</div><div className="actions"><button className="button primary" disabled={!validatedSource} onClick={() => validatedSource && onNext(validatedSource)}>Analyze learning gaps <ArrowIcon /></button></div></section>}</>
}

function Analysis({ source, initialAnalysis, onLoadDemo, onNext }: { source: AnalysisSource | null; initialAnalysis: AnalysisResponse | null; onLoadDemo: () => void; onNext: (group: ReviewedMisconceptionGroup, analysis: AnalysisResponse) => void }) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>(initialAnalysis ? 'ready' : source ? 'loading' : 'idle')
  const [result, setResult] = useState<AnalysisResponse | null>(initialAnalysis)
  const [errorMessage, setErrorMessage] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [reviewAttempt, setReviewAttempt] = useState(0)
  const [reviews, setReviews] = useState<GroupReviewResponse | null>(null)

  useEffect(() => {
    if (!source || initialAnalysis) return
    const controller = new AbortController()
    const request = source.kind === 'demo'
      ? analyzePhotosynthesisDemo(controller.signal)
      : analyzeAssessment(source.file, controller.signal)
    void request.then((analysis) => { setResult(analysis); setStatus('ready') }).catch((error: unknown) => {
      if (controller.signal.aborted) return
      setErrorMessage(error instanceof ApiError ? error.message : `The analysis service did not respond. ${NETWORK_FAILURE_HINT}`)
      setStatus('error')
    })
    return () => controller.abort()
  }, [source, initialAnalysis, attempt])

  useEffect(() => {
    if (!result) return
    let cancelled = false
    void getGroupReviews(result.analysis_id).then((value) => {
      if (!cancelled) setReviews(value)
    }).catch((error: unknown) => {
      if (cancelled) return
      setErrorMessage(error instanceof ApiError ? error.message : `Teacher review state could not be loaded. ${NETWORK_FAILURE_HINT}`)
      setStatus('error')
    })
    return () => { cancelled = true }
  }, [result, reviewAttempt])

  const retry = () => {
    setErrorMessage('')
    if (result) {
      setReviews(null)
      setStatus('ready')
      setReviewAttempt((value) => value + 1)
      return
    }
    setStatus('loading')
    setAttempt((value) => value + 1)
  }

  return <><PageHeader eyebrow="Step 3 of 6" title="Learning gaps" description="Review recurring semantic groups as evidence-backed proposals. Correct and blank responses are excluded, and the teacher remains the final authority." action={result && <Badge tone={result.data_label === 'synthetic_demo' ? 'amber' : 'green'}>{result.data_label === 'synthetic_demo' ? 'Synthetic demo data' : 'Teacher upload'}</Badge>} />
    {!source && !result && <StatePanel kind="empty" title="No assessment ready for analysis" description="Validate an assessment first, or analyze the deterministic synthetic photosynthesis fixture." action={<button className="text-button" onClick={onLoadDemo}>Analyze demo dataset →</button>} />}
    {status === 'loading' && <LongTaskProgress task="analysis" />}
    {status === 'error' && <StatePanel kind="error" title="Analysis could not be completed" description={errorMessage} action={<button className="text-button" onClick={retry}>Try again</button>} />}
    {status === 'ready' && result && <><section className="question-strip"><div><span>Assessment</span><strong>{result.assessment.title} · {result.assessment.topic}</strong></div><div><span>Analysis status</span><strong>{result.summary.group_count} gap{result.summary.group_count === 1 ? '' : 's'} detected</strong></div></section><div className="metric-grid compact"><Metric label="Eligible incorrect" value={String(result.summary.eligible_incorrect_count)} note="Correct and blank excluded" /><Metric label="Grouped evidence" value={String(result.summary.grouped_response_count)} note={`${result.summary.outlier_count} unmatched`} /><Metric label="Learning gaps" value={String(result.summary.group_count)} note={`Minimum support ${result.grouping.minimum_support}`} /></div>
      {reviews && <GroupReviewPanel reviews={reviews} onChange={setReviews} />}
      {!reviews ? <StatePanel kind="loading" title="Loading teacher review state" description="ClassLens is resolving the current active evidence groups." /> : reviews.active_groups.length === 0 ? <StatePanel kind="empty" title="No active misconception groups" description={reviews.dismissed_groups.length ? 'All detected groups are currently dismissed. Open review mode to restore one.' : result.message ?? 'No group met the configured evidence threshold.'} /> : <section className="section-block"><div className="section-title"><div><p className="eyebrow">Potential misconceptions</p><h2>{reviews.active_groups.length} recurring pattern{reviews.active_groups.length === 1 ? '' : 's'} to inspect</h2></div><Badge tone="amber">Teacher review needed</Badge></div><div className="gap-list">{reviews.active_groups.map((group) => <button className="gap-card" key={group.reviewed_group_id} onClick={() => onNext(group, result)}><div><Badge tone="amber">Potential · not yet interpreted</Badge><h2>{group.display_label}</h2><p>{group.representative_responses.slice(0, 2).map((item) => `“${item.answer}”`).join(' · ')}</p></div><div className="gap-meta"><span>Affected responses</span><strong>{group.support_count} of {group.eligible_response_count}</strong><span>Open evidence →</span></div></button>)}</div></section>}
      <p className="analysis-method">Model: {result.embedding.model_id} · complete-link cosine threshold {result.grouping.similarity_threshold.toFixed(2)} · analysis {result.analysis_id}</p></>}
  </>
}

function Misconception({ group, analysisId, initialRetrieval, onBack, onRetrieved, onNext }: { group: ReviewedMisconceptionGroup | null; analysisId: string | null; initialRetrieval: MaterialRetrievalResponse | null; onBack: () => void; onRetrieved: (result: MaterialRetrievalResponse | null) => void; onNext: () => void }) {
  const [material, setMaterial] = useState<LearningMaterial | null>(initialRetrieval?.material ?? null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [ingestStatus, setIngestStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>(initialRetrieval ? 'ready' : 'idle')
  const [ingestError, setIngestError] = useState('')
  const [retrievalStatus, setRetrievalStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>(initialRetrieval ? 'ready' : 'idle')
  const [retrieval, setRetrieval] = useState<MaterialRetrievalResponse | null>(initialRetrieval)
  const [retrievalError, setRetrievalError] = useState('')

  const ingest = async (request: () => Promise<MaterialIngestionResponse>) => {
    setIngestStatus('loading'); setIngestError(''); setRetrieval(null); setRetrievalStatus('idle'); setRetrievalError(''); onRetrieved(null)
    try { const response = await request(); setMaterial(response.material); setIngestStatus('ready'); setRetrievalStatus('idle') }
    catch (error: unknown) { setMaterial(null); setIngestStatus('error'); setIngestError(error instanceof ApiError ? error.message : `The learning material could not be ingested. ${NETWORK_FAILURE_HINT}`) }
  }

  const retrieve = async () => {
    if (!group || !material) return
    setRetrievalStatus('loading'); setRetrievalError('')
    const context: MaterialRetrievalContext = {
      analysis_id: analysisId ?? '',
      group_id: group.reviewed_group_id,
      question_id: group.question_id,
      question: group.question,
      correct_answer: group.correct_answer,
      representative_answers: group.representative_responses.map((item) => item.answer),
    }
    try {
      const response = await retrieveMaterialForGroup(material.material_id, context)
      setRetrieval(response); onRetrieved(response); setRetrievalStatus('ready')
    } catch (error: unknown) {
      setRetrieval(null); onRetrieved(null); setRetrievalStatus('error')
      setRetrievalError(error instanceof ApiError ? error.message : `Supporting material could not be retrieved. ${NETWORK_FAILURE_HINT}`)
    }
  }

  if (!group) return <><PageHeader eyebrow="Step 4 of 6" title="Misconception detail" description="Select a detected group before reviewing its evidence." /><StatePanel kind="empty" title="No learning gap selected" description="Return to analysis and choose a recurring response group." action={<button className="text-button" onClick={onBack}>Back to learning gaps →</button>} /></>
  return <><PageHeader eyebrow="Step 4 of 6" title={group.display_label} description="Inspect student evidence and the teaching passages retrieved for this potential pattern. The group label remains teacher-reviewable." action={<Badge tone="amber">Not a diagnosis</Badge>} />
    <section className="card"><p className="eyebrow">Question context · {group.question_id}</p><h2>{group.question}</h2><div className="concept-box"><span>Reference answer</span><p>{group.correct_answer}</p></div></section>
    <section className="section-block"><div className="section-title"><div><p className="eyebrow">Student evidence · {group.support_count} affected responses</p><h2>Representative responses</h2></div><Badge>Exact input evidence</Badge></div><div className="evidence-list">{group.representative_responses.map((item) => <blockquote key={item.student_id}><p>“{item.answer}”</p><cite>{item.student_id} · similarity to medoid {item.similarity_to_medoid.toFixed(2)}</cite></blockquote>)}</div></section>
    <section className="section-block material-grounding"><div className="section-title"><div><p className="eyebrow">Teaching material</p><h2>Find supporting passages</h2></div><Badge tone="green">Separate from student evidence</Badge></div><p className="material-help">Choose the synthetic photosynthesis notes or ingest a UTF-8 plain text file. Retrieved passages come only from this selected material.</p>
      <div className="material-controls"><button className="button secondary" disabled={ingestStatus === 'loading'} onClick={() => void ingest(ingestPhotosynthesisDemoMaterial)}>{ingestStatus === 'loading' ? 'Preparing material…' : 'Load photosynthesis demo notes'}</button><label className="file-input material-file">{selectedFile?.name ?? 'Choose teaching material (.txt)'}<input type="file" accept=".txt,text/plain" onChange={(event: ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0] ?? null; setSelectedFile(file); setMaterial(null); setRetrieval(null); setIngestStatus('idle'); setIngestError(''); setRetrievalStatus('idle'); setRetrievalError(''); onRetrieved(null) }} /></label><button className="button secondary" disabled={!selectedFile || ingestStatus === 'loading'} onClick={() => selectedFile && void ingest(() => ingestLearningMaterial(selectedFile))}>Ingest selected text</button></div>
      {ingestStatus === 'idle' && !material && <StatePanel kind="empty" title="No teaching material selected" description="Load the demo notes or choose a .txt file. Material metadata and exact chunks are persisted; vectors are rebuilt after a backend restart." />}
      {ingestStatus === 'loading' && <StatePanel kind="loading" title="Preparing teaching material" description="The backend is validating, chunking, embedding, and indexing this text." />}
      {ingestStatus === 'error' && <StatePanel kind="error" title="Teaching material could not be ingested" description={ingestError} />}
      {material && <div className="material-ready"><div><strong>{material.title}</strong><span>{material.filename} · {material.chunk_count} chunks · {material.embedding_dimension}-dimension embeddings</span></div><Badge tone={material.source_kind === 'synthetic_demo' ? 'amber' : 'green'}>{material.source_kind === 'synthetic_demo' ? 'Synthetic demo material' : 'Teacher upload'}</Badge><button className="button primary" disabled={retrievalStatus === 'loading'} onClick={() => void retrieve()}>{retrievalStatus === 'loading' ? 'Finding passages…' : 'Find supporting passages'}</button></div>}
      {retrievalStatus === 'loading' && <StatePanel kind="loading" title="Searching selected teaching material" description="The misconception context is embedded and compared with this material's indexed chunks." />}
      {retrievalStatus === 'error' && <StatePanel kind="error" title="Supporting passages could not be retrieved" description={retrievalError} action={<button className="text-button" onClick={() => void retrieve()}>Try retrieval again</button>} />}
      {retrieval?.status === 'insufficient_relevant_context' && <StatePanel kind="empty" title="No sufficiently relevant teaching passage found" description={`${retrieval.message} Choose more relevant material before any grounded intervention can be prepared.`} />}
      {retrieval?.status === 'retrieved' && <div className="source-results"><div className="source-results__heading"><strong>Teaching material · retrieved sources</strong><span>Top {retrieval.retrieval.top_k} · minimum score {retrieval.retrieval.minimum_relevance_score.toFixed(2)}</span></div>{retrieval.results.map((source) => <article className="source-result" key={source.chunk_id}><div className="source-result__meta"><strong>{retrieval.material.filename}</strong><span>Chunk {source.chunk_index + 1} · relevance {source.similarity.toFixed(2)}</span></div><p>{source.text}</p><small>Characters {source.start_char}–{source.end_char} · {source.chunk_id}</small></article>)}</div>}
    </section>
    <p className="analysis-method">{group.coherence === null ? 'Coherence not recalculated after teacher review' : `Group coherence ${group.coherence.toFixed(2)}`} · members {group.member_student_ids.join(', ')}</p><div className="callout"><div><strong>Teacher checkpoint</strong><p>Does this grouping match the student evidence, and do the selected passages support later instruction? No intervention has been generated.</p></div><button className="button primary" onClick={onNext}>Continue to intervention review <ArrowIcon /></button></div></>
}

function editableFromRecord(record: RemediationRecord): EditableRemediationContent {
  return {
    misconception_summary: record.content.misconception_summary,
    learning_objective: record.content.learning_objective,
    teacher_explanation: record.content.teacher_explanation,
    corrected_concept: record.content.corrected_concept,
    activity: record.content.activity,
    analogy: record.content.analogy,
    follow_up_questions: record.content.follow_up_questions.map((item) => ({ ...item })),
  }
}

function getSessionStorage(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

function Intervention({ group, analysisId, dataLabel, assessment, sources, initialRemediation, onBack, onNext }: {
  group: ReviewedMisconceptionGroup | null
  analysisId: string | null
  dataLabel: AnalysisResponse['data_label'] | null
  assessment: AssessmentPreview['assessment'] | null
  sources: MaterialRetrievalResponse | null
  initialRemediation: RemediationRecord | null
  onBack: () => void
  onNext: (record: RemediationRecord) => void
}) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'saving' | 'insufficient' | 'error'>(initialRemediation ? 'ready' : 'idle')
  const [record, setRecord] = useState<RemediationRecord | null>(initialRemediation)
  const [editable, setEditable] = useState<EditableRemediationContent | null>(initialRemediation ? editableFromRecord(initialRemediation) : null)
  const [reviewed, setReviewed] = useState(false)
  const [reviewNotes, setReviewNotes] = useState(initialRemediation?.review_notes ?? '')
  const [errorMessage, setErrorMessage] = useState('')
  const pendingGenerationId = useRef<string | null>(null)
  const generationStorageKey = group && sources
    ? `classlens:remediation-generation:${analysisId ?? 'unknown'}:${group.reviewed_group_id}:${sources.material.material_id}:${sources.material.content_hash}`
    : null

  const getGenerationRequestId = () => {
    if (pendingGenerationId.current) return pendingGenerationId.current
    const requestId = generationStorageKey
      ? getOrCreatePendingRequestId(getSessionStorage(), generationStorageKey, () => window.crypto.randomUUID())
      : window.crypto.randomUUID()
    pendingGenerationId.current = requestId
    return requestId
  }

  const clearGenerationRequestId = () => {
    pendingGenerationId.current = null
    if (!generationStorageKey) return
    clearPendingRequestId(getSessionStorage(), generationStorageKey)
  }

  const generate = async () => {
    if (!group || !analysisId || !assessment || !sources) return
    setStatus('loading'); setErrorMessage(''); setReviewed(false)
    try {
      const response = await generateRemediation({
        generation_request_id: getGenerationRequestId(),
        analysis_id: analysisId,
        grade_level: assessment.grade_level,
        subject: assessment.subject,
        topic: assessment.topic,
        misconception: {
          group_id: group.reviewed_group_id,
          source_group_ids: group.source_group_ids,
          provisional_label: group.display_label,
          question_id: group.question_id,
          question: group.question,
          correct_answer: group.correct_answer,
          support_count: group.support_count,
          eligible_response_count: group.eligible_response_count,
          representative_responses: group.representative_responses,
        },
        retrieval: sources,
      })
      clearGenerationRequestId()
      if (response.status === 'insufficient_context' || !response.remediation) {
        setStatus('insufficient')
        setErrorMessage(response.message ?? 'Insufficient teacher-provided material to generate grounded remediation.')
        return
      }
      setRecord(response.remediation)
      setEditable(editableFromRecord(response.remediation))
      setStatus('ready')
    } catch (error: unknown) {
      setStatus('error')
      setErrorMessage(error instanceof ApiError ? error.message : `The grounded remediation could not be generated. ${NETWORK_FAILURE_HINT}`)
    }
  }

  const submitReview = async (action: 'save' | 'approve' | 'reject') => {
    if (!record || !editable) return
    setStatus('saving'); setErrorMessage('')
    try {
      const updated = await reviewRemediation(record.remediation_id, {
        action,
        edited_content: editable,
        review_notes: reviewNotes,
      })
      setRecord(updated)
      setEditable(editableFromRecord(updated))
      setStatus('ready')
    } catch (error: unknown) {
      setStatus('error')
      setErrorMessage(error instanceof ApiError ? error.message : `The teacher review could not be saved. Your edits remain on this screen. ${NETWORK_FAILURE_HINT}`)
    }
  }

  const updateField = (field: keyof Omit<EditableRemediationContent, 'follow_up_questions'>, value: string) => {
    setEditable((current) => current ? { ...current, [field]: value } : current)
  }
  const updateQuestion = (index: number, field: 'prompt' | 'expected_answer', value: string) => {
    setEditable((current) => current ? {
      ...current,
      follow_up_questions: current.follow_up_questions.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item),
    } : current)
  }

  const exportApprovedIntervention = () => {
    if (!group || !analysisId || !dataLabel || !assessment || record?.status !== 'approved') return
    const artifact = buildApprovedInterventionExport({
      analysisId,
      dataLabel,
      assessment,
      group,
      remediation: record,
      exportedAt: new Date().toISOString(),
    })
    const objectUrl = URL.createObjectURL(new Blob([artifact.html], { type: 'text/html;charset=utf-8' }))
    const anchor = document.createElement('a')
    try {
      anchor.href = objectUrl
      anchor.download = artifact.filename
      document.body.append(anchor)
      anchor.click()
    } finally {
      anchor.remove()
      URL.revokeObjectURL(objectUrl)
    }
  }

  if (!group || !assessment) return <><PageHeader eyebrow="Step 5 of 6" title="Review intervention" description="Select a detected learning gap before generating an intervention." /><StatePanel kind="empty" title="No misconception selected" description="Return to Learning Gaps and select a group with student evidence." action={<button className="text-button" onClick={onBack}>Back to misconception detail →</button>} /></>
  const hasGrounding = sources?.status === 'retrieved' && sources.results.length > 0
  const isTerminal = record?.status === 'approved' || record?.status === 'rejected'
  return <><PageHeader eyebrow="Step 5 of 6" title="Review intervention" description="Follow the evidence chain, edit the generated draft, then make an explicit teacher decision." action={record && <Badge tone={record.status === 'approved' ? 'green' : 'amber'}>{record.status === 'generated' ? 'Pending teacher review' : record.status}</Badge>} />
    <div className="reasoning-chain" aria-label="Grounded intervention reasoning chain">
      <section className="review-stage"><div className="review-stage__marker">1</div><div><strong>Detected misconception</strong><p>{group.display_label} · {group.support_count} of {group.eligible_response_count} eligible responses</p><div className="review-evidence">{group.representative_responses.map((item) => <blockquote key={item.student_id}>“{item.answer}” <cite>{item.student_id}</cite></blockquote>)}</div></div><Badge tone="amber">Student evidence</Badge></section>
      <section className="review-stage"><div className="review-stage__marker">2</div><div><strong>Retrieved teacher material</strong><p>{hasGrounding ? `${sources.results.length} passage${sources.results.length === 1 ? '' : 's'} from ${sources.material.title}` : 'No sufficiently relevant passage is available.'}</p>{hasGrounding && <div className="review-sources">{sources.results.map((source) => <details key={source.chunk_id}><summary>{source.chunk_id} · relevance {source.similarity.toFixed(2)}</summary><p>{source.text}</p></details>)}</div>}</div><Badge tone={hasGrounding ? 'green' : 'amber'}>{hasGrounding ? 'Teacher-provided sources' : 'Grounding unavailable'}</Badge></section>
    </div>

    {!hasGrounding && <StatePanel kind="empty" title="Grounded generation is unavailable" description="Return to the misconception detail and retrieve relevant teacher-provided material. ClassLens will not generate an unsupported intervention." action={<button className="text-button" onClick={onBack}>Choose better teaching material →</button>} />}
    {hasGrounding && status === 'idle' && <section className="generation-start"><div><strong>Ready to prepare a grounded draft</strong><p>Gemini will receive this detected group and only the passages shown above. The result will remain pending until you approve or reject it.</p></div><button className="button primary" onClick={() => void generate()}>Generate remediation</button></section>}
    {status === 'loading' && <LongTaskProgress task="generation" />}
    {status === 'insufficient' && <StatePanel kind="empty" title="Insufficient teacher-provided material" description={errorMessage} action={<button className="text-button" onClick={onBack}>Return to teaching material →</button>} />}
    {status === 'error' && <StatePanel kind="error" title="Remediation action failed" description={errorMessage} action={record ? <button className="text-button" onClick={() => setStatus('ready')}>Return to your draft →</button> : <button className="text-button" onClick={() => void generate()}>Try generation again →</button>} />}

    {record && editable && status !== 'loading' && <section className="section-block generated-review"><div className="section-title"><div><h2>AI-generated intervention</h2><p className="material-help">Review every field. Source references are locked to the retrieved teacher passages; your instructional wording remains editable until a decision is recorded.</p></div><Badge tone="amber">AI-generated · {record.model}</Badge></div>
      <div className="card form-card intervention-form">
        <label htmlFor="misconception-summary">Misconception summary</label><textarea id="misconception-summary" rows={2} value={editable.misconception_summary} disabled={isTerminal || status === 'saving'} onChange={(event) => updateField('misconception_summary', event.target.value)} />
        <div className="form-grid"><div><label htmlFor="learning-objective">Learning objective</label><textarea id="learning-objective" rows={3} value={editable.learning_objective} disabled={isTerminal || status === 'saving'} onChange={(event) => updateField('learning_objective', event.target.value)} /></div><div><label htmlFor="corrected-concept">Corrected concept</label><textarea id="corrected-concept" rows={3} value={editable.corrected_concept} disabled={isTerminal || status === 'saving'} onChange={(event) => updateField('corrected_concept', event.target.value)} /></div></div>
        <label htmlFor="teacher-explanation">Teacher explanation</label><textarea id="teacher-explanation" rows={4} value={editable.teacher_explanation} disabled={isTerminal || status === 'saving'} onChange={(event) => updateField('teacher_explanation', event.target.value)} />
        <label htmlFor="remediation-activity">Short remediation activity</label><textarea id="remediation-activity" rows={4} value={editable.activity} disabled={isTerminal || status === 'saving'} onChange={(event) => updateField('activity', event.target.value)} />
        <label htmlFor="remediation-analogy">Example or analogy <span className="optional-label">Optional</span></label><textarea id="remediation-analogy" rows={3} value={editable.analogy ?? ''} disabled={isTerminal || status === 'saving'} onChange={(event) => updateField('analogy', event.target.value)} />
        <div className="question-editor"><strong>Checks for understanding</strong>{editable.follow_up_questions.map((item, index) => <div className="question-edit" key={index}><label htmlFor={`follow-up-${index}`}>Question {index + 1}</label><textarea id={`follow-up-${index}`} rows={2} value={item.prompt} disabled={isTerminal || status === 'saving'} onChange={(event) => updateQuestion(index, 'prompt', event.target.value)} /><label htmlFor={`answer-${index}`}>Expected answer</label><textarea id={`answer-${index}`} rows={2} value={item.expected_answer} disabled={isTerminal || status === 'saving'} onChange={(event) => updateQuestion(index, 'expected_answer', event.target.value)} /></div>)}</div>
        <div className="source-lock"><strong>Grounded source references</strong><div>{record.content.source_references.map((reference) => <Badge tone="green" key={reference}>{reference}</Badge>)}</div><small>References are validated against the retrieved chunks and cannot be edited.</small></div>
        <label htmlFor="review-notes">Teacher review notes <span className="optional-label">Optional</span></label><textarea id="review-notes" rows={2} value={reviewNotes} disabled={isTerminal || status === 'saving'} onChange={(event) => setReviewNotes(event.target.value)} />
        {!isTerminal && <label className="check-row"><input type="checkbox" checked={reviewed} disabled={status === 'saving'} onChange={(event) => setReviewed(event.target.checked)} />I reviewed the student evidence, source passages, and final intervention text.</label>}
        {status === 'saving' && <p className="save-status" role="status">Saving teacher decision…</p>}
        {!isTerminal && <div className="actions review-actions"><button className="button secondary danger-action" disabled={status === 'saving'} onClick={() => void submitReview('reject')}>Reject draft</button><button className="button secondary" disabled={status === 'saving'} onClick={() => void submitReview('save')}>Save edits</button><button className="button primary" disabled={!reviewed || status === 'saving'} onClick={() => void submitReview('approve')}>Approve intervention</button></div>}
        {record.status === 'approved' && <div className="decision-state decision-state--approved"><div><strong>Approved by teacher</strong><p>The teacher-edited content above is the approved version. The original Gemini generation remains preserved in persistent storage.</p></div><div className="actions"><button className="button secondary" onClick={exportApprovedIntervention}>Download evidence summary</button><button className="button primary" onClick={() => onNext(record)}>Continue to results <ArrowIcon /></button></div></div>}
        {record.status === 'rejected' && <div className="decision-state decision-state--rejected"><div><strong>Rejected by teacher</strong><p>This draft will not be treated as an approved intervention.</p></div><button className="button secondary" onClick={onBack}>Return to misconception</button></div>}
      </div>
    </section>}
  </>
}

function Results({ baseline, group, remediation, initialResult, onResult, onNext }: {
  baseline: AnalysisResponse | null
  group: ReviewedMisconceptionGroup | null
  remediation: RemediationRecord | null
  initialResult: FollowUpComparisonRecord | null
  onResult: (record: FollowUpComparisonRecord) => void
  onNext: () => void
}) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'insufficient' | 'error'>(initialResult?.status === 'completed' ? 'ready' : initialResult ? 'insufficient' : 'idle')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<FollowUpComparisonRecord | null>(initialResult)
  const [errorMessage, setErrorMessage] = useState('')
  const hasApprovedContext = Boolean(baseline && group && remediation?.status === 'approved')
  const link: FollowUpComparisonLink | null = baseline && group && remediation ? {
    baseline_analysis_id: baseline.analysis_id,
    group_id: group.reviewed_group_id,
    remediation_id: remediation.remediation_id,
  } : null

  const runComparison = async (request: () => Promise<FollowUpComparisonRecord>) => {
    setStatus('loading'); setErrorMessage(''); setResult(null)
    try {
      const comparison = await request()
      setResult(comparison)
      onResult(comparison)
      setStatus(comparison.status === 'completed' ? 'ready' : 'insufficient')
    } catch (error: unknown) {
      setStatus('error')
      setErrorMessage(error instanceof ApiError ? error.message : `The comparison service did not respond. ${NETWORK_FAILURE_HINT}`)
    }
  }
  const loadDemo = () => { if (link) void runComparison(() => submitPhotosynthesisDemoComparison(link)) }
  const uploadSelected = () => { if (link && selectedFile) void runComparison(() => submitFollowUpComparison(selectedFile, link)) }
  const fileChanged = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file); setErrorMessage(''); setResult(null)
    if (file && !file.name.toLowerCase().endsWith('.csv')) {
      setStatus('error'); setErrorMessage('Choose a follow-up file with a .csv extension.'); return
    }
    setStatus('idle')
  }

  if (!hasApprovedContext || !baseline || !group || !remediation) {
    return <><PageHeader eyebrow="Step 6 of 6" title="Results" description="Compare baseline and follow-up transparently. Missing data remains unavailable rather than being treated as zero." action={<Badge tone="amber">Comparison unavailable</Badge>} /><StatePanel kind="empty" title="Complete the approved intervention first" description="Results require an analyzed initial assessment, a selected misconception, and an explicitly approved persisted intervention." /><div className="callout"><div><strong>No improvement has been inferred</strong><p>Return to the workflow and preserve the evidence chain before loading follow-up responses.</p></div><button className="button secondary" onClick={onNext}>Return to dashboard</button></div></>
  }

  const metrics = result?.metrics
  return <><PageHeader eyebrow="Step 6 of 6" title="Before and after" description="Re-evaluate the same question after the approved intervention, with visible denominators and missing responses kept separate." action={<Badge tone={result?.status === 'completed' ? 'green' : 'amber'}>{result?.status === 'completed' ? 'Comparison ready' : result?.status === 'insufficient_data' ? 'Insufficient evidence' : 'Follow-up needed'}</Badge>} />
    {status === 'idle' && <section className="card results-intake"><div><h2>Load the follow-up assessment</h2><p>ClassLens will validate the same CSV contract, re-run misconception grouping, and link the result to analysis <strong>{baseline.analysis_id}</strong> and the approved intervention.</p></div><div className="results-intake__actions">{baseline.data_label === 'synthetic_demo' && <button className="button primary" onClick={loadDemo}>Analyze synthetic follow-up</button>}<label className="file-input results-file">{selectedFile?.name ?? 'Choose follow-up CSV'}<input type="file" accept=".csv,text/csv" onChange={fileChanged} /></label><button className="button secondary" disabled={!selectedFile} onClick={uploadSelected}>Analyze selected follow-up</button></div></section>}
    {status === 'loading' && <StatePanel kind="loading" title="Re-evaluating student understanding" description="The backend is validating the follow-up, running the existing misconception analysis, and calculating the comparison." />}
    {status === 'error' && <StatePanel kind="error" title="Follow-up comparison failed" description={errorMessage} action={<button className="text-button" onClick={() => { setStatus('idle'); setErrorMessage('') }}>Return to follow-up intake →</button>} />}
    {status === 'insufficient' && result && <><StatePanel kind="empty" title="Not enough evidence to compare this misconception" description={result.message ?? 'The follow-up could not reliably re-identify the selected misconception, so no improvement metric was calculated.'} /><section className="trace-strip"><strong>Trace preserved</strong><span>Initial {result.trace?.baseline_analysis_id}</span><span>Follow-up {result.trace?.follow_up_analysis_id}</span><span>Intervention {result.trace?.remediation_id}</span></section><div className="actions"><button className="button secondary" onClick={() => setStatus('idle')}>Try another follow-up</button></div></>}
    {status === 'ready' && result && metrics && <>
      <section className="results-card"><div><Badge tone={result.data_label === 'synthetic_demo' ? 'amber' : 'green'}>{result.data_label === 'synthetic_demo' ? 'Synthetic demo data' : 'Teacher follow-up'}</Badge><h2>{remediation.content.misconception_summary}</h2><p>{result.message}</p></div><div className="comparison"><div><span>Before intervention</span><strong>{metrics.before.affected_students} / {metrics.before.answered_students} affected</strong><small>{metrics.before.misconception_prevalence_percent.toFixed(1)}% prevalence</small></div><span className="comparison-arrow" aria-hidden="true">→</span><div><span>After intervention</span><strong>{metrics.after.affected_students} / {metrics.after.answered_students} affected</strong><small>{metrics.after.misconception_prevalence_percent.toFixed(1)}% prevalence</small></div></div></section>
      <section className="prevalence-panel" aria-labelledby="prevalence-title"><div className="section-title"><div><h2 id="prevalence-title">Misconception prevalence</h2><p>Share of answered responses grouped into this recurring pattern.</p></div><strong className="reduction-value">{metrics.percentage_point_reduction.toFixed(1)} pp reduction</strong></div><div className="prevalence-row"><span>Before</span><div className="prevalence-track"><span style={{ width: `${metrics.before.misconception_prevalence_percent}%` }} /></div><strong>{metrics.before.misconception_prevalence_percent.toFixed(1)}%</strong></div><div className="prevalence-row"><span>After</span><div className="prevalence-track"><span className="after" style={{ width: `${metrics.after.misconception_prevalence_percent}%` }} /></div><strong>{metrics.after.misconception_prevalence_percent.toFixed(1)}%</strong></div></section>
      <div className="metric-grid"><Metric label="Observed reduction" value={`${metrics.percentage_point_reduction.toFixed(1)} pp`} note="Percentage points, not causal impact" /><Metric label="Matched answered" value={String(metrics.matched_answered_students)} note="Stable baseline identifiers" /><Metric label="Missing follow-up" value={String(metrics.missing_follow_up_students)} note="Absent or blank; never counted as zero" /></div>
      <section className="section-block"><div className="section-title"><div><h2>What changed for the original group</h2><p>Transitions are calculated only where the response evidence supports them.</p></div></div><dl className="transition-list"><div><dt>Resolved correctly</dt><dd>{metrics.transitions.resolved_correct}</dd></div><div><dt>Changed, still incorrect</dt><dd>{metrics.transitions.changed_but_still_incorrect}</dd></div><div><dt>Still in this misconception</dt><dd>{metrics.transitions.still_struggling}</dd></div><div><dt>Missing from original group</dt><dd>{metrics.transitions.missing_from_baseline_group}</dd></div><div><dt>Newly grouped after</dt><dd>{metrics.transitions.new_affected_students}</dd></div></dl></section>
      <section className="trace-strip"><strong>Evidence chain</strong><span>Initial {result.trace?.baseline_analysis_id}</span><span>Group {result.trace?.baseline_group_id}</span><span>Intervention {result.trace?.remediation_id}</span><span>Follow-up {result.trace?.follow_up_analysis_id}</span></section>
      <div className="callout complete"><div><strong>Feedback loop complete</strong><p>The same assessment contract, grouping method, approved intervention, and follow-up evidence produced this observed comparison.</p></div><div className="actions"><button className="button secondary" onClick={() => { setResult(null); setStatus('idle') }}>Run another follow-up</button><button className="button primary" onClick={onNext}>Return to dashboard</button></div></div>
    </>}
  </>
}

export default App
