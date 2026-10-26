import assert from 'node:assert/strict'
import test from 'node:test'

import type { ApprovedInterventionExportInput } from '../src/interventionExport.ts'
import { buildApprovedInterventionExport } from '../src/interventionExport.ts'

const approvedInput = (): ApprovedInterventionExportInput => ({
  analysisId: 'analysis-baseline-01',
  dataLabel: 'teacher_upload',
  assessment: {
    title: 'Photosynthesis Free-Response Check',
    subject: 'Science',
    grade_level: '7',
    topic: 'Photosynthesis',
  },
  group: {
    reviewed_group_id: 'reviewed-light-food',
    display_label: 'Sunlight is food',
    status: 'active',
    source_group_ids: ['source-light', 'source-energy'],
    question_id: 'Q1',
    question: 'How do plants make food?',
    correct_answer: 'Plants use light energy to make glucose.',
    support_count: 9,
    eligible_response_count: 29,
    member_student_ids: ['STUDENT-PRIVATE-42', 'MEMBER-PRIVATE-77'],
    representative_responses: [{
      student_id: 'STUDENT-PRIVATE-42',
      answer: 'Plants eat sunlight as their food.',
      similarity_to_medoid: 0.97,
    }],
    coherence: null,
  },
  remediation: {
    remediation_id: 'remediation_approved',
    status: 'approved',
    analysis_id: 'analysis-baseline-01',
    group_id: 'reviewed-light-food',
    source_group_ids: ['source-energy', 'source-light'],
    provider: 'google-genai',
    model: 'gemini-3.1-flash-lite',
    prompt_version: 'grounded_remediation_v1',
    generated_content: {
      misconception_summary: 'GENERATED-ONLY-SENTINEL',
      learning_objective: 'Original generated objective.',
      teacher_explanation: 'Original generated explanation.',
      corrected_concept: 'Original generated concept.',
      activity: 'Original generated activity.',
      analogy: null,
      follow_up_questions: [{ prompt: 'Original question?', expected_answer: 'Original answer.' }],
      source_references: ['chunk-001'],
    },
    content: {
      misconception_summary: 'Students confuse light energy with food matter.',
      learning_objective: 'Distinguish energy input from glucose production.',
      teacher_explanation: 'Light supplies energy; plants manufacture glucose from carbon dioxide and water.',
      corrected_concept: 'Plants use light energy to produce glucose.',
      activity: 'Sort cards into energy inputs and matter inputs or products.',
      analogy: 'A solar-powered kitchen uses energy but still needs ingredients.',
      follow_up_questions: [{
        prompt: 'What does sunlight provide to the plant?',
        expected_answer: 'Energy for making glucose.',
      }],
      source_references: ['chunk-001'],
    },
    sources: [{
      material_id: 'material-photosynthesis',
      material_title: 'Grade 7 Photosynthesis Notes',
      filename: 'photosynthesis.txt',
      chunk_id: 'chunk-001',
      chunk_index: 0,
      text: 'Sunlight supplies energy. Plants use carbon dioxide and water to make glucose.',
      similarity: 0.784,
      start_char: 0,
      end_char: 78,
    }],
    review_notes: 'Approved after aligning the language with this week’s lesson.',
    created_at: '2026-10-23T07:00:00.000Z',
    updated_at: '2026-10-23T07:30:00.000Z',
  },
  exportedAt: '2026-10-23T08:00:00.000Z',
})

