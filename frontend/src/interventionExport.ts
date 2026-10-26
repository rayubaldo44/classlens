import type {
  AnalysisResponse,
  AssessmentPreview,
  RemediationRecord,
  ReviewedMisconceptionGroup,
} from './api/client'

export type ApprovedInterventionExportInput = {
  analysisId: string
  dataLabel: AnalysisResponse['data_label']
  assessment: AssessmentPreview['assessment']
  group: ReviewedMisconceptionGroup
  remediation: RemediationRecord
  exportedAt: string
}

export type InterventionExportArtifact = {
  filename: string
  html: string
}

const escapeHtml = (value: string | number) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#39;')

const slug = (value: string, maximumLength: number) => value
  .normalize('NFKD')
  .replace(/\p{M}/gu, '')
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, '-')
  .replace(/^-+|-+$/g, '')
  .slice(0, maximumLength)
  .replace(/-+$/g, '')

const sameStringSet = (left: string[], right: string[]) => {
  const leftSet = new Set(left)
  const rightSet = new Set(right)
  return leftSet.size === left.length
    && rightSet.size === right.length
    && leftSet.size === rightSet.size
    && [...leftSet].every((value) => rightSet.has(value))
}

const list = (values: string[]) => `<ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join('')}</ul>`

const field = (label: string, value: string) => `
  <section class="field">
    <h3>${label}</h3>
    <p class="preserve-text">${escapeHtml(value)}</p>
  </section>`

const filenameFor = (input: ApprovedInterventionExportInput) => {
  const descriptive = [slug(input.assessment.subject, 32), slug(input.assessment.topic, 32)].filter(Boolean)
  const remediation = slug(input.remediation.remediation_id, 38) || 'approved-intervention'
  const stem = descriptive.length > 0
    ? ['classlens', ...descriptive, remediation].join('-')
    : `classlens-${remediation}`
  return `${stem.slice(0, 115).replace(/-+$/g, '')}.html`
}

const validate = ({ analysisId, group, remediation }: ApprovedInterventionExportInput) => {
  if (remediation.status !== 'approved') {
    throw new Error('An approved remediation is required for export.')
  }
  if (remediation.analysis_id !== analysisId) {
    throw new Error('The remediation does not belong to the active analysis.')
  }
  if (remediation.group_id !== group.reviewed_group_id) {
    throw new Error('The remediation does not belong to the active reviewed group.')
  }
  if (!sameStringSet(remediation.source_group_ids, group.source_group_ids)) {
    throw new Error('The remediation source group provenance does not match the reviewed evidence.')
  }
  const savedSourceIds = new Set(remediation.sources.map((source) => source.chunk_id))
  if (remediation.content.source_references.some((reference) => !savedSourceIds.has(reference))) {
    throw new Error('An approved source reference is missing from the persisted remediation sources.')
  }
}

