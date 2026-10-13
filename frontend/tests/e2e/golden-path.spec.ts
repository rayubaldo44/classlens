import { expect, test, type Page, type Route } from '@playwright/test'
import path from 'node:path'

const assessment = {
  title: 'Photosynthesis Free-Response Check',
  subject: 'Science',
  grade_level: '7',
  topic: 'Photosynthesis',
}

const preview = {
  status: 'validated',
  data_label: 'teacher_upload',
  filename: 'photosynthesis_responses.csv',
  assessment,
  summary: {
    response_count: 45,
    answered_count: 43,
    blank_count: 2,
    student_count: 45,
    question_count: 1,
    correct_count: 14,
    incorrect_count: 29,
  },
  sample_responses: [{
    row_number: 2,
    student_id: 'S001',
    question_id: 'Q1',
    question: 'Explain how plants make food during photosynthesis.',
    answer: 'Plants eat sunlight and that becomes their food.',
    correct_answer: 'Plants use light energy to make glucose from carbon dioxide and water.',
    answer_status: 'answered',
    is_correct: false,
  }],
}

const group = {
  group_id: 'grp_sunlight_food',
  provisional_label: 'Potential misconception pattern 1',
  interpretation_status: 'not_requested',
  question_id: 'Q1',
  question: preview.sample_responses[0].question,
  correct_answer: preview.sample_responses[0].correct_answer,
  support_count: 9,
  eligible_response_count: 29,
  member_student_ids: ['S001', 'S005', 'S009'],
  representative_responses: [{
    student_id: 'S001',
    answer: preview.sample_responses[0].answer,
    similarity_to_medoid: 1,
  }],
  coherence: 0.8454,
}

const analysis = {
  assessment_id: 'assessment_baseline',
  analysis_id: 'analysis_baseline',
  status: 'completed',
  data_label: 'teacher_upload',
  filename: preview.filename,
  assessment,
  summary: {
    response_count: 45,
    answered_count: 43,
    blank_count: 2,
    correct_count: 14,
    eligible_incorrect_count: 29,
    grouped_response_count: 18,
    outlier_count: 11,
    question_count: 1,
    group_count: 1,
  },
  embedding: { model_id: 'test/embedding', dimension: 384, preprocessing: 'answer_only_v1' },
  grouping: { algorithm: 'complete_link_cosine_v1', similarity_threshold: 0.7, minimum_support: 3 },
  groups: [group],
  message: null,
}

const material = {
  material_id: 'material_photosynthesis',
  title: 'Photosynthesis Grade 7',
  filename: 'photosynthesis_grade7.txt',
  source_kind: 'teacher_upload',
  content_hash: 'hash-material',
  chunk_count: 3,
  chunk_size_chars: 900,
  chunk_overlap_chars: 120,
  embedding_model: 'test/embedding',
  embedding_dimension: 384,
}

const retrieval = {
  status: 'retrieved',
  group_id: group.group_id,
  material,
  retrieval: {
    algorithm: 'cosine_similarity_v1',
    top_k: 3,
    minimum_relevance_score: 0.42,
    embedding_model: 'test/embedding',
  },
  results: [{
    chunk_id: 'chunk_001',
    chunk_index: 0,
    text: 'Sunlight supplies energy. Plants make glucose, which stores chemical energy.',
    similarity: 0.784,
    start_char: 0,
    end_char: 76,
  }],
  message: null,
}

const generatedContent = {
  misconception_summary: 'Students describe sunlight itself as plant food.',
  learning_objective: 'Distinguish light energy from glucose matter.',
  teacher_explanation: 'Light provides energy; plants manufacture glucose.',
  corrected_concept: 'Plants use light energy to make and store energy in glucose.',
  activity: 'Sort examples into energy inputs and matter products.',
  analogy: null,
  follow_up_questions: [{ prompt: 'What does sunlight provide?', expected_answer: 'Energy.' }],
  source_references: ['chunk_001'],
}