test('exports the approved intervention and exact evidence without student identifiers', () => {
  const artifact = buildApprovedInterventionExport(approvedInput())

  assert.equal(artifact.filename, 'classlens-science-photosynthesis-remediation-approved.html')
  for (const expected of [
    'Photosynthesis Free-Response Check', 'Science', 'Grade 7', 'Photosynthesis',
    'Sunlight is food', '9 of 29', 'Plants eat sunlight as their food.',
    'Students confuse light energy with food matter.',
    'Distinguish energy input from glucose production.',
    'Light supplies energy; plants manufacture glucose from carbon dioxide and water.',
    'Plants use light energy to produce glucose.',
    'Sort cards into energy inputs and matter inputs or products.',
    'A solar-powered kitchen uses energy but still needs ingredients.',
    'What does sunlight provide to the plant?', 'Energy for making glucose.',
    'Approved after aligning the language with this week’s lesson.',
    'Sunlight supplies energy. Plants use carbon dioxide and water to make glucose.',
    'chunk-001', 'Chunk 1', 'Characters 0–78', 'Cited by approved intervention',
    'analysis-baseline-01', 'reviewed-light-food', 'source-light', 'source-energy',
    'remediation_approved', 'google-genai', 'gemini-3.1-flash-lite',
    'grounded_remediation_v1', '2026-10-23T07:00:00.000Z',
    '2026-10-23T07:30:00.000Z', '2026-10-23T08:00:00.000Z',
    'potential misconception', 'not a diagnosis', 'does not establish causation',
  ]) assert.ok(artifact.html.includes(expected), `missing ${expected}`)

  for (const forbidden of [
    'STUDENT-PRIVATE-42', 'MEMBER-PRIVATE-77', 'GENERATED-ONLY-SENTINEL',
    '<script', 'src="http', 'href="http', 'url(', '@import',
  ]) assert.equal(artifact.html.includes(forbidden), false, `included ${forbidden}`)
})

test('rejects records that are not approved', () => {
  for (const status of ['generated', 'rejected'] as const) {
    const input = approvedInput()
    input.remediation.status = status
    assert.throws(() => buildApprovedInterventionExport(input), /approved remediation/i)
  }
})

test('rejects stale analysis, group, and source-group provenance', () => {
  const staleAnalysis = approvedInput()
  staleAnalysis.analysisId = 'analysis-other'
  assert.throws(() => buildApprovedInterventionExport(staleAnalysis), /analysis/i)

  const staleGroup = approvedInput()
  staleGroup.group.reviewed_group_id = 'reviewed-other'
  assert.throws(() => buildApprovedInterventionExport(staleGroup), /group/i)

  const staleSources = approvedInput()
  staleSources.remediation.source_group_ids = ['source-light']
  assert.throws(() => buildApprovedInterventionExport(staleSources), /source group/i)
})

test('rejects source references missing from persisted remediation snapshots', () => {
  const input = approvedInput()
  input.remediation.content.source_references = ['chunk-missing']

  assert.throws(() => buildApprovedInterventionExport(input), /source reference/i)
})

test('escapes hostile dynamic values without introducing active resources', () => {
  const input = approvedInput()
  const hostile = '<script>alert("x")</script> & < > \' " https://evil.example/asset'
  input.assessment.title = hostile
  input.group.display_label = hostile
  input.group.representative_responses[0].answer = hostile
  input.remediation.content.teacher_explanation = hostile
  input.remediation.review_notes = hostile
  input.remediation.sources[0].text = hostile

  const { html } = buildApprovedInterventionExport(input)

  assert.equal(html.includes(hostile), false)
  assert.ok(html.includes('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; &lt; &gt; &#39; &quot; https://evil.example/asset'))
  for (const active of ['<script', 'src="http', 'href="http', 'url(', '@import']) {
    assert.equal(html.includes(active), false, `included ${active}`)
  }
})

test('omits empty optional sections', () => {
  const input = approvedInput()
  input.remediation.content.analogy = null
  input.remediation.review_notes = null

  const { html } = buildApprovedInterventionExport(input)

  assert.equal(html.includes('<h3>Analogy</h3>'), false)
  assert.equal(html.includes('<h2>Teacher review notes</h2>'), false)
})

test('creates a bounded safe filename with remediation fallback', () => {
  const input = approvedInput()
  input.assessment.subject = `${'Very Long Subject '.repeat(12)}!!!`
  input.assessment.topic = `${'Detailed Topic '.repeat(12)}???`

  const longName = buildApprovedInterventionExport(input).filename
  assert.match(longName, /^[a-z0-9-]+\.html$/)
  assert.ok(longName.length <= 120)

  input.assessment.subject = '!!!'
  input.assessment.topic = '???'
  input.remediation.remediation_id = 'remediation_fallback_99'
  assert.equal(
    buildApprovedInterventionExport(input).filename,
    'classlens-remediation-fallback-99.html',
  )
})

test('labels only synthetic data as synthetic demo data', () => {
  const teacher = approvedInput()
  assert.equal(buildApprovedInterventionExport(teacher).html.includes('Synthetic demo data'), false)

  const synthetic = approvedInput()
  synthetic.dataLabel = 'synthetic_demo'
  assert.equal(buildApprovedInterventionExport(synthetic).html.includes('Synthetic demo data'), true)
})