export function buildApprovedInterventionExport(input: ApprovedInterventionExportInput): InterventionExportArtifact {
  validate(input)
  const { analysisId, assessment, dataLabel, exportedAt, group, remediation } = input
  const content = remediation.content
  const cited = new Set(content.source_references)
  const optionalAnalogy = content.analogy ? field('Analogy', content.analogy) : ''
  const reviewNotes = remediation.review_notes ? `
    <section>
      <h2>Teacher review notes</h2>
      <p class="preserve-text">${escapeHtml(remediation.review_notes)}</p>
    </section>` : ''
  const syntheticLabel = dataLabel === 'synthetic_demo'
    ? '<p class="label label-warning">Synthetic demo data</p>'
    : '<p class="label">Teacher upload</p>'
  const sources = remediation.sources.map((source) => `
    <article class="source">
      <div class="source-heading">
        <h3>${escapeHtml(source.material_title)}</h3>
        <span class="label">${cited.has(source.chunk_id) ? 'Cited by approved intervention' : 'Persisted supporting source'}</span>
      </div>
      <p class="meta">${escapeHtml(source.filename)} · ${escapeHtml(source.chunk_id)} · Chunk ${source.chunk_index + 1} · Characters ${source.start_char}–${source.end_char}</p>
      <blockquote class="preserve-text">${escapeHtml(source.text)}</blockquote>
      <dl class="audit compact">
        <div><dt>Material ID</dt><dd>${escapeHtml(source.material_id)}</dd></div>
        <div><dt>Retrieval similarity</dt><dd>${escapeHtml(source.similarity)}</dd></div>
      </dl>
    </article>`).join('')

  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ClassLens teacher-approved intervention</title>
  <style>
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #17211b; background: #f5f3ed; }
    * { box-sizing: border-box; }
    body { margin: 0; line-height: 1.55; }
    main { width: min(900px, calc(100% - 32px)); margin: 32px auto; background: #fff; padding: clamp(24px, 5vw, 56px); border: 1px solid #d8d6cd; }
    header { border-bottom: 3px solid #17211b; padding-bottom: 24px; }
    h1 { margin: 8px 0; font-size: clamp(2rem, 6vw, 4rem); line-height: .95; letter-spacing: -.04em; }
    h2 { margin-top: 36px; font-size: 1.35rem; }
    h3 { margin: 0 0 6px; font-size: 1rem; }
    p, blockquote { margin: 6px 0 14px; }
    h1, h2, h3, p, blockquote, li, strong, dd { overflow-wrap: anywhere; }
    blockquote { padding: 14px 18px; border-left: 3px solid #7c8f7d; background: #f5f7f3; }
    .preserve-text { white-space: pre-wrap; }
    .label { display: inline-block; margin: 0; padding: 4px 8px; border: 1px solid #78917d; color: #315c3c; font-size: .75rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; overflow-wrap: anywhere; }
    .label-warning { border-color: #a06b22; color: #74480d; }
    .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 24px; }
    .summary div, .field, .source { break-inside: avoid; }
    .summary div, .source-heading > * { min-width: 0; }
    .summary span, .meta, dt { color: #5c655e; font-size: .82rem; }
    .summary strong { display: block; }
    .field { padding: 16px 0; border-bottom: 1px solid #e4e2db; }
    .source { margin: 16px 0; padding: 18px; border: 1px solid #d8d6cd; }
    .source-heading { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 16px; align-items: start; }
    .source-heading h3 { flex: 1 1 240px; }
    .audit { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
    .audit div { min-width: 0; }
    dt { font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
    dd { margin: 2px 0 0; overflow-wrap: anywhere; }
    .compact { margin-bottom: 0; }
    .limits { margin-top: 40px; padding: 18px; background: #f5f3ed; border: 1px solid #d8d6cd; }
    @media print { body { background: #fff; } main { width: 100%; margin: 0; border: 0; padding: 0; } @page { margin: 16mm; } }
  </style>
</head>
<body>
<main>
  <header>
    ${syntheticLabel}
    <p>ClassLens evidence summary</p>
    <h1>Teacher-approved intervention</h1>
    <p>Exported <time datetime="${escapeHtml(exportedAt)}">${escapeHtml(exportedAt)}</time></p>
    <div class="summary">
      <div><span>Assessment</span><strong>${escapeHtml(assessment.title)}</strong></div>
      <div><span>Subject</span><strong>${escapeHtml(assessment.subject)}</strong></div>
      <div><span>Grade</span><strong>Grade ${escapeHtml(assessment.grade_level)}</strong></div>
      <div><span>Topic</span><strong>${escapeHtml(assessment.topic)}</strong></div>
    </div>
  </header>

  <section>
    <h2>Potential misconception evidence</h2>
    <h3>${escapeHtml(group.display_label)}</h3>
    <p><strong>${group.support_count} of ${group.eligible_response_count}</strong> eligible incorrect responses were grouped in this reviewed pattern.</p>
    ${field('Question', group.question)}
    ${field('Expected answer', group.correct_answer)}
    <section class="field">
      <h3>Representative responses</h3>
      ${group.representative_responses.map((response) => `<blockquote class="preserve-text">${escapeHtml(response.answer)}</blockquote>`).join('')}
    </section>
  </section>

  <section>
    <h2>Approved intervention</h2>
    ${field('Misconception summary', content.misconception_summary)}
    ${field('Learning objective', content.learning_objective)}
    ${field('Corrected concept', content.corrected_concept)}
    ${field('Teacher explanation', content.teacher_explanation)}
    ${field('Activity', content.activity)}
    ${optionalAnalogy}
    <section class="field">
      <h3>Checks for understanding</h3>
      <ol>${content.follow_up_questions.map((question) => `<li><strong class="preserve-text">${escapeHtml(question.prompt)}</strong><p class="preserve-text">Expected answer: ${escapeHtml(question.expected_answer)}</p></li>`).join('')}</ol>
    </section>
    <section class="field"><h3>Validated source references</h3>${list(content.source_references)}</section>
  </section>

  ${reviewNotes}

  <section>
    <h2>Grounding sources</h2>
    ${sources}
  </section>

  <section>
    <h2>Audit details</h2>
    <dl class="audit">
      <div><dt>Analysis ID</dt><dd>${escapeHtml(analysisId)}</dd></div>
      <div><dt>Reviewed group ID</dt><dd>${escapeHtml(group.reviewed_group_id)}</dd></div>
      <div><dt>Source group IDs</dt><dd>${escapeHtml(group.source_group_ids.join(', '))}</dd></div>
      <div><dt>Question ID</dt><dd>${escapeHtml(group.question_id)}</dd></div>
      <div><dt>Remediation ID</dt><dd>${escapeHtml(remediation.remediation_id)}</dd></div>
      <div><dt>Status</dt><dd>Approved by teacher</dd></div>
      <div><dt>Provider</dt><dd>${escapeHtml(remediation.provider)}</dd></div>
      <div><dt>Model</dt><dd>${escapeHtml(remediation.model)}</dd></div>
      <div><dt>Prompt version</dt><dd>${escapeHtml(remediation.prompt_version)}</dd></div>
      <div><dt>Created</dt><dd><time datetime="${escapeHtml(remediation.created_at)}">${escapeHtml(remediation.created_at)}</time></dd></div>
      <div><dt>Teacher decision updated</dt><dd><time datetime="${escapeHtml(remediation.updated_at)}">${escapeHtml(remediation.updated_at)}</time></dd></div>
    </dl>
  </section>

  <aside class="limits">
    <h2>How to read this summary</h2>
    <p>This is a potential misconception supported by observed response evidence, not a diagnosis of student thinking.</p>
    <p>This export records an approved instructional response and its sources. It does not establish causation or claim that later outcomes were caused by this intervention.</p>
  </aside>
</main>
</body>
</html>`

  return { filename: filenameFor(input), html }
}