const remediation = {
  remediation_id: 'remediation_approved',
  status: 'generated',
  analysis_id: analysis.analysis_id,
  group_id: group.group_id,
  provider: 'test-provider',
  model: 'test-model',
  prompt_version: 'grounded_remediation_v1',
  generated_content: generatedContent,
  content: generatedContent,
  sources: retrieval.results.map((source) => ({
    material_id: material.material_id,
    material_title: material.title,
    filename: material.filename,
    ...source,
  })),
  review_notes: null,
  created_at: '2026-10-13T00:00:00Z',
  updated_at: '2026-10-13T00:00:00Z',
}

const comparison = {
  comparison_id: 'comparison_follow_up',
  status: 'completed',
  data_label: 'teacher_upload',
  subject: assessment.subject,
  grade_level: assessment.grade_level,
  topic: assessment.topic,
  question_id: group.question_id,
  question: group.question,
  misconception_label: group.provisional_label,
  trace: {
    baseline_assessment_id: analysis.assessment_id,
    follow_up_assessment_id: 'assessment_follow_up',
    baseline_analysis_id: analysis.analysis_id,
    follow_up_analysis_id: 'analysis_follow_up',
    baseline_group_id: group.group_id,
    follow_up_group_id: 'grp_follow_up',
    remediation_id: remediation.remediation_id,
    remediation_status: 'approved',
    comparison_method: 'same_question_member_overlap_v1',
  },
  metrics: {
    before: {
      analysis_id: analysis.analysis_id,
      assessment_title: assessment.title,
      filename: preview.filename,
      answered_students: 43,
      correct_students: 14,
      affected_students: 9,
      misconception_prevalence_percent: 20.9,
    },
    after: {
      analysis_id: 'analysis_follow_up',
      assessment_title: 'Photosynthesis Follow-Up',
      filename: 'photosynthesis_follow_up_responses.csv',
      answered_students: 43,
      correct_students: 33,
      affected_students: 3,
      misconception_prevalence_percent: 7,
    },
    matched_answered_students: 43,
    missing_follow_up_students: 2,
    percentage_point_reduction: 13.9,
    correct_percentage_point_change: 44.1,
    transitions: {
      baseline_affected_students: 9,
      resolved_correct: 5,
      changed_but_still_incorrect: 1,
      still_struggling: 3,
      missing_from_baseline_group: 0,
      new_affected_students: 0,
    },
  },
  message: 'Observed prevalence decreased in the synthetic follow-up.',
  created_at: '2026-10-13T00:05:00Z',
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

async function installApi(page: Page) {
  let generationAttempts = 0
  let approvedRemediation = { ...remediation, content: { ...generatedContent } }

  await page.route('http://api.classlens.test/**', async (route) => {
    const request = route.request()
    const pathname = new URL(request.url()).pathname

    if (pathname === '/health') return json(route, { status: 'ok', service: 'classlens-api' })
    if (pathname === '/api/v1/assessments/preview') return json(route, preview)
    if (pathname === '/api/v1/assessments/analyze') return json(route, analysis)
    if (pathname === `/api/v1/assessments/analyses/${analysis.analysis_id}`) return json(route, analysis)
    if (pathname === '/api/v1/learning-materials/ingest') {
      return json(route, { status: 'ready', material, message: 'Teaching material is ready.' })
    }
    if (pathname === `/api/v1/learning-materials/${material.material_id}/retrieve`) return json(route, retrieval)
    if (pathname === '/api/v1/remediations' && request.method() === 'POST') {
      generationAttempts += 1
      if (generationAttempts === 1) {
        return json(route, {
          error: { code: 'llm_unavailable', message: 'The controlled test provider is temporarily unavailable.', retryable: true },
        }, 503)
      }
      return json(route, { status: 'generated', remediation, message: null })
    }
    if (pathname === `/api/v1/remediations/${remediation.remediation_id}` && request.method() === 'PATCH') {
      const review = request.postDataJSON()
      approvedRemediation = {
        ...remediation,
        status: review.action === 'approve' ? 'approved' : remediation.status,
        content: { ...review.edited_content, source_references: generatedContent.source_references },
        review_notes: review.review_notes ?? null,
        updated_at: '2026-10-13T00:04:00Z',
      }
      return json(route, approvedRemediation)
    }
    if (pathname === `/api/v1/remediations/${remediation.remediation_id}`) return json(route, approvedRemediation)
    if (pathname === '/api/v1/results' && request.method() === 'POST') return json(route, comparison)
    if (pathname === `/api/v1/results/${comparison.comparison_id}`) return json(route, comparison)

    return json(route, { error: { code: 'unexpected_test_request', message: `${request.method()} ${pathname}` } }, 500)
  })
}

test('teacher completes and restores the evidence-backed workflow after a controlled provider failure', async ({ page }) => {
  const approvedExplanation = 'Light provides energy; plants use matter to manufacture glucose.'
  await installApi(page)
  await page.goto('/upload')

  await page.getByLabel('Choose CSV').setInputFiles(path.resolve('../data/demo/photosynthesis_responses.csv'))
  await page.getByRole('button', { name: 'Validate selected CSV' }).click()
  await expect(page.getByRole('heading', { name: assessment.title })).toBeVisible()
  await expect(page.getByText('45 accepted responses')).toBeVisible()

  await page.getByRole('button', { name: /Analyze learning gaps/ }).click()
  await expect(page.getByRole('heading', { name: '1 recurring pattern to inspect' })).toBeVisible()
  await page.getByRole('button', { name: /Potential misconception pattern 1/ }).click()
  await expect(page.getByText('Student evidence · 9 affected responses')).toBeVisible()

  await page.getByLabel('Choose teaching material (.txt)').setInputFiles(
    path.resolve('../data/demo/learning_materials/photosynthesis_grade7.txt'),
  )
  await page.getByRole('button', { name: 'Ingest selected text' }).click()
  await expect(page.getByText('3 chunks · 384-dimension embeddings')).toBeVisible()
  await page.getByRole('button', { name: 'Find supporting passages' }).click()
  await expect(page.getByText(/Sunlight supplies energy/)).toBeVisible()
  await page.getByRole('button', { name: /Continue to intervention review/ }).click()

  await page.getByRole('button', { name: 'Generate remediation' }).click()
  await expect(page.getByRole('alert').getByText('Remediation action failed')).toBeVisible()
  await expect(page.getByText('controlled test provider is temporarily unavailable')).toBeVisible()
  await page.getByRole('button', { name: /Try generation again/ }).click()

  await page.getByLabel('Teacher explanation').fill(approvedExplanation)
  await page.getByLabel(/I reviewed the student evidence/).check()
  await page.getByRole('button', { name: 'Approve intervention' }).click()
  await expect(page.getByText('Approved by teacher')).toBeVisible()
  await page.getByRole('button', { name: /Continue to results/ }).click()

  await page.getByLabel('Choose follow-up CSV').setInputFiles(
    path.resolve('../data/demo/photosynthesis_follow_up_responses.csv'),
  )
  await page.getByRole('button', { name: 'Analyze selected follow-up' }).click()
  await expect(page.getByText('Feedback loop complete')).toBeVisible()
  await expect(page.getByText('9 / 43 affected')).toBeVisible()
  await expect(page.getByText('3 / 43 affected')).toBeVisible()
  await expect(page.getByText('13.9 pp reduction')).toBeVisible()

  await page.reload()
  await expect(page.getByText('Feedback loop complete')).toBeVisible()
  await page.getByRole('button', { name: '05 Intervention review' }).click()
  await expect(page.getByText('Approved by teacher')).toBeVisible()
  await expect(page.getByLabel('Teacher explanation')).toHaveValue(approvedExplanation)
  await page.getByRole('button', { name: '06 Results' }).click()
  await expect(page.getByText('13.9 pp reduction')).toBeVisible()
})
